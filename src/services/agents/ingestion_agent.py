import aiohttp
import docker
import os
import re
import hashlib
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from tempfile import mkdtemp
from shutil import rmtree
from google import genai
from urllib.parse import urljoin, urlparse

from services.base_agent import BaseAgent
from services.memory import AgentMemory
from models.models import SourceDocument
from configuration.configuration import Configuration as Config, logger


class IngestionAgent(BaseAgent):
    def __init__(self, config: Config, memory: AgentMemory):
        super().__init__("IngestionAgent", config, memory)
        self.gemini_client = genai.Client(api_key=config.gemini_api_key)
        self.processed_sources = set()

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing entry point for different source types"""
        self.update_status("processing")
        logger.info(f"🔄 IngestionAgent processing: {task.get('type')} - {task.get('source', '')[:100]}")

        source_type = task.get("type")
        source = task.get("source")

        if not source:
            self.update_status("error")
            return {"status": "error", "message": "Source is required"}

        try:
            if source_type == "website":
                return await self._scrape_website(source, task.get("depth", 2))
            elif source_type == "github":
                return await self._process_github_repo(source)
            elif source_type == "text":
                return await self._process_text_content(source, task.get("metadata", {}))
            elif source_type == "document":
                return await self._process_document(source)
            else:
                self.update_status("error")
                return {"status": "error", "message": f"Unknown source type: {source_type}"}
        except Exception as e:
            self.update_status("error")
            logger.error(f"❌ IngestionAgent error: {e}")
            return {"status": "error", "message": str(e)}

    async def _process_text_content(self, content: str, metadata: Dict) -> Dict[str, Any]:
        """Process raw text content"""
        if len(content) < self.config.min_content_length:
            return {"status": "error",
                    "message": f"Content too short (minimum {self.config.min_content_length} characters)"}

        # Clean and preprocess text
        cleaned_content = self._clean_text(content)
        doc_type = await self._classify_content_advanced(cleaned_content)

        # Generate unique ID
        content_hash = hashlib.md5(cleaned_content.encode()).hexdigest()
        doc_id = f"text_{content_hash}"

        doc = SourceDocument(
            id=doc_id,
            title=metadata.get("title", f"Text Content ({content_hash[:8]})"),
            content=cleaned_content,
            source="text",
            url=None,
            doc_type=doc_type,
            metadata={
                **metadata,
                "content_length": len(cleaned_content),
                "word_count": len(cleaned_content.split()),
                "processing_timestamp": str(datetime.now())
            },
        )

        if not self.memory.check_duplicate(doc):
            self.memory.store_document(doc)
            await self._extract_concepts_and_relationships(doc)
            self.update_status("completed")
            return {
                "status": "success",
                "document_id": doc.id,
                "type": "text",
                "metadata": {
                    "title": doc.title,
                    "doc_type": doc_type,
                    "content_length": len(cleaned_content),
                    "concepts_extracted": True
                }
            }
        else:
            return {"status": "skipped", "message": "Duplicate content detected", "document_id": doc_id}

    async def _scrape_website(self, url: str, depth: int = 2) -> Dict[str, Any]:
        """Enhanced website scraping with content filtering"""
        if url in self.processed_sources:
            return {"status": "skipped", "message": "URL already processed", "url": url}

        try:
            logger.info(f"🌐 Scraping website: {url} (depth: {depth})")
            temp_dir = mkdtemp()
            docker_client = docker.from_env()

            # Enhanced httrack command with better filtering
            container = docker_client.containers.run(
                self.config.httrack_docker_image,
                command=[
                    url,
                    f"--depth={depth}",
                    "--mirror",
                    "--path", "/output",
                    "--ext-depth=1",  # Limit external links
                    "--robots=0",  # Ignore robots.txt
                    "--timeout=30",  # Connection timeout
                    "--retries=2"  # Retry attempts
                ],
                volumes={temp_dir: {'bind': '/output', 'mode': 'rw'}},
                detach=True,
                remove=True,
                mem_limit="512m"  # Memory limit for safety
            )

            # Wait with timeout
            result = container.wait(timeout=300)  # 5 minute timeout
            if result['StatusCode'] != 0:
                logger.warning(f"⚠️ httrack exited with code {result['StatusCode']}")

            # Process scraped content
            content_parts = []
            processed_files = 0

            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(('.html', '.htm')):
                        try:
                            file_path = os.path.join(root, file)
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                soup = BeautifulSoup(f.read(), "html.parser")

                                # Remove script and style elements
                                for script in soup(["script", "style", "nav", "footer", "header"]):
                                    script.decompose()

                                # Extract meaningful text
                                text = soup.get_text(separator=" ", strip=True)
                                if len(text) > 200:  # Only include substantial content
                                    content_parts.append(text)
                                    processed_files += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Error processing file {file}: {e}")

            # Combine and clean content
            raw_content = "\n\n".join(content_parts)
            text_content = self._clean_text(raw_content)

            if len(text_content) < self.config.min_content_length:
                return {"status": "error", "message": f"Scraped content too short ({len(text_content)} chars)"}

            # Advanced content classification
            doc_type = await self._classify_content_advanced(text_content)

            # Extract title from URL or content
            title = self._extract_title_from_content(text_content) or urlparse(url).netloc

            document = SourceDocument(
                id=url,
                title=title,
                content=text_content,
                source="website",
                url=url,
                doc_type=doc_type,
                metadata={
                    "depth": depth,
                    "files_processed": processed_files,
                    "content_length": len(text_content),
                    "scraping_timestamp": str(datetime.now()),
                    "domain": urlparse(url).netloc
                },
            )

            if not self.memory.check_duplicate(document):
                self.memory.store_document(document)
                await self._extract_concepts_and_relationships(document)
                self.processed_sources.add(url)

            rmtree(temp_dir)
            self.update_status("completed")

            return {
                "status": "success",
                "document_id": document.id,
                "type": "website",
                "url": url,
                "metadata": {
                    "title": title,
                    "doc_type": doc_type,
                    "files_processed": processed_files,
                    "content_length": len(text_content)
                }
            }

        except Exception as e:
            self.update_status("error")
            logger.error(f"❌ Website scraping failed for {url}: {e}")
            return {"status": "error", "message": f"Website scraping failed: {str(e)}"}

    async def _process_github_repo(self, repo_url: str) -> Dict[str, Any]:
        """Enhanced GitHub repository processing with intelligent file prioritization"""
        if repo_url in self.processed_sources:
            return {"status": "skipped", "message": "Repository already processed", "url": repo_url}

        try:
            logger.info(f"📁 Processing GitHub repo: {repo_url}")
            parts = repo_url.rstrip('/').split('/')
            if len(parts) < 2:
                return {"status": "error", "message": "Invalid GitHub URL format"}

            owner, repo = parts[-2], parts[-1]

            # Priority file patterns (in order of importance)
            priority_patterns = [
                r'readme\.md$',
                r'readme\.rst$',
                r'readme\.txt$',
                r'docs?/.*\.md$',
                r'documentation/.*\.md$',
                r'guide.*\.md$',
                r'tutorial.*\.md$',
                r'getting.?started.*\.md$',
                r'api.*\.md$',
                r'reference.*\.md$'
            ]

            async with aiohttp.ClientSession() as session:
                # Get repository contents
                async with session.get(f"https://api.github.com/repos/{owner}/{repo}/contents") as resp:
                    resp.raise_for_status()
                    contents = await resp.json()

                # Collect files by priority
                collected_files = []
                await self._collect_github_files(session, contents, priority_patterns, collected_files)

                # Also check common documentation directories
                for item in contents:
                    if item['type'] == 'dir' and item['name'].lower() in ['docs', 'documentation', 'doc']:
                        async with session.get(item['url']) as resp:
                            if resp.status == 200:
                                dir_contents = await resp.json()
                                await self._collect_github_files(session, dir_contents, priority_patterns,
                                                                 collected_files)

            if not collected_files:
                return {"status": "error", "message": "No documentation files found in repository"}

            # Combine content with metadata
            content_sections = []
            for file_info in collected_files:
                content_sections.append(f"## {file_info['name']}\n\n{file_info['content']}")

            text_content = "\n\n".join(content_sections)
            cleaned_content = self._clean_text(text_content)

            if len(cleaned_content) < self.config.min_content_length:
                return {"status": "error", "message": f"Repository content too short ({len(cleaned_content)} chars)"}

            doc_type = await self._classify_content_advanced(cleaned_content)
            title = f"{owner}/{repo} Documentation"

            document = SourceDocument(
                id=repo_url,
                title=title,
                content=cleaned_content,
                source="github",
                url=repo_url,
                doc_type=doc_type,
                metadata={
                    "owner": owner,
                    "repository": repo,
                    "files_processed": len(collected_files),
                    "content_length": len(cleaned_content),
                    "processing_timestamp": str(datetime.now())
                },
            )

            if not self.memory.check_duplicate(document):
                self.memory.store_document(document)
                await self._extract_concepts_and_relationships(document)
                self.processed_sources.add(repo_url)

            self.update_status("completed")
            return {
                "status": "success",
                "document_id": document.id,
                "type": "github",
                "url": repo_url,
                "metadata": {
                    "title": title,
                    "doc_type": doc_type,
                    "files_processed": len(collected_files),
                    "content_length": len(cleaned_content)
                }
            }

        except Exception as e:
            self.update_status("error")
            logger.error(f"❌ GitHub processing failed for {repo_url}: {e}")
            return {"status": "error", "message": f"GitHub processing failed: {str(e)}"}

    async def _collect_github_files(self, session: aiohttp.ClientSession, contents: List, patterns: List[str],
                                    collected: List):
        """Collect GitHub files based on priority patterns"""
        for item in contents:
            if item['type'] == 'file':
                file_name = item['name'].lower()

                # Check against priority patterns
                for pattern in patterns:
                    if re.search(pattern, file_name, re.IGNORECASE):
                        try:
                            async with session.get(item['download_url']) as resp:
                                if resp.status == 200:
                                    content = await resp.text()
                                    collected.append({
                                        'name': item['name'],
                                        'content': content,
                                        'size': item['size'],
                                        'priority': patterns.index(pattern)
                                    })
                                    break  # Found match, don't check other patterns
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to download {item['name']}: {e}")

        # Sort by priority (lower index = higher priority)
        collected.sort(key=lambda x: x['priority'])

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove common web artifacts
        text = re.sub(r'(Cookie|Privacy Policy|Terms of Service|Subscribe|Newsletter)', '', text, flags=re.IGNORECASE)

        # Remove URLs (but keep the text around them)
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        # Clean up markdown artifacts
        text = re.sub(r'#{1,6}\s*', '', text)  # Remove markdown headers
        text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)  # Remove bold/italic
        text = re.sub(r'`([^`]+)`', r'\1', text)  # Remove inline code

        return text.strip()

    def _extract_title_from_content(self, content: str) -> str:
        """Extract a meaningful title from content"""
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if len(line) > 10 and len(line) < 100:
                # Remove common prefixes
                line = re.sub(r'^(Home|Welcome to|About|Introduction|Overview)', '', line, flags=re.IGNORECASE).strip()
                if line:
                    return line
        return None

    async def _classify_content_advanced(self, content: str) -> str:
        """Advanced content classification using Gemini AI"""
        try:
            # Use Gemini for intelligent classification
            classification_prompt = f"""
            Analyze this content and classify it into one of these categories:
            - tutorial: Step-by-step instructions, how-to guides
            - reference: API docs, specifications, technical references  
            - example: Code samples, demos, use cases
            - overview: General information, introductions, concepts

            Content preview (first 1000 chars):
            {content[:1000]}

            Return only the category name.
            """

            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=classification_prompt,
            )

            classification = response.candidates[0].content.parts[0].text.strip().lower()

            # Validate classification
            valid_types = ["tutorial", "reference", "example", "overview"]
            if classification in valid_types:
                return classification
            else:
                # Fallback to keyword-based classification
                return self._classify_content_fallback(content)

        except Exception as e:
            logger.warning(f"⚠️ AI classification failed, using fallback: {e}")
            return self._classify_content_fallback(content)

    def _classify_content_fallback(self, content: str) -> str:
        """Fallback content classification using keywords"""
        content_lower = content.lower()

        if "tutorial" in content.lower() or "step by step" in content.lower():
            return "tutorial"
        elif "example" in content.lower() or "code sample" in content.lower():
            return "example"
        elif "api" in content_lower or "reference" in content_lower or "documentation" in content_lower:
            return "reference"
        else:
            return "overview"

    async def _extract_concepts_and_relationships(self, document: SourceDocument):
        """Enhanced concept and relationship extraction using Gemini AI"""
        try:
            logger.info(f"🧠 Extracting concepts from document: {document.title}")

            # Extract concepts using Gemini
            concept_prompt = f"""
            Extract 5-10 key concepts, terms, or topics from this content. 
            Focus on technical terms, important concepts, and main topics.
            Return each concept on a separate line, no numbering or bullets.

            Content: {document.content[:3000]}
            """

            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=concept_prompt,
            )

            concept_text = response.candidates[0].content.parts[0].text.strip()
            concepts = [c.strip() for c in concept_text.split('\n') if c.strip() and len(c.strip()) > 2]

            # Store concepts
            concept_ids = []
            for concept in concepts[:10]:  # Limit to 10 concepts
                concept_id = self.memory.store_concept(concept, document.id)
                concept_ids.append((concept_id, concept))

            # Extract relationships using Gemini
            if len(concepts) > 1:
                relationship_prompt = f"""
                Given these concepts from the same document: {', '.join(concepts[:8])}

                Identify 3-5 meaningful relationships between them.
                Format: concept1 -> concept2 (relationship_type)

                Relationship types: related_to, part_of, enables, requires, implements
                """

                rel_response = self.gemini_client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=relationship_prompt,
                )

                rel_text = rel_response.candidates[0].content.parts[0].text.strip()

                # Parse relationships
                for line in rel_text.split('\n'):
                    if '->' in line and '(' in line:
                        try:
                            parts = line.split('->')
                            if len(parts) == 2:
                                concept1 = parts[0].strip()
                                rest = parts[1].strip()
                                if '(' in rest:
                                    concept2 = rest.split('(')[0].strip()
                                    rel_type = rest.split('(')[1].split(')')[0].strip()

                                    # Store relationship if both concepts exist
                                    if concept1 in concepts and concept2 in concepts:
                                        store_relationship(concept1, concept2, rel_type)
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to parse relationship: {line} - {e}")

            logger.info(f"✅ Extracted {len(concepts)} concepts and relationships for {document.title}")

        except Exception as e:
            logger.error(f"❌ Failed to extract concepts for {document.id}: {e}")

    async def _process_document(self, doc_path: str) -> Dict[str, Any]:
        """Process document files (PDF, DOCX, etc.)"""
        # This would require additional libraries like PyPDF2, python-docx
        # For now, return a placeholder implementation
        return {
            "status": "error",
            "message": "Document processing not yet implemented. Please use text input instead."
        }