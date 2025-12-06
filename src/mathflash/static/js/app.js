// MathFlash Frontend Application

class MathFlash {
    constructor() {
        this.uploadId = null;
        this.sessionId = null;
        this.currentMode = null;
        this.selectedAnswer = null;
        this.handwritingImage = null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupDragDrop();
    }
    
    bindEvents() {
        // File input
        const fileInput = document.getElementById('file-input');
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Mode buttons
        document.querySelectorAll('.btn-mode').forEach(btn => {
            btn.addEventListener('click', () => this.startQuiz(btn.dataset.mode));
        });
        
        // Submit answer
        document.getElementById('submit-answer').addEventListener('click', () => this.submitAnswer());
        
        // Next question
        document.getElementById('next-question').addEventListener('click', () => this.showNextQuestion());
        
        // Results actions
        document.getElementById('retry-quiz').addEventListener('click', () => this.retryQuiz());
        document.getElementById('new-upload').addEventListener('click', () => this.newUpload());
        
        // Text input enter key
        document.getElementById('text-answer').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.submitAnswer();
        });
        
        // Handwriting input
        document.getElementById('handwriting-input').addEventListener('change', (e) => this.handleHandwritingUpload(e));
    }
    
    setupDragDrop() {
        const uploadArea = document.getElementById('upload-area');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.add('drag-over');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.remove('drag-over');
            });
        });
        
        uploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.uploadFile(files[0]);
            }
        });
        
        uploadArea.addEventListener('click', () => {
            document.getElementById('file-input').click();
        });
    }
    
    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.uploadFile(file);
        }
    }
    
    async uploadFile(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            alert('Please select a PDF file.');
            return;
        }
        
        // Show progress
        document.getElementById('upload-area').classList.add('hidden');
        document.getElementById('upload-progress').classList.remove('hidden');
        
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        // Simulate progress for PDF parsing
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            progressFill.style.width = `${progress}%`;
        }, 500);
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            progressText.textContent = 'Uploading and parsing PDF...';
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            clearInterval(progressInterval);
            progressFill.style.width = '100%';
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            progressText.textContent = `Found ${data.exercises_found} exercises!`;
            
            this.uploadId = data.upload_id;
            
            setTimeout(() => {
                this.showExercises(data);
            }, 1000);
            
        } catch (error) {
            clearInterval(progressInterval);
            alert('Error uploading file: ' + error.message);
            this.resetUpload();
        }
    }
    
    resetUpload() {
        document.getElementById('upload-area').classList.remove('hidden');
        document.getElementById('upload-progress').classList.add('hidden');
        document.getElementById('progress-fill').style.width = '0%';
    }
    
    showExercises(data) {
        document.getElementById('upload-section').classList.add('hidden');
        document.getElementById('exercises-section').classList.remove('hidden');
        
        document.getElementById('exercises-info').textContent = 
            `${data.filename} - ${data.total_pages} pages, ${data.exercises_found} exercises found`;
        
        const listEl = document.getElementById('exercises-list');
        listEl.innerHTML = '';
        
        if (data.exercises.length === 0) {
            listEl.innerHTML = '<div class="exercise-item"><p>No exercises found in this PDF. The AI could not identify any exercise questions.</p></div>';
            return;
        }
        
        data.exercises.forEach(ex => {
            const item = document.createElement('div');
            item.className = 'exercise-item';
            item.innerHTML = `
                <span class="exercise-number">Q${ex.question_number}</span>
                <span class="exercise-text">${this.escapeHtml(ex.question_text)}</span>
                <span class="exercise-page">Page ${ex.page_number}</span>
            `;
            listEl.appendChild(item);
        });
    }
    
    async startQuiz(mode) {
        this.currentMode = mode;
        
        try {
            const response = await fetch('/api/quiz/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    upload_id: this.uploadId,
                    mode: mode
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.sessionId = data.session_id;
            
            document.getElementById('exercises-section').classList.add('hidden');
            document.getElementById('quiz-section').classList.remove('hidden');
            
            document.getElementById('quiz-total').textContent = data.total_questions;
            
            this.displayQuestion(data.current_question, 1, data.total_questions);
            
        } catch (error) {
            alert('Error starting quiz: ' + error.message);
        }
    }
    
    displayQuestion(question, questionNum, total) {
        document.getElementById('quiz-question-num').textContent = `Question ${questionNum}`;
        document.getElementById('question-number').textContent = `Q${question.question_number}`;
        document.getElementById('question-text').textContent = question.question_text;
        
        // Format blanked answer with visual blanks
        const blankedAnswer = question.blanked_answer.replace(/____/g, 
            '<span class="blank">____</span>');
        document.getElementById('blanked-answer').innerHTML = blankedAnswer;
        
        // Hide all answer input types
        document.getElementById('mc-options').classList.add('hidden');
        document.getElementById('text-input-container').classList.add('hidden');
        document.getElementById('handwriting-container').classList.add('hidden');
        
        // Show appropriate input type
        if (question.mode === 'multiple_choice') {
            this.displayMultipleChoice(question.options);
        } else if (question.mode === 'text_input') {
            this.displayTextInput(question.hint);
        } else if (question.mode === 'handwriting') {
            this.displayHandwriting(question.instructions);
        }
        
        // Reset state
        this.selectedAnswer = null;
        this.handwritingImage = null;
        document.getElementById('question-card').classList.remove('hidden');
        document.getElementById('feedback-card').classList.add('hidden');
    }
    
    displayMultipleChoice(options) {
        const container = document.getElementById('mc-options');
        container.classList.remove('hidden');
        container.innerHTML = '';
        
        for (const [letter, value] of Object.entries(options)) {
            const option = document.createElement('div');
            option.className = 'mc-option';
            option.dataset.letter = letter;
            option.dataset.value = value;
            option.innerHTML = `
                <span class="mc-option-letter">${letter}</span>
                <span class="mc-option-text">${this.escapeHtml(value)}</span>
            `;
            option.addEventListener('click', () => this.selectOption(option));
            container.appendChild(option);
        }
    }
    
    selectOption(option) {
        document.querySelectorAll('.mc-option').forEach(o => o.classList.remove('selected'));
        option.classList.add('selected');
        this.selectedAnswer = option.dataset.value;
    }
    
    displayTextInput(hint) {
        const container = document.getElementById('text-input-container');
        container.classList.remove('hidden');
        document.getElementById('text-answer').value = '';
        document.getElementById('text-hint').textContent = hint || '';
    }
    
    displayHandwriting(instructions) {
        const container = document.getElementById('handwriting-container');
        container.classList.remove('hidden');
        document.getElementById('handwriting-preview').classList.add('hidden');
        document.getElementById('handwriting-input').value = '';
    }
    
    handleHandwritingUpload(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                this.handwritingImage = event.target.result.split(',')[1]; // Get base64 part
                document.getElementById('handwriting-image').src = event.target.result;
                document.getElementById('handwriting-preview').classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
    }
    
    async submitAnswer() {
        let answer;
        
        if (this.currentMode === 'multiple_choice') {
            if (!this.selectedAnswer) {
                alert('Please select an answer.');
                return;
            }
            answer = this.selectedAnswer;
        } else if (this.currentMode === 'text_input') {
            answer = document.getElementById('text-answer').value.trim();
            if (!answer) {
                alert('Please enter an answer.');
                return;
            }
        } else if (this.currentMode === 'handwriting') {
            if (!this.handwritingImage) {
                alert('Please upload an image of your handwritten answer.');
                return;
            }
            answer = ''; // Will be processed server-side
        }
        
        try {
            const body = { answer };
            if (this.currentMode === 'handwriting' && this.handwritingImage) {
                body.image = this.handwritingImage;
            }
            
            const response = await fetch(`/api/quiz/${this.sessionId}/answer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.showFeedback(data);
            
        } catch (error) {
            alert('Error submitting answer: ' + error.message);
        }
    }
    
    showFeedback(data) {
        document.getElementById('question-card').classList.add('hidden');
        
        const feedbackCard = document.getElementById('feedback-card');
        feedbackCard.classList.remove('hidden', 'correct', 'incorrect');
        feedbackCard.classList.add(data.is_correct ? 'correct' : 'incorrect');
        
        document.getElementById('feedback-text').textContent = 
            data.is_correct ? 'Correct!' : 'Incorrect';
        
        document.getElementById('correct-answer-display').textContent = 
            `Correct answer: ${data.correct_answer}`;
        
        document.getElementById('quiz-score').textContent = 
            `${data.score_percentage}`;
        
        if (data.complete) {
            document.getElementById('next-question').textContent = 'See Results';
            this.quizSummary = data.summary;
        } else {
            document.getElementById('next-question').textContent = 'Next Question';
            this.nextQuestion = data.next_question;
            this.questionsAnswered = data.questions_answered;
        }
    }
    
    showNextQuestion() {
        if (this.quizSummary) {
            this.showResults(this.quizSummary);
        } else {
            const total = parseInt(document.getElementById('quiz-total').textContent);
            this.displayQuestion(this.nextQuestion, this.questionsAnswered + 1, total);
        }
    }
    
    showResults(summary) {
        document.getElementById('quiz-section').classList.add('hidden');
        document.getElementById('results-section').classList.remove('hidden');
        
        document.getElementById('final-score').textContent = summary.score_percentage;
        document.getElementById('correct-count').textContent = summary.correct_answers;
        document.getElementById('total-count').textContent = summary.total_questions;
        
        const detailsEl = document.getElementById('results-details');
        detailsEl.innerHTML = '';
        
        summary.results.forEach(result => {
            const item = document.createElement('div');
            item.className = `result-item ${result.correct ? 'correct' : 'incorrect'}`;
            item.innerHTML = `
                <span class="result-item-icon">${result.correct ? '✅' : '❌'}</span>
                <span>Q${result.question}: Your answer: "${result.user_answer}" ${result.correct ? '' : `(Correct: ${result.correct_answer})`}</span>
            `;
            detailsEl.appendChild(item);
        });
    }
    
    retryQuiz() {
        this.quizSummary = null;
        document.getElementById('results-section').classList.add('hidden');
        document.getElementById('exercises-section').classList.remove('hidden');
    }
    
    newUpload() {
        this.uploadId = null;
        this.sessionId = null;
        this.quizSummary = null;
        
        document.getElementById('results-section').classList.add('hidden');
        document.getElementById('upload-section').classList.remove('hidden');
        this.resetUpload();
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.mathFlash = new MathFlash();
});
