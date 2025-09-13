from typing import Any, Dict
import textstat
from google import genai

from services.base_agent import BaseAgent
from services.memory import AgentMemory
from configuration.configuration import Configuration as Config


class QualityAgent(BaseAgent):
    def __init__(self, config: Config, memory: AgentMemory):
        super().__init__("QualityAgent", config, memory)
        self.gemini_client = genai.Client()

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.update_status("processing")

        content = task.get("content", "")
        if not content:
            self.update_status("error")
            return {"status": "error", "message": "Content is required"}

        try:
            acc_response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=f"Rate technical accuracy of this content on a scale of 0-1: {content[:2000]}",
            )
            accuracy = float(acc_response.text.strip())
        except Exception:
            accuracy = _check_technical_accuracy(content)

        completeness = _check_completeness(content)
        readability = textstat.flesch_reading_ease(content)
        engagement = 0.8 if len(content.split()) > 500 and "example" in content.lower() else 0.5

        score = {
            "readability": readability,
            "accuracy": accuracy,
            "completeness": completeness,
            "engagement": engagement,
        }
        overall = (accuracy + completeness + (readability / 100) + engagement) / 4 * 100

        recs = []
        if accuracy < 0.75:
            recs.append("Improve factual accuracy")
        if completeness < 0.6:
            recs.append("Expand sections")
        if readability < 60:
            recs.append("Simplify language")
        if engagement < 0.6:
            recs.append("Add more examples or interactive elements")

        return {
            "status": "success",
            "quality_metrics": {
                "overall_score": overall,
                "technical_accuracy": accuracy * 100,
                "readability_score": readability,
                "completeness_score": completeness * 100,
            },
            "recommendations": recs
        }


def _check_technical_accuracy(text: str) -> float:
    return 0.9 if "error" not in text.lower() else 0.5


def _check_completeness(text: str) -> float:
    return 0.8 if len(text.split()) > 500 else 0.4