"""Quiz modes module for different ways to answer exercise questions."""

import base64
import io
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from PIL import Image

from .exercise_extractor import Exercise


class AnswerMode(Enum):
    """Enumeration of available answer modes."""
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT_INPUT = "text_input"
    HANDWRITING = "handwriting"


@dataclass
class QuizResult:
    """Result of a quiz attempt."""
    
    exercise: Exercise
    mode: AnswerMode
    user_answer: str
    is_correct: bool
    correct_answer: str
    time_taken_seconds: float = 0.0


class QuizMode(ABC):
    """Abstract base class for quiz modes."""
    
    @property
    @abstractmethod
    def mode_type(self) -> AnswerMode:
        """Return the mode type."""
        pass
    
    @abstractmethod
    def present_question(self, exercise: Exercise) -> dict:
        """Present the question to the user."""
        pass
    
    @abstractmethod
    def check_answer(self, exercise: Exercise, user_answer: str) -> QuizResult:
        """Check the user's answer."""
        pass


class MultipleChoiceMode(QuizMode):
    """Mode 1: Multiple choice - student chooses from a set of options."""
    
    def __init__(self, num_options: int = 4, shuffle: bool = True):
        """
        Initialize multiple choice mode.
        
        Args:
            num_options: Number of options to present.
            shuffle: Whether to shuffle the options.
        """
        self.num_options = num_options
        self.shuffle = shuffle
    
    @property
    def mode_type(self) -> AnswerMode:
        return AnswerMode.MULTIPLE_CHOICE
    
    def present_question(self, exercise: Exercise) -> dict:
        """
        Present the question with multiple choice options.
        
        Returns:
            Dictionary containing question, blanked answer, and options.
        """
        options = exercise.get_multiple_choice_options(self.num_options)
        
        if self.shuffle:
            random.shuffle(options)
        
        # Label options A, B, C, D, etc.
        labeled_options = {
            chr(65 + i): opt for i, opt in enumerate(options)
        }
        
        return {
            "question_number": exercise.question_number,
            "question_text": exercise.question_text,
            "blanked_answer": exercise.blanked_answer,
            "options": labeled_options,
            "mode": self.mode_type.value
        }
    
    def check_answer(self, exercise: Exercise, user_answer: str) -> QuizResult:
        """
        Check if the selected option is correct.
        
        Args:
            exercise: The exercise being answered.
            user_answer: The user's selected answer (letter or value).
            
        Returns:
            QuizResult with the outcome.
        """
        # Handle both letter selection (A, B, C, D) and direct value
        options = exercise.get_multiple_choice_options(self.num_options)
        correct_answer = exercise.blanked_parts[0] if exercise.blanked_parts else ""
        
        # If user provided a letter, convert to value
        if user_answer.upper() in [chr(65 + i) for i in range(len(options))]:
            idx = ord(user_answer.upper()) - 65
            if idx < len(options):
                user_answer = options[idx]
        
        is_correct = exercise.check_answer(user_answer)
        
        return QuizResult(
            exercise=exercise,
            mode=self.mode_type,
            user_answer=user_answer,
            is_correct=is_correct,
            correct_answer=correct_answer
        )


class TextInputMode(QuizMode):
    """Mode 2: Text input - student types in the answer."""
    
    def __init__(self, case_sensitive: bool = False, strip_whitespace: bool = True):
        """
        Initialize text input mode.
        
        Args:
            case_sensitive: Whether to do case-sensitive comparison.
            strip_whitespace: Whether to strip whitespace from answers.
        """
        self.case_sensitive = case_sensitive
        self.strip_whitespace = strip_whitespace
    
    @property
    def mode_type(self) -> AnswerMode:
        return AnswerMode.TEXT_INPUT
    
    def present_question(self, exercise: Exercise) -> dict:
        """
        Present the question for text input.
        
        Returns:
            Dictionary containing question and blanked answer.
        """
        return {
            "question_number": exercise.question_number,
            "question_text": exercise.question_text,
            "blanked_answer": exercise.blanked_answer,
            "mode": self.mode_type.value,
            "hint": f"Fill in the blank (length: ~{len(exercise.blanked_parts[0]) if exercise.blanked_parts else '?'} characters)"
        }
    
    def check_answer(self, exercise: Exercise, user_answer: str) -> QuizResult:
        """
        Check if the typed answer is correct.
        
        Args:
            exercise: The exercise being answered.
            user_answer: The user's typed answer.
            
        Returns:
            QuizResult with the outcome.
        """
        correct_answer = exercise.blanked_parts[0] if exercise.blanked_parts else ""
        
        user_processed = user_answer
        correct_processed = correct_answer
        
        if self.strip_whitespace:
            user_processed = user_processed.strip()
            correct_processed = correct_processed.strip()
        
        if not self.case_sensitive:
            user_processed = user_processed.lower()
            correct_processed = correct_processed.lower()
        
        is_correct = exercise.check_answer(user_answer)
        
        return QuizResult(
            exercise=exercise,
            mode=self.mode_type,
            user_answer=user_answer,
            is_correct=is_correct,
            correct_answer=correct_answer
        )


class HandwritingMode(QuizMode):
    """Mode 3: Handwriting - student writes answer and takes a picture."""
    
    def __init__(self, use_ocr: bool = True):
        """
        Initialize handwriting mode.
        
        Args:
            use_ocr: Whether to use OCR to convert handwriting to text.
        """
        self.use_ocr = use_ocr
        self._has_tesseract = False
        
        try:
            import pytesseract
            self._has_tesseract = True
        except ImportError:
            pass
    
    @property
    def mode_type(self) -> AnswerMode:
        return AnswerMode.HANDWRITING
    
    def present_question(self, exercise: Exercise) -> dict:
        """
        Present the question for handwriting input.
        
        Returns:
            Dictionary containing question, blanked answer, and instructions.
        """
        return {
            "question_number": exercise.question_number,
            "question_text": exercise.question_text,
            "blanked_answer": exercise.blanked_answer,
            "mode": self.mode_type.value,
            "instructions": "Write your answer on paper and take a picture, or upload an image of your handwritten answer."
        }
    
    def process_image(self, image_source: str | Path | Image.Image | bytes) -> str:
        """
        Process an image to extract handwritten text.
        
        Args:
            image_source: Image path, PIL Image, bytes, or base64 string.
            
        Returns:
            Extracted text from the image.
        """
        # Convert to PIL Image
        if isinstance(image_source, Image.Image):
            img = image_source
        elif isinstance(image_source, bytes):
            img = Image.open(io.BytesIO(image_source))
        elif isinstance(image_source, (str, Path)):
            path = Path(image_source)
            if path.exists():
                img = Image.open(path)
            else:
                # Assume base64 string
                try:
                    img_data = base64.b64decode(str(image_source))
                    img = Image.open(io.BytesIO(img_data))
                except Exception as e:
                    raise ValueError(f"Invalid image source: {e}")
        else:
            raise ValueError(f"Unsupported image source type: {type(image_source)}")
        
        # Perform OCR
        if self.use_ocr and self._has_tesseract:
            import pytesseract
            
            # Preprocess image for better OCR
            img = self._preprocess_image(img)
            
            # Extract text
            text = pytesseract.image_to_string(img)
            return text.strip()
        
        return ""
    
    def _preprocess_image(self, img: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy."""
        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')
        
        # Resize if too small
        min_size = 300
        if img.width < min_size or img.height < min_size:
            scale = max(min_size / img.width, min_size / img.height)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        return img
    
    def check_answer(
        self, 
        exercise: Exercise, 
        user_answer: str | Image.Image | bytes
    ) -> QuizResult:
        """
        Check if the handwritten answer is correct.
        
        Args:
            exercise: The exercise being answered.
            user_answer: The user's answer as text or image.
            
        Returns:
            QuizResult with the outcome.
        """
        correct_answer = exercise.blanked_parts[0] if exercise.blanked_parts else ""
        
        # If answer is an image, perform OCR
        if isinstance(user_answer, (Image.Image, bytes)):
            user_text = self.process_image(user_answer)
        else:
            user_text = str(user_answer)
        
        is_correct = exercise.check_answer(user_text)
        
        return QuizResult(
            exercise=exercise,
            mode=self.mode_type,
            user_answer=user_text,
            is_correct=is_correct,
            correct_answer=correct_answer
        )


class QuizSession:
    """Manages a quiz session with exercises and selected mode."""
    
    def __init__(
        self, 
        exercises: list[Exercise], 
        mode: QuizMode,
        shuffle_exercises: bool = True
    ):
        """
        Initialize a quiz session.
        
        Args:
            exercises: List of exercises to quiz on.
            mode: The quiz mode to use.
            shuffle_exercises: Whether to shuffle the order of exercises.
        """
        self.exercises = list(exercises)
        self.mode = mode
        self.current_index = 0
        self.results: list[QuizResult] = []
        
        if shuffle_exercises:
            random.shuffle(self.exercises)
    
    @property
    def total_questions(self) -> int:
        """Return total number of questions."""
        return len(self.exercises)
    
    @property
    def questions_answered(self) -> int:
        """Return number of questions answered."""
        return len(self.results)
    
    @property
    def correct_answers(self) -> int:
        """Return number of correct answers."""
        return sum(1 for r in self.results if r.is_correct)
    
    @property
    def score_percentage(self) -> float:
        """Return the score as a percentage."""
        if not self.results:
            return 0.0
        return (self.correct_answers / len(self.results)) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if all questions have been answered."""
        return self.current_index >= len(self.exercises)
    
    def get_current_question(self) -> Optional[dict]:
        """Get the current question presentation."""
        if self.is_complete:
            return None
        return self.mode.present_question(self.exercises[self.current_index])
    
    def submit_answer(self, answer: str) -> QuizResult:
        """
        Submit an answer for the current question.
        
        Args:
            answer: The user's answer.
            
        Returns:
            QuizResult for the submitted answer.
        """
        if self.is_complete:
            raise IndexError("No more questions to answer")
        
        exercise = self.exercises[self.current_index]
        result = self.mode.check_answer(exercise, answer)
        self.results.append(result)
        self.current_index += 1
        
        return result
    
    def get_summary(self) -> dict:
        """Get a summary of the quiz session."""
        return {
            "total_questions": self.total_questions,
            "questions_answered": self.questions_answered,
            "correct_answers": self.correct_answers,
            "score_percentage": round(self.score_percentage, 1),
            "mode": self.mode.mode_type.value,
            "results": [
                {
                    "question": r.exercise.question_number,
                    "correct": r.is_correct,
                    "user_answer": r.user_answer,
                    "correct_answer": r.correct_answer
                }
                for r in self.results
            ]
        }


def create_quiz_mode(mode: AnswerMode | str, **kwargs) -> QuizMode:
    """
    Factory function to create a quiz mode.
    
    Args:
        mode: The mode type (enum or string).
        **kwargs: Additional arguments for the mode.
        
    Returns:
        QuizMode instance.
    """
    if isinstance(mode, str):
        mode = AnswerMode(mode)
    
    if mode == AnswerMode.MULTIPLE_CHOICE:
        return MultipleChoiceMode(**kwargs)
    elif mode == AnswerMode.TEXT_INPUT:
        return TextInputMode(**kwargs)
    elif mode == AnswerMode.HANDWRITING:
        return HandwritingMode(**kwargs)
    else:
        raise ValueError(f"Unknown mode: {mode}")
