"""AI-powered exercise extraction and intelligent blanking module."""

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from .exercise_extractor import Exercise


@dataclass
class AIExercise(Exercise):
    """Extended Exercise with AI-generated blanking rationale."""
    
    blanking_rationale: str = ""
    concept_tested: str = ""
    difficulty_level: str = "medium"
    alternative_blanks: list[dict] = field(default_factory=list)


class AIExerciseProcessor:
    """AI-powered processor for intelligent exercise extraction and blanking."""
    
    EXTRACTION_PROMPT = """You are an expert educational content analyzer. Analyze the following textbook page content and extract all exercise questions with their answers.

For each exercise found, provide:
1. question_number: The exercise/question number
2. question_text: The full question text
3. full_answer: The complete answer
4. key_concept: What concept/skill this question tests
5. difficulty: easy/medium/hard

Return your response as a JSON array. If no exercises are found, return an empty array [].

Content to analyze:
---
{content}
---

JSON Response:"""

    BLANKING_PROMPT = """You are an expert educational assessment designer. Given an exercise question and its answer, determine the BEST part to blank out that will:
1. Test the student's understanding of the core concept, not just memorization
2. Require the student to think through the problem
3. Be a key computational result, formula application, or concept

For math problems, blank out:
- Final numerical answers
- Key intermediate calculations
- Variable values that require understanding to derive

For conceptual questions, blank out:
- Key terms that demonstrate understanding
- Cause-effect relationships
- Critical reasoning steps

Question: {question}
Full Answer: {answer}
Concept Being Tested: {concept}

Respond with JSON:
{{
    "blanked_answer": "The answer with ____ replacing the key part",
    "blanked_part": "The exact text that was blanked",
    "rationale": "Why this part tests understanding",
    "distractors": ["plausible wrong answer 1", "plausible wrong answer 2", "plausible wrong answer 3"]
}}

JSON Response:"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the AI processor.
        
        Args:
            api_key: OpenAI API key. If not provided, will try to get from environment.
            model: The OpenAI model to use.
        """
        self.api_key = api_key
        self.model = model
        self._client = None
    
    def _get_client(self):
        """Get or create the OpenAI client."""
        if self._client is None:
            import os
            from openai import OpenAI
            
            api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
            
            self._client = OpenAI(api_key=api_key)
        return self._client
    
    def extract_exercises_from_page(self, page_content: str, page_number: int = 0) -> list[AIExercise]:
        """
        Use AI to extract exercises from a page of content.
        
        Args:
            page_content: The text content of the page.
            page_number: The page number for reference.
            
        Returns:
            List of extracted AIExercise objects.
        """
        if not page_content.strip():
            return []
        
        try:
            client = self._get_client()
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert educational content analyzer. Always respond with valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": self.EXTRACTION_PROMPT.format(content=page_content[:6000])
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content
            exercises_data = self._parse_json_response(result_text)
            
            exercises = []
            for ex_data in exercises_data:
                exercise = AIExercise(
                    question_number=str(ex_data.get("question_number", "")),
                    question_text=ex_data.get("question_text", ""),
                    full_answer=ex_data.get("full_answer", ""),
                    page_number=page_number,
                    concept_tested=ex_data.get("key_concept", ""),
                    difficulty_level=ex_data.get("difficulty", "medium")
                )
                exercises.append(exercise)
            
            return exercises
            
        except Exception as e:
            # Fallback to regex-based extraction
            from .exercise_extractor import ExerciseExtractor
            extractor = ExerciseExtractor()
            basic_exercises = extractor.extract_from_text(page_content, page_number)
            return [
                AIExercise(
                    question_number=ex.question_number,
                    question_text=ex.question_text,
                    full_answer=ex.full_answer,
                    page_number=ex.page_number
                )
                for ex in basic_exercises
            ]
    
    def create_intelligent_blank(self, exercise: AIExercise) -> AIExercise:
        """
        Use AI to create an intelligent blank that tests understanding.
        
        Args:
            exercise: The exercise to process.
            
        Returns:
            Updated AIExercise with intelligent blanking.
        """
        if not exercise.full_answer or exercise.full_answer == "Answer not found":
            return exercise
        
        try:
            client = self._get_client()
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educational assessment designer. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": self.BLANKING_PROMPT.format(
                            question=exercise.question_text,
                            answer=exercise.full_answer,
                            concept=exercise.concept_tested or "general understanding"
                        )
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content
            blanking_data = self._parse_json_response(result_text, expect_array=False)
            
            if blanking_data:
                exercise.blanked_answer = blanking_data.get("blanked_answer", exercise.blanked_answer)
                exercise.blanked_parts = [blanking_data.get("blanked_part", "")]
                exercise.blanking_rationale = blanking_data.get("rationale", "")
                exercise.distractors = blanking_data.get("distractors", [])
            
            return exercise
            
        except Exception:
            # Fallback to default blanking logic
            if not exercise.blanked_answer:
                exercise.blanked_answer, exercise.blanked_parts = exercise._create_blanked_answer()
            return exercise
    
    def process_document(self, pages_content: list[str]) -> list[AIExercise]:
        """
        Process an entire document, extracting and processing all exercises.
        
        Args:
            pages_content: List of page content strings.
            
        Returns:
            List of processed AIExercise objects.
        """
        all_exercises = []
        
        for page_num, content in enumerate(pages_content, 1):
            exercises = self.extract_exercises_from_page(content, page_num)
            
            for exercise in exercises:
                processed = self.create_intelligent_blank(exercise)
                all_exercises.append(processed)
        
        return all_exercises
    
    def _parse_json_response(self, text: str, expect_array: bool = True) -> list | dict:
        """Parse JSON from AI response, handling various formats."""
        text = text.strip()
        
        # Try direct parse first
        try:
            result = json.loads(text)
            if expect_array and isinstance(result, list):
                return result
            elif not expect_array and isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in markdown code blocks
        code_block_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\]|\{[\s\S]*?\})\s*```', text)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find raw JSON
        if expect_array:
            json_match = re.search(r'\[[\s\S]*\]', text)
        else:
            json_match = re.search(r'\{[\s\S]*\}', text)
        
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return [] if expect_array else {}
