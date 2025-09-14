from typing import Any, Dict
import asyncio
from datetime import datetime

from services.base_agent import BaseAgent
from services.memory import AgentMemory
from configuration.configuration import Configuration as Config, logger
from models.models import GeneratedContent
from google import genai
from google.genai import types


class GenerationAgent(BaseAgent):
    def __init__(self, config: Config, memory: AgentMemory):
        super().__init__("GenerationAgent", config, memory)
        self.gemini_client = genai.Client(api_key=config.gemini_api_key)

        # Content type templates and configurations
        self.content_templates = {
            "youtube": {
                "system_instruction": "You are a YouTube content creator who makes engaging, educational videos. Use timing markers, visual cues, and conversational tone.",
                "format_instructions": "Include timing markers like [00:00], [01:30]. Add visual cues like 'Show on screen:', 'Cut to:', etc.",
                "max_length": 3000
            },
            "tutorial": {
                "system_instruction": "You are a technical writer creating step-by-step tutorials. Be clear, precise, and include practical examples.",
                "format_instructions": "Use numbered steps, code blocks, and clear section headers. Include prerequisites and troubleshooting.",
                "max_length": 5000
            },
            "book": {
                "system_instruction": "You are an educational author writing comprehensive book chapters. Maintain academic rigor while being accessible.",
                "format_instructions": "Include chapter introduction, main sections with subheadings, examples, and chapter summary.",
                "max_length": 8000
            },
            "interactive": {
                "system_instruction": "You are an instructional designer creating interactive learning content with quizzes and exercises.",
                "format_instructions": "Include learning objectives, interactive elements, quizzes, and hands-on exercises.",
                "max_length": 4000
            }
        }

    async def process(self, task: Dict[str, Any]) -> Any:
        """Generate content using advanced prompting and context optimization"""
        self.update_status("processing")
        logger.info(f"🎯 GenerationAgent starting content generation")

        content_type = task.get("content_type")
        topic = task.get("topic")
        plan = task.get("plan", {})
        sources = task.get("sources", [])
        recommendations = task.get("recommendations", [])
        audience_level = task.get("audience_level", "intermediate")
        tone = task.get("tone", "conversational")
        constraints = task.get("constraints", {})

        if not topic or not content_type:
            self.update_status("error")
            return {"status": "error", "message": "Topic and content_type are required"}

        if content_type not in self.content_templates:
            self.update_status("error")
            return {"status": "error", "message": f"Unsupported content type: {content_type}"}

        try:
            # Get relevant context from memory
            relevant_chunks = self.memory.search_relevant_content(topic, n_results=8)
            context = self._optimize_context(relevant_chunks, self.config.max_context_tokens)

            # Build comprehensive prompt
            prompt = self._build_generation_prompt(
                content_type, topic, plan, context, recommendations,
                audience_level, tone, constraints
            )

            # Generate content with streaming
            content_text = await self._generate_with_streaming(prompt, content_type)

            # Post-process content
            processed_content = self._post_process_content(content_text, content_type, constraints)

            # Create content object
            content_obj = GeneratedContent(
                title=self._generate_title(topic, content_type),
                content_type=content_type,
                content=processed_content,
                source_documents=[s.get("document_id") for s in sources if s.get("document_id")],
                metadata={
                    "topic": topic,
                    "audience_level": audience_level,
                    "tone": tone,
                    "constraints": constraints,
                    "recommendations_applied": recommendations,
                    "context_chunks_used": len(relevant_chunks),
                    "generation_timestamp": str(datetime.now()),
                    "content_length": len(processed_content),
                    "word_count": len(processed_content.split())
                },
            )

            content_obj.save()
            self.update_status("completed")
            logger.info(f"✅ Generated {content_type} content: {content_obj.title} ({len(processed_content)} chars)")

            return content_obj

        except Exception as e:
            self.update_status("error")
            logger.error(f"❌ Content generation failed: {e}")

            # Return fallback content
            fallback_content = self._create_fallback_content(topic, content_type, str(e))
            fallback_content.save()
            return fallback_content

    def _optimize_context(self, relevant_chunks: list, max_tokens: int) -> str:
        """Optimize context selection to fit within token limits"""
        if not relevant_chunks:
            return ""

        # Sort by relevance score
        sorted_chunks = sorted(relevant_chunks, key=lambda x: x.get('score', 0), reverse=True)

        context_parts = []
        estimated_tokens = 0

        for chunk in sorted_chunks:
            content = chunk['content']
            # Rough token estimation (1 token ≈ 4 characters)
            chunk_tokens = len(content) // 4

            if estimated_tokens + chunk_tokens > max_tokens:
                break

            context_parts.append(f"Source: {chunk['metadata'].get('document_title', 'Unknown')}\n{content}")
            estimated_tokens += chunk_tokens

        logger.info(f"Selected {len(context_parts)} context chunks (~{estimated_tokens} tokens)")
        return "\n\n---\n\n".join(context_parts)

    def _build_generation_prompt(self, content_type: str, topic: str, plan: dict,
                                 context: str, recommendations: list, audience_level: str,
                                 tone: str, constraints: dict) -> str:
        """Build comprehensive generation prompt"""

        template = self.content_templates[content_type]

        prompt_parts = [
            f"Create {content_type} content about: {topic}",
            f"Target audience: {audience_level}",
            f"Tone and style: {tone}",
            ""
        ]

        # Add outline if available
        if plan.get('outline'):
            prompt_parts.extend([
                "Content Structure:",
                "\n".join(f"- {item}" for item in plan['outline']),
                ""
            ])

        # Add learning objectives
        if plan.get('objectives'):
            prompt_parts.extend([
                "Learning Objectives:",
                "\n".join(f"- {obj}" for obj in plan['objectives']),
                ""
            ])

        # Add context from sources
        if context:
            prompt_parts.extend([
                "Reference Material:",
                context[:4000],  # Limit context length
                ""
            ])

        # Add improvement recommendations
        if recommendations:
            prompt_parts.extend([
                "Improvement Guidelines:",
                "\n".join(f"- {rec}" for rec in recommendations),
                ""
            ])

        # Add constraints
        if constraints:
            constraint_text = []
            if constraints.get('length'):
                constraint_text.append(f"Length: {constraints['length']}")
            if constraints.get('word_count'):
                constraint_text.append(f"Target word count: {constraints['word_count']}")
            if constraints.get('complexity'):
                constraint_text.append(f"Complexity level: {constraints['complexity']}")

            if constraint_text:
                prompt_parts.extend([
                    "Constraints:",
                    ", ".join(constraint_text),
                    ""
                ])

        # Add format instructions
        prompt_parts.extend([
            "Format Requirements:",
            template["format_instructions"],
            "",
            "Generate comprehensive, accurate, and engaging content that follows the structure and meets all requirements."
        ])

        return "\n".join(prompt_parts)

    async def _generate_with_streaming(self, prompt: str, content_type: str) -> str:
        """Generate content with streaming for better performance"""
        template = self.content_templates[content_type]

        try:
            response = self.gemini_client.models.generate_content_stream(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=template["system_instruction"],
                    temperature=0.7,
                    max_output_tokens=template["max_length"],
                    top_p=0.9,
                    top_k=40
                ),
            )

            content_parts = []
            async for chunk in response:
                if chunk.text:
                    content_parts.append(chunk.text)

            return "".join(content_parts)

        except Exception as e:
            logger.error(f"❌ Streaming generation failed: {e}")
            # Fallback to non-streaming
            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=template["system_instruction"],
                    temperature=0.7
                ),
            )
            return response.candidates[0].content.parts[0].text

    def _post_process_content(self, content: str, content_type: str, constraints: dict) -> str:
        """Post-process generated content for quality and formatting"""

        # Remove excessive whitespace
        content = "\n".join(line.strip() for line in content.split("\n"))
        content = content.replace("\n\n\n", "\n\n")

        # Apply word count constraints if specified
        if constraints.get('word_count'):
            target_words = constraints['word_count']
            current_words = len(content.split())

            if current_words > target_words * 1.2:  # 20% over target
                # Truncate content intelligently
                words = content.split()
                content = " ".join(words[:target_words])
                content += "\n\n[Content truncated to meet word count requirements]"

        # Content type specific post-processing
        if content_type == "youtube":
            content = self._format_youtube_script(content)
        elif content_type == "tutorial":
            content = self._format_tutorial(content)
        elif content_type == "book":
            content = self._format_book_chapter(content)
        elif content_type == "interactive":
            content = self._format_interactive_content(content)

        return content.strip()

    def _format_youtube_script(self, content: str) -> str:
        """Format content as YouTube script with timing markers"""
        if not content.startswith("["):
            content = "[00:00] " + content

        # Ensure timing markers are present
        lines = content.split("\n")
        formatted_lines = []

        for line in lines:
            if line.strip() and not line.startswith("[") and not any(
                    marker in line for marker in ["[", "Show on screen:", "Cut to:"]):
                # Add timing marker if missing
                if len(formatted_lines) > 0:
                    formatted_lines.append(line)
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append(line)

        return "\n".join(formatted_lines)

    def _format_tutorial(self, content: str) -> str:
        """Format content as step-by-step tutorial"""
        # Ensure proper step numbering
        lines = content.split("\n")
        formatted_lines = []
        step_counter = 1

        for line in lines:
            if line.strip().startswith(("Step", "##")):
                if not line.strip().startswith(f"Step {step_counter}"):
                    line = f"## Step {step_counter}: " + line.strip().replace("Step", "").replace("##", "").strip()
                    step_counter += 1
            formatted_lines.append(line)

        return "\n".join(formatted_lines)

    def _format_book_chapter(self, content: str) -> str:
        """Format content as book chapter"""
        if not content.startswith("#"):
            content = "# Chapter: " + content.split("\n")[0] + "\n\n" + "\n".join(content.split("\n")[1:])

        return content

    def _format_interactive_content(self, content: str) -> str:
        """Format content with interactive elements"""
        # Ensure interactive elements are properly formatted
        if "quiz" not in content.lower():
            content += "\n\n## Knowledge Check Quiz\n\n1. [Quiz question would be generated here]\n2. [Another quiz question]\n3. [Final quiz question]"

        return content

    def _generate_title(self, topic: str, content_type: str) -> str:
        """Generate appropriate title based on content type"""
        type_prefixes = {
            "youtube": "Video:",
            "tutorial": "Tutorial:",
            "book": "Chapter:",
            "interactive": "Interactive Guide:"
        }

        prefix = type_prefixes.get(content_type, "Content:")
        return f"{prefix} {topic}"

    def _create_fallback_content(self, topic: str, content_type: str, error: str) -> GeneratedContent:
        """Create fallback content when generation fails"""
        fallback_templates = {
            "youtube": f"[00:00] Welcome to this video about {topic}.\n\n[00:30] Unfortunately, we encountered an issue generating the full script.\n\n[01:00] Please try again or contact support.\n\nError: {error}",
            "tutorial": f"# Tutorial: {topic}\n\n## Introduction\n\nThis tutorial was intended to cover {topic}, but encountered a generation error.\n\n## Error Details\n{error}\n\n## Next Steps\nPlease try regenerating the content or contact support.",
            "book": f"# Chapter: {topic}\n\n## Introduction\n\nThis chapter was intended to provide comprehensive coverage of {topic}.\n\n## Generation Error\n\nAn error occurred during content generation: {error}\n\n## Recommendation\n\nPlease try again with different parameters or contact support.",
            "interactive": f"# Interactive Guide: {topic}\n\n## Learning Objectives\n- Understand {topic}\n- Apply concepts practically\n\n## Error Notice\n\nContent generation failed with error: {error}\n\n## Quiz\n1. What should you do when content generation fails?\n   a) Try again\n   b) Contact support\n   c) Both a and b\n\nAnswer: c) Both a and b"
        }

        return GeneratedContent(
            title=f"[ERROR] {self._generate_title(topic, content_type)}",
            content_type=content_type,
            content=fallback_templates.get(content_type, f"Error generating {content_type} for {topic}: {error}"),
            source_documents=[],
            metadata={
                "error": error,
                "fallback": True,
                "generation_timestamp": str(datetime.now())
            }
        )

        prompt_base = f"""Generate {content_type} content for {topic}.
Outline: {chr(10).join(f'- {item}' for item in plan.get('outline', []))}
Objectives: {chr(10).join(f'- {item}' for item in plan.get('objectives', []))}
Context from sources: {context[:4000]}
Improve based on recommendations: {', '.join(recommendations)}
"""

        if content_type == "youtube":
            prompt = prompt_base + "Format as a script with timing markers (e.g., [00:00] Intro)."
        elif content_type == "book":
            prompt = prompt_base + "Format as a chapter with sections and learning objectives."
        elif content_type == "tutorial":
            prompt = prompt_base + "Format as step-by-step guide with examples."
        elif content_type == "interactive":
            prompt = prompt_base + "Include quizzes and exercises."
        else:
            self.update_status("error")
            return {"status": "error", "message": f"Unknown content type: {content_type}"}

        try:
            response = self.gemini_client.models.generate_content_stream(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.7),
            )
            content_text = ""
            async for chunk in response:
                content_text += chunk.text

            content_obj = GeneratedContent(
                id=f"{content_type}_{topic.replace(' ', '_')}_{str(hash(content_text))}",
                title=f"{content_type.capitalize()}: {topic}",
                content_type=content_type,
                content=content_text,
                source_documents=[s.get("document_id") for s in sources],
                metadata={"recommendations_applied": recommendations},
            )
            content_obj.save()
            return content_obj
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            content_obj = GeneratedContent(
                id=f"{content_type}_{topic.replace(' ', '_')}",
                title=f"{content_type.capitalize()}: {topic}",
                content_type=content_type,
                content=f"Placeholder {content_type} for {topic}. Error: {str(e)}",
                source_documents=[],
                metadata={},
            )
            content_obj.save()
            return content_obj