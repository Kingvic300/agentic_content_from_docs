from typing import Any, Dict
import textstat
import re
from datetime import datetime
from google import genai

from services.base_agent import BaseAgent
from services.memory import AgentMemory
from configuration.configuration import Configuration as Config, logger


class QualityAgent(BaseAgent):
    def __init__(self, config: Config, memory: AgentMemory):
        super().__init__("QualityAgent", config, memory)
        self.gemini_client = genai.Client(api_key=config.gemini_api_key)

        # Quality thresholds
        self.thresholds = {
            "min_accuracy": 0.75,
            "min_readability": 60,
            "min_completeness": 0.70,
            "min_engagement": 0.60,
            "min_overall": config.min_quality_score
        }

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive quality assessment with detailed metrics and recommendations"""
        self.update_status("processing")
        logger.info(f"🔍 QualityAgent starting assessment")

        content = task.get("content", "")
        content_type = task.get("content_type", "unknown")
        topic = task.get("topic", "")

        if not content:
            self.update_status("error")
            return {"status": "error", "message": "Content is required"}

        try:
            # Comprehensive quality assessment
            metrics = await self._assess_all_metrics(content, content_type, topic)

            # Generate recommendations
            recommendations = self._generate_recommendations(metrics, content_type)

            # Calculate overall score
            overall_score = self._calculate_overall_score(metrics)

            # Determine if content meets quality standards
            meets_standards = overall_score >= self.thresholds["min_overall"]

            self.update_status("completed")
            logger.info(
                f"✅ Quality assessment complete: {overall_score:.1f}/100 ({'PASS' if meets_standards else 'NEEDS IMPROVEMENT'})")

            return {
                "status": "success",
                "quality_metrics": {
                    "overall_score": overall_score,
                    "technical_accuracy": metrics["accuracy"] * 100,
                    "readability_score": metrics["readability"],
                    "completeness_score": metrics["completeness"] * 100,
                    "engagement_score": metrics["engagement"] * 100,
                    "structure_score": metrics["structure"] * 100,
                    "factual_consistency": metrics["factual_consistency"] * 100
                },
                "detailed_analysis": {
                    "word_count": metrics["word_count"],
                    "sentence_count": metrics["sentence_count"],
                    "paragraph_count": metrics["paragraph_count"],
                    "avg_sentence_length": metrics["avg_sentence_length"],
                    "reading_level": metrics["reading_level"],
                    "content_type_compliance": metrics["content_type_compliance"]
                },
                "recommendations": recommendations,
                "meets_quality_standards": meets_standards,
                "assessment_timestamp": str(datetime.now())
            }

        except Exception as e:
            self.update_status("error")
            logger.error(f"❌ Quality assessment failed: {e}")
            return {
                "status": "error",
                "message": f"Quality assessment failed: {str(e)}",
                "quality_metrics": self._get_fallback_metrics()
            }

    async def _assess_all_metrics(self, content: str, content_type: str, topic: str) -> Dict[str, float]:
        """Comprehensive assessment of all quality metrics"""

        # Basic text metrics
        word_count = len(content.split())
        sentences = re.split(r'[.!?]+', content)
        sentence_count = len([s for s in sentences if s.strip()])
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        avg_sentence_length = word_count / max(sentence_count, 1)

        # Readability metrics
        readability = textstat.flesch_reading_ease(content)
        reading_level = textstat.flesch_kincaid_grade(content)

        # AI-powered assessments
        accuracy = await self._assess_technical_accuracy(content, topic)
        completeness = self._assess_completeness(content, content_type)
        engagement = self._assess_engagement(content, content_type)
        structure = self._assess_structure(content, content_type)
        factual_consistency = await self._assess_factual_consistency(content)
        content_type_compliance = self._assess_content_type_compliance(content, content_type)

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "avg_sentence_length": avg_sentence_length,
            "readability": readability,
            "reading_level": reading_level,
            "accuracy": accuracy,
            "completeness": completeness,
            "engagement": engagement,
            "structure": structure,
            "factual_consistency": factual_consistency,
            "content_type_compliance": content_type_compliance
        }

    async def _assess_technical_accuracy(self, content: str, topic: str) -> float:
        """AI-powered technical accuracy assessment"""
        try:
            accuracy_prompt = f"""
            Assess the technical accuracy of this content about "{topic}".

            Rate on a scale of 0.0 to 1.0 based on:
            - Factual correctness
            - Technical precision
            - Absence of misleading information
            - Consistency with established knowledge

            Content: {content[:2500]}

            Return only a decimal number between 0.0 and 1.0.
            """

            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=accuracy_prompt,
            )

            accuracy_text = response.candidates[0].content.parts[0].text.strip()
            accuracy = float(re.search(r'0\.\d+|1\.0|0\.0', accuracy_text).group())
            return max(0.0, min(1.0, accuracy))

        except Exception as e:
            logger.warning(f"⚠️ AI accuracy assessment failed: {e}")
            return self._fallback_accuracy_check(content)

    async def _assess_factual_consistency(self, content: str) -> float:
        """Check for internal factual consistency"""
        try:
            consistency_prompt = f"""
            Check this content for internal consistency and logical flow.

            Rate on a scale of 0.0 to 1.0 based on:
            - No contradictory statements
            - Logical progression of ideas
            - Consistent terminology usage
            - Coherent narrative flow

            Content: {content[:2500]}

            Return only a decimal number between 0.0 and 1.0.
            """

            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=consistency_prompt,
            )

            consistency_text = response.candidates[0].content.parts[0].text.strip()
            consistency = float(re.search(r'0\.\d+|1\.0|0\.0', consistency_text).group())
            return max(0.0, min(1.0, consistency))

        except Exception as e:
            logger.warning(f"⚠️ Consistency assessment failed: {e}")
            return 0.8  # Default reasonable score

    def _assess_completeness(self, content: str, content_type: str) -> float:
        """Assess content completeness based on type and length"""
        word_count = len(content.split())

        # Expected word counts by content type
        expected_lengths = {
            "youtube": (800, 1500),  # 5-10 minute script
            "tutorial": (1200, 3000),  # Comprehensive tutorial
            "book": (2000, 5000),  # Book chapter
            "interactive": (1000, 2500)  # Interactive content
        }

        min_words, max_words = expected_lengths.get(content_type, (500, 2000))

        # Length-based completeness
        if word_count < min_words * 0.5:
            length_score = 0.3
        elif word_count < min_words:
            length_score = 0.6
        elif word_count <= max_words:
            length_score = 1.0
        else:
            length_score = 0.9  # Slightly penalize excessive length

        # Structure-based completeness
        has_intro = any(word in content.lower()[:500] for word in ["introduction", "welcome", "overview", "begin"])
        has_conclusion = any(word in content.lower()[-500:] for word in ["conclusion", "summary", "recap", "end"])
        has_examples = "example" in content.lower() or "for instance" in content.lower()

        structure_score = (has_intro + has_conclusion + has_examples) / 3

        return (length_score * 0.7) + (structure_score * 0.3)

    def _assess_engagement(self, content: str, content_type: str) -> float:
        """Assess content engagement potential"""
        engagement_indicators = {
            "questions": len(re.findall(r'\?', content)),
            "examples": len(re.findall(r'\bexample\b|\bfor instance\b', content, re.IGNORECASE)),
            "action_words": len(
                re.findall(r'\b(let\'s|try|practice|implement|build|create)\b', content, re.IGNORECASE)),
            "personal_pronouns": len(re.findall(r'\b(you|your|we|our)\b', content, re.IGNORECASE)),
            "exclamations": len(re.findall(r'!', content))
        }

        # Content type specific engagement factors
        type_factors = {
            "youtube": {"questions": 2, "personal_pronouns": 2, "exclamations": 1.5},
            "tutorial": {"examples": 2, "action_words": 2, "questions": 1.5},
            "book": {"examples": 1.5, "questions": 1.2, "action_words": 1},
            "interactive": {"questions": 2.5, "action_words": 2, "examples": 1.5}
        }

        factors = type_factors.get(content_type, {})

        # Calculate weighted engagement score
        total_score = 0
        word_count = len(content.split())

        for indicator, count in engagement_indicators.items():
            normalized_count = count / max(word_count / 100, 1)  # Per 100 words
            weight = factors.get(indicator, 1)
            total_score += normalized_count * weight

        # Normalize to 0-1 scale
        return min(1.0, total_score / 10)

    def _assess_structure(self, content: str, content_type: str) -> float:
        """Assess content structure and organization"""

        # Count structural elements
        headers = len(re.findall(r'^#+\s', content, re.MULTILINE))
        lists = len(re.findall(r'^\s*[-*+]\s|\d+\.\s', content, re.MULTILINE))
        code_blocks = len(re.findall(r'```|`[^`]+`', content))

        # Content type specific structure requirements
        structure_requirements = {
            "youtube": {
                "timing_markers": len(re.findall(r'\[\d{2}:\d{2}\]', content)),
                "visual_cues": len(re.findall(r'show on screen|cut to|visual', content, re.IGNORECASE))
            },
            "tutorial": {
                "steps": len(re.findall(r'step \d+|^\d+\.', content, re.IGNORECASE | re.MULTILINE)),
                "code_examples": code_blocks
            },
            "book": {
                "sections": headers,
                "subsections": len(re.findall(r'^###+\s', content, re.MULTILINE))
            },
            "interactive": {
                "quizzes": len(re.findall(r'quiz|question \d+', content, re.IGNORECASE)),
                "exercises": len(re.findall(r'exercise|practice|try', content, re.IGNORECASE))
            },
        }

        # Calculate structure score
        base_score = min(1.0, (headers + lists) / 5)  # Basic structure

        # Type-specific bonus
        type_reqs = structure_requirements.get(content_type, {})
        type_score = 0

        for req, count in type_reqs.items():
            if count > 0:
                type_score += 0.2

        return min(1.0, base_score + type_score)

    def _assess_content_type_compliance(self, content: str, content_type: str) -> float:
        """Assess how well content matches its intended type"""

        compliance_checks = {
            "youtube": [
                (r'\[\d{2}:\d{2}\]', "timing markers"),
                (r'welcome|hello|today', "conversational opening"),
                (r'subscribe|like|comment', "engagement calls")
            ],
            "tutorial": [
                (r'step \d+|^\d+\.', "numbered steps"),
                (r'```|`[^`]+`', "code examples"),
                (r'prerequisite|requirement', "prerequisites")
            ],
            "book": [
                (r'^#+\s', "chapter structure"),
                (r'introduction|conclusion', "academic structure"),
                (r'figure|table|reference', "academic elements")
            ],
            "interactive": [
                (r'quiz|question', "interactive elements"),
                (r'exercise|practice', "hands-on activities"),
                (r'objective|goal', "learning objectives")
            ]
        }

        checks = compliance_checks.get(content_type, [])
        if not checks:
            return 0.8  # Default score for unknown types

        passed_checks = 0
        for pattern, description in checks:
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                passed_checks += 1

        return passed_checks / len(checks)

    def _generate_recommendations(self, metrics: Dict[str, float], content_type: str) -> list:
        """Generate specific improvement recommendations"""
        recommendations = []

        # Accuracy recommendations
        if metrics["accuracy"] < self.thresholds["min_accuracy"]:
            recommendations.append("Improve technical accuracy - verify facts and technical details")

        # Readability recommendations
        if metrics["readability"] < self.thresholds["min_readability"]:
            recommendations.append("Improve readability - use shorter sentences and simpler vocabulary")

        # Completeness recommendations
        if metrics["completeness"] < self.thresholds["min_completeness"]:
            if metrics["word_count"] < 500:
                recommendations.append("Expand content - add more detailed explanations and examples")
            else:
                recommendations.append("Improve content structure - add introduction and conclusion")

        # Engagement recommendations
        if metrics["engagement"] < self.thresholds["min_engagement"]:
            recommendations.append("Increase engagement - add more examples, questions, and interactive elements")

        # Structure recommendations
        if metrics["structure"] < 0.6:
            recommendations.append("Improve structure - add clear headings and organize content better")

        # Content type specific recommendations
        if metrics["content_type_compliance"] < 0.7:
            type_recommendations = {
                "youtube": "Add timing markers and conversational elements for video format",
                "tutorial": "Include numbered steps and code examples for tutorial format",
                "book": "Add academic structure with proper sections and references",
                "interactive": "Include quizzes, exercises, and learning objectives"
            }
            rec = type_recommendations.get(content_type)
            if rec:
                recommendations.append(rec)

        # Factual consistency recommendations
        if metrics["factual_consistency"] < 0.8:
            recommendations.append("Review content for internal consistency and logical flow")

        return recommendations

    def _calculate_overall_score(self, metrics: Dict[str, float]) -> float:
        """Calculate weighted overall quality score"""
        weights = {
            "accuracy": 0.25,
            "completeness": 0.20,
            "readability": 0.15,
            "engagement": 0.15,
            "structure": 0.15,
            "factual_consistency": 0.10
        }

        # Normalize readability to 0-1 scale
        normalized_readability = max(0, min(1, metrics["readability"] / 100))

        score = (
                metrics["accuracy"] * weights["accuracy"] +
                metrics["completeness"] * weights["completeness"] +
                normalized_readability * weights["readability"] +
                metrics["engagement"] * weights["engagement"] +
                metrics["structure"] * weights["structure"] +
                metrics["factual_consistency"] * weights["factual_consistency"]
        )

        return score * 100  # Convert to percentage

    def _fallback_accuracy_check(self, content: str) -> float:
        """Fallback accuracy assessment using heuristics"""
        # Simple heuristic checks
        error_indicators = ["error", "wrong", "incorrect", "mistake", "bug"]
        positive_indicators = ["correct", "accurate", "precise", "verified"]

        error_count = sum(content.lower().count(word) for word in error_indicators)
        positive_count = sum(content.lower().count(word) for word in positive_indicators)

        # Basic scoring
        if error_count > positive_count:
            return 0.6
        elif positive_count > 0:
            return 0.9
        else:
            return 0.8

    def _get_fallback_metrics(self) -> Dict[str, float]:
        """Return fallback metrics when assessment fails"""
        return {
            "overall_score": 50.0,
            "technical_accuracy": 50.0,
            "readability_score": 50.0,
            "completeness_score": 50.0,
            "engagement_score": 50.0,
            "structure_score": 50.0,
            "factual_consistency": 50.0
        }


def _check_technical_accuracy(text: str) -> float:
    return 0.9 if "error" not in text.lower() else 0.5


def _check_completeness(text: str) -> float:
    return 0.8 if len(text.split()) > 500 else 0.4