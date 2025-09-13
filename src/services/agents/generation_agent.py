from typing import Any, Dict
import asyncio

from services.base_agent import BaseAgent
from services.memory import AgentMemory
from configuration.configuration import Configuration as Config
from models.models import GeneratedContent
from google import genai
from google.genai import types


class GenerationAgent(BaseAgent):
    def __init__(self, config: Config, memory: AgentMemory):
        super().__init__("GenerationAgent", config, memory)
        self.gemini_client = genai.Client()

    async def process(self, task: Dict[str, Any]) -> Any:
        self.update_status("processing")

        content_type = task.get("content_type")
        topic = task.get("topic")
        plan = task.get("plan", {})
        sources = task.get("sources", [])
        recommendations = task.get("recommendations", [])

        if not topic or not content_type:
            self.update_status("error")
            return {"status": "error", "message": "Topic and content_type are required"}

        relevant = self.memory.search_relevant_content(topic, n_results=5)
        context = "\n".join([item['content'] for item in relevant])

        system_instruction = "You are an educational content creator with a clear, engaging voice. Maintain technical accuracy and progressive learning."

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