# MathFlash

📚 Automated math flash card question training from PDF textbooks

## Overview

MathFlash transforms your PDF textbooks into interactive learning experiences. Upload a PDF containing exercises, and the AI will:

1. **Parse the PDF** - Supports both text-based and scanned/image-based PDFs (with OCR)
2. **Extract Exercises** - Automatically identifies questions and answers
3. **Intelligent Blanking** - Uses AI to determine what parts of answers to blank out, ensuring students truly understand the concepts rather than just memorizing
4. **Three Answer Modes**:
   - 🔘 **Multiple Choice** - Select from options
   - ⌨️ **Type Answer** - Type in your answer
   - ✍️ **Handwriting** - Write your answer on paper and take a photo

## Installation

### Prerequisites

- Python 3.9 or higher
- Tesseract OCR (optional, for image-based PDFs)
- OpenRouter API key (optional, for AI-powered extraction and blanking - uses Gemini 2.0 Flash by default)

### Install from Source

```bash
git clone https://github.com/raymondclowe/MathFlash.git
cd MathFlash
pip install -e .
```

### Install Dependencies Only

```bash
pip install -r requirements.txt
```

### Install Tesseract OCR (Optional)

For Ubuntu/Debian:
```bash
sudo apt-get install tesseract-ocr
```

For macOS:
```bash
brew install tesseract
```

## Configuration

Set the following environment variables:

```bash
# Required for AI-powered features (OpenRouter API)
export OPENROUTER_API_KEY="your-openrouter-api-key"

# Optional: Custom upload folder
export UPLOAD_FOLDER="/path/to/uploads"

# Optional: Production secret key
export SECRET_KEY="your-secret-key"
```

### Getting an OpenRouter API Key

1. Go to [OpenRouter](https://openrouter.ai/)
2. Sign up for an account
3. Generate an API key from the dashboard
4. Set it as the `OPENROUTER_API_KEY` environment variable

The default model is **Gemini 2.0 Flash** (`google/gemini-2.0-flash-001`), which provides excellent performance for exercise extraction and intelligent blanking.

## Running the Application

### Start the Flask Server

```bash
# Development mode (with debug enabled)
export FLASK_DEBUG=true
python src/mathflash/web_app.py

# Or using Flask CLI
cd src/mathflash
python -m flask --app web_app run --debug

# Production mode (debug disabled by default)
python src/mathflash/web_app.py
```

The application will be available at `http://localhost:5000`

### Using the Web Interface

1. **Upload PDF**: Drag and drop or click to select your textbook PDF
2. **Review Exercises**: See all extracted exercises with their page numbers
3. **Choose Mode**: Select how you want to answer questions
4. **Take Quiz**: Answer questions and get instant feedback
5. **View Results**: See your score and review answers

## API Endpoints

### Upload PDF
```
POST /api/upload
Content-Type: multipart/form-data
Body: file (PDF)
```

### Get Exercises
```
GET /api/exercises/<upload_id>
```

### Start Quiz
```
POST /api/quiz/start
Content-Type: application/json
Body: {
  "upload_id": "...",
  "mode": "multiple_choice|text_input|handwriting"
}
```

### Submit Answer
```
POST /api/quiz/<session_id>/answer
Content-Type: application/json
Body: {
  "answer": "user's answer",
  "image": "base64 encoded image (for handwriting mode)"
}
```

## Project Structure

```
MathFlash/
├── src/mathflash/
│   ├── __init__.py
│   ├── pdf_parser.py       # PDF parsing with OCR support
│   ├── exercise_extractor.py   # Regex-based extraction
│   ├── ai_processor.py     # AI-powered extraction and blanking
│   ├── quiz_modes.py       # Three answer modes
│   ├── web_app.py          # Flask application
│   ├── templates/
│   │   └── index.html      # Main web interface
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## How AI Blanking Works

The AI analyzes each exercise to determine the optimal part to blank out:

1. **For math problems**: Blanks out final numerical answers or key intermediate calculations
2. **For conceptual questions**: Blanks out key terms or relationships
3. **Generates distractors**: Creates plausible wrong answers for multiple choice

The goal is to ensure students demonstrate understanding of the problem-solving process, not just recall of answers.

## Development

### Run Tests

```bash
pytest tests/
```

### Run with Coverage

```bash
pytest --cov=mathflash tests/
```

## License

MIT License
