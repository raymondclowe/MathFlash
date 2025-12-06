"""Exercise extraction module for finding questions and answers in textbook content."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Exercise:
    """Represents an exercise question with its answer."""
    
    question_number: str
    question_text: str
    full_answer: str
    blanked_answer: str = ""
    blanked_parts: list[str] = field(default_factory=list)
    distractors: list[str] = field(default_factory=list)
    page_number: int = 0
    
    def __post_init__(self):
        if not self.blanked_answer:
            self.blanked_answer, self.blanked_parts = self._create_blanked_answer()
    
    def _create_blanked_answer(self) -> tuple[str, list[str]]:
        """Create a blanked version of the answer by hiding key parts."""
        answer = self.full_answer
        blanked_parts = []
        
        # Pattern 1: Blank out numbers (including decimals and fractions)
        number_pattern = r'-?\d+\.?\d*(?:/\d+)?'
        numbers = re.findall(number_pattern, answer)
        
        if numbers:
            # Pick the most significant number (usually the final answer)
            key_number = numbers[-1] if len(numbers) > 1 else numbers[0]
            blanked_answer = answer.replace(key_number, "____", 1)
            blanked_parts.append(key_number)
            return blanked_answer, blanked_parts
        
        # Pattern 2: Blank out mathematical expressions
        math_pattern = r'[a-zA-Z]\s*[=]\s*[^,.\n]+'
        math_matches = re.findall(math_pattern, answer)
        
        if math_matches:
            key_expr = math_matches[-1]
            # Blank out the right side of the equation
            eq_parts = key_expr.split('=')
            if len(eq_parts) == 2:
                blanked_answer = answer.replace(eq_parts[1].strip(), "____", 1)
                blanked_parts.append(eq_parts[1].strip())
                return blanked_answer, blanked_parts
        
        # Pattern 3: Blank out key words (nouns, technical terms)
        words = answer.split()
        if len(words) > 3:
            # Blank out a word from the middle/end that's significant
            for i in range(len(words) - 1, len(words) // 2, -1):
                word = words[i]
                if len(word) > 3 and word.isalpha():
                    blanked_parts.append(word)
                    words[i] = "____"
                    return " ".join(words), blanked_parts
        
        # Fallback: blank out the last significant word
        for i in range(len(words) - 1, -1, -1):
            word = words[i].strip('.,!?')
            if len(word) > 2:
                blanked_parts.append(word)
                words[i] = "____"
                return " ".join(words), blanked_parts
        
        return answer, []
    
    def get_multiple_choice_options(self, num_options: int = 4) -> list[str]:
        """Generate multiple choice options including the correct answer and distractors."""
        if not self.blanked_parts:
            return []
        
        correct = self.blanked_parts[0]
        options = [correct]
        
        # Add provided distractors
        for d in self.distractors[:num_options - 1]:
            if d not in options:
                options.append(d)
        
        # Generate additional distractors if needed
        while len(options) < num_options:
            distractor = self._generate_distractor(correct, len(options))
            if distractor and distractor not in options:
                options.append(distractor)
            else:
                break
        
        return options
    
    def _generate_distractor(self, correct: str, index: int) -> Optional[str]:
        """Generate a plausible distractor based on the correct answer."""
        # Try to parse as number
        try:
            num = float(correct.replace("/", "."))
            # Generate nearby numbers as distractors
            variations = [
                num * 2,
                num / 2,
                num + 10,
                num - 5,
                num * 1.5,
                -num,
            ]
            if index - 1 < len(variations):
                result = variations[index - 1]
                if result == int(result):
                    return str(int(result))
                return f"{result:.2f}"
        except (ValueError, ZeroDivisionError):
            pass
        
        # For text answers, create variations
        if correct.isalpha():
            # Simple letter substitution or scrambling
            variations = [
                correct[::-1],  # Reversed
                correct.upper() if correct.islower() else correct.lower(),
                correct + "s" if not correct.endswith("s") else correct[:-1],
            ]
            if index - 1 < len(variations):
                return variations[index - 1]
        
        return None
    
    def check_answer(self, user_answer: str) -> bool:
        """Check if the user's answer is correct."""
        if not self.blanked_parts:
            return False
        
        correct = self.blanked_parts[0].lower().strip()
        user = user_answer.lower().strip()
        
        # Exact match
        if user == correct:
            return True
        
        # Numeric comparison (handle floating point)
        try:
            correct_num = float(correct.replace("/", "."))
            user_num = float(user.replace("/", "."))
            return abs(correct_num - user_num) < 0.01
        except ValueError:
            pass
        
        return False


class ExerciseExtractor:
    """Extracts exercise questions from textbook content."""
    
    # Common patterns for exercise sections
    EXERCISE_PATTERNS = [
        r'(?i)(?:exercise|problem|question|example)\s*(\d+[\.\):]?)\s*(.+?)(?=(?:exercise|problem|question|example)\s*\d+|answer|solution|$)',
        r'(?i)(\d+[\.\)])\s*(.+?)(?=\d+[\.\)]|answer|solution|$)',
        r'(?i)(?:Q|q)\.?\s*(\d+)\s*[:\.]?\s*(.+?)(?=(?:Q|q)\.?\s*\d+|answer|$)',
    ]
    
    # Common patterns for answers
    ANSWER_PATTERNS = [
        r'(?i)(?:answer|solution|ans)[\s:]*(\d+[\.\):]?)\s*(.+?)(?=(?:answer|solution|ans)[\s:]*\d+|$)',
        r'(?i)(\d+[\.\)])\s*[=:]\s*(.+?)(?=\d+[\.\)]|$)',
    ]
    
    def extract_from_text(self, text: str, page_number: int = 0) -> list[Exercise]:
        """
        Extract exercises from raw text content.
        
        Args:
            text: The text content to parse.
            page_number: The page number this text came from.
            
        Returns:
            List of extracted Exercise objects.
        """
        exercises = []
        questions = self._extract_questions(text)
        answers = self._extract_answers(text)
        
        # Match questions with answers
        for q_num, q_text in questions.items():
            answer = answers.get(q_num, "")
            if q_text and len(q_text.strip()) > 10:  # Filter very short questions
                exercise = Exercise(
                    question_number=q_num,
                    question_text=q_text.strip(),
                    full_answer=answer.strip() if answer else "Answer not found",
                    page_number=page_number
                )
                exercises.append(exercise)
        
        return exercises
    
    def _extract_questions(self, text: str) -> dict[str, str]:
        """Extract question numbers and their text."""
        questions = {}
        
        for pattern in self.EXERCISE_PATTERNS:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                if len(match) >= 2:
                    q_num = re.sub(r'[^\d]', '', str(match[0]))
                    q_text = str(match[1]).strip()
                    if q_num and q_text and len(q_text) > 10:
                        questions[q_num] = q_text
        
        # Also try line-by-line extraction for numbered items
        # Split by "Answers" or "Solutions" section to avoid capturing answers as questions
        text_parts = re.split(r'(?i)\n\s*(?:answers?|solutions?)\s*:?\s*\n', text)
        question_text = text_parts[0] if text_parts else text
        
        lines = question_text.split('\n')
        current_num = None
        current_text = []
        
        for line in lines:
            # Skip if this looks like an answer section header
            if re.match(r'(?i)^\s*(?:answers?|solutions?)\s*:?\s*$', line):
                break
            
            # Check if line starts with a number
            line_match = re.match(r'^\s*(\d+)[\.\)\s]+(.+)', line)
            if line_match:
                # Save previous question
                if current_num and current_text:
                    combined = ' '.join(current_text)
                    if current_num not in questions and len(combined) > 10:
                        questions[current_num] = combined
                
                current_num = line_match.group(1)
                current_text = [line_match.group(2).strip()]
            elif current_num and line.strip():
                current_text.append(line.strip())
        
        # Save last question
        if current_num and current_text:
            combined = ' '.join(current_text)
            if current_num not in questions and len(combined) > 10:
                questions[current_num] = combined
        
        return questions
    
    def _extract_answers(self, text: str) -> dict[str, str]:
        """Extract answer numbers and their content."""
        answers = {}
        
        for pattern in self.ANSWER_PATTERNS:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                if len(match) >= 2:
                    a_num = re.sub(r'[^\d]', '', str(match[0]))
                    a_text = str(match[1]).strip()
                    if a_num and a_text:
                        answers[a_num] = a_text
        
        # Also try to extract from "Answers:" section
        answer_section_match = re.search(r'(?i)(?:answers?|solutions?)\s*:?\s*\n([\s\S]*?)(?=\n\n|\Z)', text)
        if answer_section_match:
            answer_section = answer_section_match.group(1)
            # Look for numbered answers in this section
            numbered_answers = re.findall(r'(\d+)[\.\)]\s*(.+?)(?=\d+[\.\)]|\Z)', answer_section, re.DOTALL)
            for a_num, a_text in numbered_answers:
                a_text = a_text.strip()
                if a_num and a_text and a_num not in answers:
                    answers[a_num] = a_text
        
        return answers
    
    def extract_with_ai(self, text: str, api_key: Optional[str] = None) -> list[Exercise]:
        """
        Use AI to extract exercises from text (requires OpenAI API key).
        
        This provides better extraction for complex or non-standard formats.
        """
        if not api_key:
            return self.extract_from_text(text)
        
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=api_key)
            
            prompt = f"""Extract all exercise questions and their answers from the following textbook content.
For each exercise, provide:
1. Question number
2. Question text
3. Full answer

Format your response as a JSON array with objects containing:
{{"question_number": "1", "question_text": "...", "full_answer": "..."}}

Content:
{text[:8000]}  # Limit to avoid token limits
"""
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts exercise questions from textbooks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            
            import json
            result_text = response.choices[0].message.content
            
            # Try to parse JSON from the response
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                exercises_data = json.loads(json_match.group())
                exercises = []
                for ex in exercises_data:
                    exercises.append(Exercise(
                        question_number=ex.get("question_number", ""),
                        question_text=ex.get("question_text", ""),
                        full_answer=ex.get("full_answer", "")
                    ))
                return exercises
        except Exception:
            pass
        
        # Fallback to regex extraction
        return self.extract_from_text(text)
