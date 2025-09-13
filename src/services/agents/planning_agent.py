from typing import Any, Dict
from google import genai

from services.base_agent import BaseAgent
from services.memory import AgentMemory
from configuration.configuration import Configuration as Config


class PlanningAgent(BaseAgent):
    def __init__(self, config: Config, memory: AgentMemory):
        super().__init__("PlanningAgent", config, memory)
        self.gemini_client = genai.Client()

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.update_status("processing")

        topic = task.get("topic")
        if not topic:
            self.update_status("error")
            return {"status": "error", "message": "Topic is required"}

        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=f"Generate a detailed outline and learning objectives for {topic}. Format as JSON with 'outline' list and 'objectives' list.",
            )
            res_json = eval(response.text)  # Assume safe JSON
            outline = res_json.get("outline", [])
            objectives = res_json.get("objectives", [])
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            outline = [f"Introduction to {topic}", f"Core Concepts", f"Advanced Topics", f"Examples", f"Conclusion"]
            objectives = [f"Understand {topic}", f"Apply {topic}"]

        return {
            "status": "success",
            "topic": topic,
            "outline": outline,
            "objectives": objectives,
        }