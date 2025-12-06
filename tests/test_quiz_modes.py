"""Tests for the quiz modes module."""

import pytest
from mathflash.exercise_extractor import Exercise
from mathflash.quiz_modes import (
    AnswerMode,
    MultipleChoiceMode,
    TextInputMode,
    HandwritingMode,
    QuizSession,
    create_quiz_mode,
)


class TestMultipleChoiceMode:
    """Tests for multiple choice mode."""
    
    def test_present_question(self):
        """Test presenting a question with options."""
        mode = MultipleChoiceMode(num_options=4)
        exercise = Exercise(
            question_number="1",
            question_text="What is 2 + 2?",
            full_answer="4"
        )
        
        presentation = mode.present_question(exercise)
        
        assert "question_number" in presentation
        assert "question_text" in presentation
        assert "options" in presentation
        assert presentation["mode"] == "multiple_choice"
    
    def test_check_answer_correct(self):
        """Test checking a correct answer."""
        mode = MultipleChoiceMode()
        exercise = Exercise(
            question_number="1",
            question_text="What is 2 + 2?",
            full_answer="4"
        )
        
        result = mode.check_answer(exercise, "4")
        
        assert result.is_correct is True
        assert result.mode == AnswerMode.MULTIPLE_CHOICE
    
    def test_check_answer_incorrect(self):
        """Test checking an incorrect answer."""
        mode = MultipleChoiceMode()
        exercise = Exercise(
            question_number="1",
            question_text="What is 2 + 2?",
            full_answer="4"
        )
        
        result = mode.check_answer(exercise, "5")
        
        assert result.is_correct is False


class TestTextInputMode:
    """Tests for text input mode."""
    
    def test_present_question(self):
        """Test presenting a question for text input."""
        mode = TextInputMode()
        exercise = Exercise(
            question_number="1",
            question_text="What is 3 + 3?",
            full_answer="6"
        )
        
        presentation = mode.present_question(exercise)
        
        assert "question_text" in presentation
        assert "blanked_answer" in presentation
        assert presentation["mode"] == "text_input"
    
    def test_check_answer_with_whitespace(self):
        """Test that whitespace is handled correctly."""
        mode = TextInputMode(strip_whitespace=True)
        exercise = Exercise(
            question_number="1",
            question_text="What is 3 + 3?",
            full_answer="6"
        )
        
        result = mode.check_answer(exercise, "  6  ")
        
        assert result.is_correct is True


class TestHandwritingMode:
    """Tests for handwriting mode."""
    
    def test_present_question(self):
        """Test presenting a question for handwriting."""
        mode = HandwritingMode(use_ocr=False)
        exercise = Exercise(
            question_number="1",
            question_text="What is 4 + 4?",
            full_answer="8"
        )
        
        presentation = mode.present_question(exercise)
        
        assert "instructions" in presentation
        assert presentation["mode"] == "handwriting"
    
    def test_check_answer_with_text(self):
        """Test checking a text answer (bypass OCR)."""
        mode = HandwritingMode(use_ocr=False)
        exercise = Exercise(
            question_number="1",
            question_text="What is 4 + 4?",
            full_answer="8"
        )
        
        result = mode.check_answer(exercise, "8")
        
        assert result.is_correct is True


class TestQuizSession:
    """Tests for quiz session management."""
    
    def get_sample_exercises(self):
        """Create sample exercises for testing."""
        return [
            Exercise("1", "What is 1 + 1?", "2"),
            Exercise("2", "What is 2 + 2?", "4"),
            Exercise("3", "What is 3 + 3?", "6"),
        ]
    
    def test_session_creation(self):
        """Test creating a quiz session."""
        exercises = self.get_sample_exercises()
        mode = TextInputMode()
        
        session = QuizSession(exercises, mode, shuffle_exercises=False)
        
        assert session.total_questions == 3
        assert session.questions_answered == 0
        assert session.is_complete is False
    
    def test_get_current_question(self):
        """Test getting the current question."""
        exercises = self.get_sample_exercises()
        mode = TextInputMode()
        session = QuizSession(exercises, mode, shuffle_exercises=False)
        
        question = session.get_current_question()
        
        assert question is not None
        assert "question_text" in question
    
    def test_submit_answer(self):
        """Test submitting an answer."""
        exercises = self.get_sample_exercises()
        mode = TextInputMode()
        session = QuizSession(exercises, mode, shuffle_exercises=False)
        
        result = session.submit_answer("2")
        
        assert session.questions_answered == 1
        assert result.is_correct is True
    
    def test_score_calculation(self):
        """Test score percentage calculation."""
        exercises = self.get_sample_exercises()
        mode = TextInputMode()
        session = QuizSession(exercises, mode, shuffle_exercises=False)
        
        session.submit_answer("2")  # Correct
        session.submit_answer("5")  # Incorrect
        
        assert session.correct_answers == 1
        assert session.score_percentage == 50.0
    
    def test_session_completion(self):
        """Test session completion."""
        exercises = self.get_sample_exercises()
        mode = TextInputMode()
        session = QuizSession(exercises, mode, shuffle_exercises=False)
        
        session.submit_answer("2")
        session.submit_answer("4")
        session.submit_answer("6")
        
        assert session.is_complete is True
        assert session.get_current_question() is None
    
    def test_get_summary(self):
        """Test getting session summary."""
        exercises = self.get_sample_exercises()
        mode = TextInputMode()
        session = QuizSession(exercises, mode, shuffle_exercises=False)
        
        session.submit_answer("2")
        session.submit_answer("4")
        
        summary = session.get_summary()
        
        assert summary["total_questions"] == 3
        assert summary["questions_answered"] == 2
        assert summary["correct_answers"] == 2
        assert "results" in summary


class TestCreateQuizMode:
    """Tests for the quiz mode factory function."""
    
    def test_create_multiple_choice(self):
        """Test creating multiple choice mode."""
        mode = create_quiz_mode(AnswerMode.MULTIPLE_CHOICE)
        assert isinstance(mode, MultipleChoiceMode)
    
    def test_create_text_input(self):
        """Test creating text input mode."""
        mode = create_quiz_mode(AnswerMode.TEXT_INPUT)
        assert isinstance(mode, TextInputMode)
    
    def test_create_handwriting(self):
        """Test creating handwriting mode."""
        mode = create_quiz_mode(AnswerMode.HANDWRITING)
        assert isinstance(mode, HandwritingMode)
    
    def test_create_from_string(self):
        """Test creating mode from string."""
        mode = create_quiz_mode("multiple_choice")
        assert isinstance(mode, MultipleChoiceMode)
    
    def test_create_unknown_mode(self):
        """Test that unknown mode raises error."""
        with pytest.raises(ValueError):
            create_quiz_mode("unknown_mode")
