"""Flask web application for MathFlash."""

import json
import os
import uuid
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request, session

from .ai_processor import AIExerciseProcessor
from .pdf_parser import PDFParser
from .quiz_modes import (
    AnswerMode,
    HandwritingMode,
    MultipleChoiceMode,
    QuizSession,
    TextInputMode,
)


def create_app(config: Optional[dict] = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp/mathflash_uploads')
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
    app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', '')
    
    if config:
        app.config.update(config)
    
    # Ensure upload folder exists
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    
    # Store for exercises (in production, use a proper database)
    app.exercises_store = {}
    app.quiz_sessions = {}
    
    @app.route('/')
    def index():
        """Render the main page."""
        return render_template('index.html')
    
    @app.route('/api/upload', methods=['POST'])
    def upload_pdf():
        """Handle PDF file upload."""
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'File must be a PDF'}), 400
        
        # Generate unique ID for this upload
        upload_id = str(uuid.uuid4())
        
        # Save the file
        upload_path = Path(app.config['UPLOAD_FOLDER']) / f"{upload_id}.pdf"
        file.save(upload_path)
        
        try:
            # Parse the PDF
            parser = PDFParser(use_ocr=True)
            document = parser.parse(upload_path)
            
            # Extract page contents
            pages_content = [page.text for page in document.pages]
            
            # Process with AI
            api_key = app.config.get('OPENAI_API_KEY')
            if api_key:
                processor = AIExerciseProcessor(api_key=api_key)
                exercises = processor.process_document(pages_content)
            else:
                # Fallback to basic extraction
                from .exercise_extractor import ExerciseExtractor
                extractor = ExerciseExtractor()
                exercises = []
                for i, content in enumerate(pages_content, 1):
                    exercises.extend(extractor.extract_from_text(content, i))
            
            # Store exercises
            app.exercises_store[upload_id] = {
                'exercises': exercises,
                'filename': file.filename,
                'total_pages': document.total_pages,
                'pages_content': pages_content
            }
            
            # Store in session
            session['upload_id'] = upload_id
            
            return jsonify({
                'success': True,
                'upload_id': upload_id,
                'filename': file.filename,
                'total_pages': document.total_pages,
                'exercises_found': len(exercises),
                'exercises': [
                    {
                        'id': i,
                        'question_number': ex.question_number,
                        'question_text': ex.question_text[:200] + '...' if len(ex.question_text) > 200 else ex.question_text,
                        'page_number': ex.page_number,
                        'has_answer': bool(ex.full_answer and ex.full_answer != "Answer not found")
                    }
                    for i, ex in enumerate(exercises)
                ]
            })
            
        except Exception as e:
            # Clean up on error
            if upload_path.exists():
                upload_path.unlink()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/exercises/<upload_id>')
    def get_exercises(upload_id: str):
        """Get all exercises for an upload."""
        if upload_id not in app.exercises_store:
            return jsonify({'error': 'Upload not found'}), 404
        
        data = app.exercises_store[upload_id]
        exercises = data['exercises']
        
        return jsonify({
            'upload_id': upload_id,
            'filename': data['filename'],
            'total_pages': data['total_pages'],
            'exercises': [
                {
                    'id': i,
                    'question_number': ex.question_number,
                    'question_text': ex.question_text,
                    'page_number': ex.page_number,
                    'blanked_answer': ex.blanked_answer,
                    'has_answer': bool(ex.full_answer and ex.full_answer != "Answer not found"),
                    'concept_tested': getattr(ex, 'concept_tested', ''),
                    'difficulty_level': getattr(ex, 'difficulty_level', 'medium'),
                    'blanking_rationale': getattr(ex, 'blanking_rationale', '')
                }
                for i, ex in enumerate(exercises)
            ]
        })
    
    @app.route('/api/quiz/start', methods=['POST'])
    def start_quiz():
        """Start a new quiz session."""
        data = request.get_json()
        upload_id = data.get('upload_id') or session.get('upload_id')
        mode = data.get('mode', 'multiple_choice')
        exercise_ids = data.get('exercise_ids')  # Optional: specific exercises to include
        
        if not upload_id or upload_id not in app.exercises_store:
            return jsonify({'error': 'Upload not found'}), 404
        
        stored_data = app.exercises_store[upload_id]
        exercises = stored_data['exercises']
        
        # Filter exercises if specific IDs provided
        if exercise_ids:
            exercises = [ex for i, ex in enumerate(exercises) if i in exercise_ids]
        
        # Filter out exercises without answers
        exercises = [ex for ex in exercises if ex.full_answer and ex.full_answer != "Answer not found"]
        
        if not exercises:
            return jsonify({'error': 'No exercises with answers found'}), 400
        
        # Create quiz mode
        if mode == 'multiple_choice':
            quiz_mode = MultipleChoiceMode(num_options=4)
        elif mode == 'text_input':
            quiz_mode = TextInputMode()
        elif mode == 'handwriting':
            quiz_mode = HandwritingMode()
        else:
            return jsonify({'error': f'Unknown mode: {mode}'}), 400
        
        # Create session
        quiz_session = QuizSession(exercises, quiz_mode, shuffle_exercises=True)
        session_id = str(uuid.uuid4())
        app.quiz_sessions[session_id] = quiz_session
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'total_questions': quiz_session.total_questions,
            'mode': mode,
            'current_question': quiz_session.get_current_question()
        })
    
    @app.route('/api/quiz/<session_id>/question')
    def get_current_question(session_id: str):
        """Get the current question in a quiz session."""
        if session_id not in app.quiz_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        quiz = app.quiz_sessions[session_id]
        question = quiz.get_current_question()
        
        if question is None:
            return jsonify({
                'complete': True,
                'summary': quiz.get_summary()
            })
        
        return jsonify({
            'complete': False,
            'question_index': quiz.current_index + 1,
            'total_questions': quiz.total_questions,
            'question': question
        })
    
    @app.route('/api/quiz/<session_id>/answer', methods=['POST'])
    def submit_answer(session_id: str):
        """Submit an answer for the current question."""
        if session_id not in app.quiz_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        quiz = app.quiz_sessions[session_id]
        
        if quiz.is_complete:
            return jsonify({
                'error': 'Quiz is already complete',
                'summary': quiz.get_summary()
            }), 400
        
        data = request.get_json()
        answer = data.get('answer', '')
        
        # Handle image upload for handwriting mode
        if quiz.mode.mode_type == AnswerMode.HANDWRITING and 'image' in data:
            import base64
            image_data = base64.b64decode(data['image'])
            answer = quiz.mode.process_image(image_data)
        
        result = quiz.submit_answer(answer)
        
        response = {
            'is_correct': result.is_correct,
            'correct_answer': result.correct_answer,
            'user_answer': result.user_answer,
            'questions_answered': quiz.questions_answered,
            'correct_so_far': quiz.correct_answers,
            'score_percentage': round(quiz.score_percentage, 1)
        }
        
        if quiz.is_complete:
            response['complete'] = True
            response['summary'] = quiz.get_summary()
        else:
            response['complete'] = False
            response['next_question'] = quiz.get_current_question()
        
        return jsonify(response)
    
    @app.route('/api/quiz/<session_id>/summary')
    def get_quiz_summary(session_id: str):
        """Get the summary of a quiz session."""
        if session_id not in app.quiz_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        quiz = app.quiz_sessions[session_id]
        return jsonify(quiz.get_summary())
    
    @app.route('/api/reprocess/<upload_id>', methods=['POST'])
    def reprocess_exercise(upload_id: str):
        """Reprocess a specific exercise with AI for better blanking."""
        if upload_id not in app.exercises_store:
            return jsonify({'error': 'Upload not found'}), 404
        
        data = request.get_json()
        exercise_id = data.get('exercise_id')
        
        if exercise_id is None:
            return jsonify({'error': 'exercise_id required'}), 400
        
        stored_data = app.exercises_store[upload_id]
        exercises = stored_data['exercises']
        
        if exercise_id < 0 or exercise_id >= len(exercises):
            return jsonify({'error': 'Invalid exercise_id'}), 400
        
        exercise = exercises[exercise_id]
        
        api_key = app.config.get('OPENAI_API_KEY')
        if not api_key:
            return jsonify({'error': 'AI processing not available (no API key)'}), 400
        
        try:
            processor = AIExerciseProcessor(api_key=api_key)
            updated = processor.create_intelligent_blank(exercise)
            exercises[exercise_id] = updated
            
            return jsonify({
                'success': True,
                'exercise': {
                    'id': exercise_id,
                    'question_number': updated.question_number,
                    'question_text': updated.question_text,
                    'blanked_answer': updated.blanked_answer,
                    'concept_tested': getattr(updated, 'concept_tested', ''),
                    'blanking_rationale': getattr(updated, 'blanking_rationale', '')
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return app


# Create the default app instance
app = create_app()


if __name__ == '__main__':
    import os
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
