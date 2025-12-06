"""Tests for the Flask web application."""

import json
import pytest
from io import BytesIO

from mathflash.web_app import create_app


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'UPLOAD_FOLDER': '/tmp/mathflash_test_uploads',
    })
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestIndexRoute:
    """Tests for the index route."""
    
    def test_index_returns_html(self, client):
        """Test that index returns HTML page."""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'MathFlash' in response.data


class TestUploadEndpoint:
    """Tests for the upload endpoint."""
    
    def test_upload_no_file(self, client):
        """Test upload with no file."""
        response = client.post('/api/upload')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_upload_empty_filename(self, client):
        """Test upload with empty filename."""
        response = client.post(
            '/api/upload',
            data={'file': (BytesIO(b''), '')},
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 400
    
    def test_upload_non_pdf(self, client):
        """Test upload with non-PDF file."""
        response = client.post(
            '/api/upload',
            data={'file': (BytesIO(b'test content'), 'test.txt')},
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'PDF' in data['error']


class TestExercisesEndpoint:
    """Tests for the exercises endpoint."""
    
    def test_get_exercises_not_found(self, client):
        """Test getting exercises for non-existent upload."""
        response = client.get('/api/exercises/nonexistent-id')
        
        assert response.status_code == 404


class TestQuizEndpoints:
    """Tests for quiz-related endpoints."""
    
    def test_start_quiz_no_upload(self, client):
        """Test starting quiz without upload."""
        response = client.post(
            '/api/quiz/start',
            data=json.dumps({'upload_id': 'nonexistent'}),
            content_type='application/json'
        )
        
        assert response.status_code == 404
    
    def test_get_question_no_session(self, client):
        """Test getting question without valid session."""
        response = client.get('/api/quiz/nonexistent-session/question')
        
        assert response.status_code == 404
    
    def test_submit_answer_no_session(self, client):
        """Test submitting answer without valid session."""
        response = client.post(
            '/api/quiz/nonexistent-session/answer',
            data=json.dumps({'answer': 'test'}),
            content_type='application/json'
        )
        
        assert response.status_code == 404
    
    def test_get_summary_no_session(self, client):
        """Test getting summary without valid session."""
        response = client.get('/api/quiz/nonexistent-session/summary')
        
        assert response.status_code == 404
