from typing import Any, Dict
import json
from datetime import datetime
from google import genai

from services.base_agent import BaseAgent
from services.memory import AgentMemory
from configuration.configuration import Configuration as Config, logger


class PlanningAgent(BaseAgent):
    def __init__(self, config: Config, memory: AgentMemory):
        super().__init__("PlanningAgent", config, memory)
        self.gemini_client = genai.Client(api_key=config.gemini_api_key)

        # Content type specific planning templates
        self.planning_templates = {
            "youtube": {
                "structure": ["Hook/Introduction", "Problem Statement", "Main Content", "Examples/Demos",
                              "Call to Action"],
                "objectives_focus": "engagement and retention",
                "timing_considerations": True
            },
            "tutorial": {
                "structure": ["Prerequisites", "Overview", "Step-by-step Instructions", "Examples", "Troubleshooting",
                              "Next Steps"],
                "objectives_focus": "practical application",
                "timing_considerations": False
            },
            "book": {
                "structure": ["Chapter Introduction", "Theoretical Foundation", "Detailed Explanation", "Case Studies",
                              "Summary"],
                "objectives_focus": "comprehensive understanding",
                "timing_considerations": False
            },
            "interactive": {
                "structure": ["Learning Objectives", "Interactive Content", "Practice Exercises", "Assessment",
                              "Reflection"],
                "objectives_focus": "active learning and assessment",
                "timing_considerations": False
            }
        }

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive content plan with structure and learning objectives"""
        self.update_status("processing")
        logger.info(f"📋 PlanningAgent creating plan")

        topic = task.get("topic")
        content_type = task.get("content_type", "tutorial")
        audience_level = task.get("audience_level", "intermediate")
        constraints = task.get("constraints", {})

        if not topic:
            self.update_status("error")
            return {"status": "error", "message": "Topic is required"}

        try:
            # Get relevant context from memory
            relevant_content = self.memory.search_relevant_content(topic, n_results=5)
            context_summary = self._summarize_context(relevant_content)

            # Create comprehensive planning prompt
            planning_prompt = self._build_planning_prompt(
                topic, content_type, audience_level, constraints, context_summary
            )

            # Generate plan using Gemini
            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=planning_prompt,
            )

            # Parse response
            plan_data = self._parse_planning_response(response.candidates[0].content.parts[0].text)

            # Enhance plan with template-specific elements
            enhanced_plan = self._enhance_plan_with_template(plan_data, content_type, constraints)

            self.update_status("completed")
            logger.info(
                f"✅ Plan created: {len(enhanced_plan.get('outline', []))} sections, {len(enhanced_plan.get('objectives', []))} objectives")

            return {
                "status": "success",
                "topic": topic,
                "content_type": content_type,
                "outline": enhanced_plan.get("outline", []),
                "objectives": enhanced_plan.get("objectives", []),
                "structure_notes": enhanced_plan.get("structure_notes", []),
                "estimated_length": enhanced_plan.get("estimated_length", "medium"),
                "key_concepts": enhanced_plan.get("key_concepts", []),
                "planning_metadata": {
                    "audience_level": audience_level,
                    "constraints": constraints,
                    "context_sources": len(relevant_content),
                    "planning_timestamp": str(datetime.now())
                }
            }

        except Exception as e:
            self.update_status("error")
            logger.error(f"❌ Planning failed: {e}")

            # Return fallback plan
            fallback_plan = self._create_fallback_plan(topic, content_type)
            return {
                "status": "success",
                "topic": topic,
                "content_type": content_type,
                "outline": fallback_plan["outline"],
                "objectives": fallback_plan["objectives"],
                "structure_notes": ["Generated using fallback planning due to AI planning failure"],
                "error": str(e)
            }

    def _summarize_context(self, relevant_content: list) -> str:
        """Summarize relevant context for planning"""
        if not relevant_content:
            return "No relevant context available"

        # Extract key information from top relevant chunks
        context_parts = []
        for item in relevant_content[:3]:  # Use top 3 most relevant
            content = item['content'][:500]  # Limit length
            source = item['metadata'].get('document_title', 'Unknown source')
            context_parts.append(f"From {source}: {content}")

        return "\n\n".join(context_parts)

    def _build_planning_prompt(self, topic: str, content_type: str, audience_level: str,
                               constraints: dict, context: str) -> str:
        """Build comprehensive planning prompt"""

        template = self.planning_templates.get(content_type, self.planning_templates["tutorial"])

        prompt_parts = [
            f"Create a detailed content plan for: {topic}",
            f"Content type: {content_type}",
            f"Target audience: {audience_level}",
            f"Objectives focus: {template['objectives_focus']}",
            ""
        ]

        # Add context if available
        if context and context != "No relevant context available":
            prompt_parts.extend([
                "Reference material context:",
                context[:1500],  # Limit context length
                ""
            ])

        # Add constraints
        if constraints:
            constraint_text = []
            if constraints.get('length'):
                constraint_text.append(f"Length: {constraints['length']}")
            if constraints.get('complexity'):
                constraint_text.append(f"Complexity: {constraints['complexity']}")
            if constraints.get('word_count'):
                constraint_text.append(f"Target word count: {constraints['word_count']}")

            if constraint_text:
                prompt_parts.extend([
                    "Constraints:",
                    ", ".join(constraint_text),
                    ""
                ])

        # Add specific requirements
        prompt_parts.extend([
            "Requirements:",
            f"1. Create a detailed outline with {len(template['structure'])} main sections",
            f"2. Generate 4-6 specific learning objectives",
            f"3. Consider {audience_level} audience level",
            f"4. Focus on {template['objectives_focus']}",
            ""
        ])

        if template.get('timing_considerations'):
            prompt_parts.append("5. Include timing considerations for video format")
            prompt_parts.append("")

        # Format instructions
        prompt_parts.extend([
            "Format your response as JSON with these keys:",
            "- outline: array of section titles/descriptions",
            "- objectives: array of specific learning objectives",
            "- key_concepts: array of main concepts to cover",
            "- structure_notes: array of structural guidance",
            "- estimated_length: 'short', 'medium', or 'long'",
            "",
            "Make the plan comprehensive, logical, and appropriate for the content type and audience."
        ])

        return "\n".join(prompt_parts)

    def _parse_planning_response(self, response_text: str) -> dict:
        """Parse Gemini response into structured plan data"""
        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
            else:
                # Fallback: parse structured text
                return self._parse_structured_text(response_text)

        except json.JSONDecodeError:
            logger.warning("⚠️ Failed to parse JSON response, using text parsing")
            return self._parse_structured_text(response_text)

    def _parse_structured_text(self, text: str) -> dict:
        """Parse structured text response when JSON parsing fails"""
        lines = text.split('\n')

        outline = []
        objectives = []
        key_concepts = []
        structure_notes = []

        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect sections
            if 'outline' in line.lower():
                current_section = 'outline'
                continue
            elif 'objective' in line.lower():
                current_section = 'objectives'
                continue
            elif 'concept' in line.lower():
                current_section = 'concepts'
                continue
            elif 'note' in line.lower() or 'structure' in line.lower():
                current_section = 'notes'
                continue

            # Extract content based on current section
            if line.startswith(('-', '*', '•')) or line[0].isdigit():
                content = line.lstrip('-*•0123456789. ')

                if current_section == 'outline':
                    outline.append(content)
                elif current_section == 'objectives':
                    objectives.append(content)
                elif current_section == 'concepts':
                    key_concepts.append(content)
                elif current_section == 'notes':
                    structure_notes.append(content)

        return {
            "outline": outline,
            "objectives": objectives,
            "key_concepts": key_concepts,
            "structure_notes": structure_notes,
            "estimated_length": "medium"
        }

    def _enhance_plan_with_template(self, plan_data: dict, content_type: str, constraints: dict) -> dict:
        """Enhance plan with content type specific elements"""
        template = self.planning_templates.get(content_type, self.planning_templates["tutorial"])

        # Ensure minimum outline structure
        if len(plan_data.get("outline", [])) < 3:
            plan_data["outline"] = template["structure"]

        # Ensure minimum objectives
        if len(plan_data.get("objectives", [])) < 3:
            topic = plan_data.get("topic", "the subject")
            default_objectives = [
                f"Understand the fundamental concepts of {topic}",
                f"Apply {topic} in practical scenarios",
                f"Identify best practices and common pitfalls"
            ]
            plan_data["objectives"] = default_objectives

        # Add content type specific enhancements
        if content_type == "youtube":
            plan_data["structure_notes"] = plan_data.get("structure_notes", []) + [
                "Include engaging hook in first 30 seconds",
                "Add timing markers throughout script",
                "Include call-to-action at the end"
            ]
        elif content_type == "tutorial":
            plan_data["structure_notes"] = plan_data.get("structure_notes", []) + [
                "Include prerequisites section",
                "Provide step-by-step instructions",
                "Add troubleshooting section"
            ]
        elif content_type == "book":
            plan_data["structure_notes"] = plan_data.get("structure_notes", []) + [
                "Include chapter introduction and summary",
                "Provide comprehensive theoretical background",
                "Include case studies and examples"
            ]
        elif content_type == "interactive":
            plan_data["structure_notes"] = plan_data.get("structure_notes", []) + [
                "Include interactive exercises",
                "Add knowledge check quizzes",
                "Provide hands-on practice opportunities"
            ]

        # Apply constraints
        if constraints.get("length") == "short":
            plan_data["outline"] = plan_data["outline"][:3]  # Limit sections
            plan_data["estimated_length"] = "short"
        elif constraints.get("length") == "long":
            plan_data["estimated_length"] = "long"

        return plan_data

    def _create_fallback_plan(self, topic: str, content_type: str) -> dict:
        """Create fallback plan when AI planning fails"""
        template = self.planning_templates.get(content_type, self.planning_templates["tutorial"])

        # Create basic outline based on template
        outline = [section.replace("Main Content", f"{topic} Fundamentals") for section in template["structure"]]

        # Create basic objectives
        objectives = [
            f"Understand the core concepts of {topic}",
            f"Learn practical applications of {topic}",
            f"Identify best practices and common challenges",
            f"Gain confidence in applying {topic} knowledge"
        ]

        return {
            "outline": outline,
            "objectives": objectives,
            "key_concepts": [topic, "best practices", "practical application"],
            "structure_notes": ["Fallback plan generated due to AI planning failure"],
            "estimated_length": "medium"
        }