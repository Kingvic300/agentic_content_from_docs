import aiohttp
import docker
import os
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from tempfile import mkdtemp
from shutil import rmtree
from google import genai

from services.base_agent import BaseAgent
from services.memory import AgentMemory
from models.models import SourceDocument
from configuration.configuration import Configuration as Config


class IngestionAgent(BaseAgent):
    def __init__(self, config: Config, memory: AgentMemory):
        super().__init__("IngestionAgent", config, memory)
        self.gemini_client = genai.Client()

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.update_status("processing")

        source_type = task.get("type")
        source = task.get("source")

        if source_type == "website":
            return await self._scrape_website(source, task.get("depth", 2))
        elif source_type == "github":
            return await self._process_github_repo(source)
        elif source_type == "text":
            content = source
            doc_type = self._classify_content(content)
            if len(content) < 100:
                return {"status": "error", "message": "Content too short"}
            doc = SourceDocument(
                id=f"text_{hash(content)}",
                title=task.get("metadata", {}).get("title", "text_source"),
                content=content,
                source="text",
                url=None,
                doc_type=doc_type,
                metadata=task.get("metadata", {}),
            )
            if not self.memory.check_duplicate(doc):
                self.memory.store_document(doc)
                await self._extract_concepts_and_relationships(doc)
            return {"status": "success", "document_id": doc.id, "type": "text"}
        else:
            self.update_status("error")
            return {"error": f"Unknown source type: {source_type}"}

    async def _scrape_website(self, url: str, depth: int = 2) -> Dict[str, Any]:
        try:
            temp_dir = mkdtemp()
            docker_client = docker.from_env()
            container = docker_client.containers.run(
                self.config.httrack_docker_image,
                command=[url, f"--depth={depth}", "--mirror", "--path", "/output"],
                volumes={temp_dir: {'bind': '/output', 'mode': 'rw'}},
                detach=True,
                remove=True
            )
            container.wait()

            content_parts = []
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.html'):
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            soup = BeautifulSoup(f.read(), "html.parser")
                            text = soup.get_text(separator=" ", strip=True)
                            content_parts.append(text)

            text_content = "\n".join(content_parts)
            doc_type = self._classify_content(text_content)
            if len(text_content) < 500:
                return {"status": "error", "message": "Scraped content too short"}

            document = SourceDocument(
                id=url,
                title=url,
                content=text_content,
                source="website",
                url=url,
                doc_type=doc_type,
                metadata={"depth": depth},
            )
            if not self.memory.check_duplicate(document):
                self.memory.store_document(document)
                await self._extract_concepts_and_relationships(document)
            rmtree(temp_dir)
            return {"status": "success", "document_id": document.id, "type": "website", "url": url}

        except Exception as e:
            self.update_status("error")
            return {"status": "error", "message": str(e)}

    async def _process_github_repo(self, repo_url: str) -> Dict[str, Any]:
        try:
            parts = repo_url.rstrip('/').split('/')
            owner, repo = parts[-2], parts[-1]
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.github.com/repos/{owner}/{repo}/contents") as resp:
                    resp.raise_for_status()
                    contents = await resp.json()

            priority_files = []
            for item in contents:
                if item['name'].lower() == 'readme.md':
                    async with aiohttp.ClientSession() as session:
                        async with session.get(item['download_url']) as resp:
                            content = await resp.text()
                            priority_files.append(content)
                elif item['name'] == 'docs' and item['type'] == 'dir':
                    async with aiohttp.ClientSession() as session:
                        async with session.get(item['url']) as resp:
                            doc_contents = await resp.json()
                            for doc_item in doc_contents:
                                if doc_item['type'] == 'file' and doc_item['name'].endswith('.md'):
                                    async with session.get(doc_item['download_url']) as d_resp:
                                        doc_content = await d_resp.text()
                                        priority_files.append(doc_content)

            text_content = "\n".join(priority_files)
            doc_type = self._classify_content(text_content)
            if len(text_content) < 500:
                return {"status": "error", "message": "Repo content too short"}

            document = SourceDocument(
                id=repo_url,
                title=repo_url,
                content=text_content,
                source="github",
                url=repo_url,
                doc_type=doc_type,
                metadata={},
            )
            if not self.memory.check_duplicate(document):
                self.memory.store_document(document)
                await self._extract_concepts_and_relationships(document)
            return {"status": "success", "document_id": document.id, "type": "github", "url": repo_url}

        except Exception as e:
            self.update_status("error")
            return {"status": "error", "message": str(e)}

    def _classify_content(self, content: str) -> str:
        if "tutorial" in content.lower() or "step by step" in content.lower():
            return "tutorial"
        elif "example" in content.lower() or "code sample" in content.lower():
            return "example"
        return "reference"

    async def _extract_concepts_and_relationships(self, document: SourceDocument):
        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=f"Extract key concepts and relationships from this text: {document.content[:2000]}",
            )
            concepts = response.text.split('\n')
            for concept in concepts:
                if concept.strip():
                    self.memory.store_concept(concept.strip(), document.id)

            relationships = [(concepts[i], concepts[i+1]) for i in range(len(concepts)-1)]
            for rel in relationships:
                self.memory.store_relationship(rel[0], rel[1], "related_to")
        except Exception as e:
            logger.error(f"Failed to extract concepts: {e}")