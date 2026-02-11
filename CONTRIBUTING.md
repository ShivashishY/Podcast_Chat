# Contributing to Podcast Chat

Thank you for your interest in contributing to Podcast Chat! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- macOS 10.15+, Windows 10/11, or Linux (Ubuntu 20.04+)
- FFmpeg installed
- Ollama installed (for AI chat)

### Development Setup

**macOS/Linux:**
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/podcast-chat.git
   cd podcast-chat
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your SMALLEST_API_KEY
   ```

5. **Run in development mode**
   ```bash
   FLASK_DEBUG=true python app.py
   ```

**Windows:**
1. Clone the repository
2. Run `Start Podcast Chat.bat` (handles setup automatically)
3. Or manually:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   python app.py
   ```

## Project Structure

```
podcast_chat/
├── app.py              # Main Flask application & API routes
│                       # Includes AI_FEATURE_PROMPTS dictionary with 20+ feature prompts
├── auth.py             # Authentication module (email login)
├── models.py           # SQLAlchemy database models
├── templates/          # Jinja2 HTML templates
│   ├── index.html      # Main app interface (two-column layout, dark/light mode)
│   ├── login.html      # Login page
│   └── signup.html     # Registration page
├── downloads/          # Downloaded audio files (gitignored)
├── transcripts/        # Saved transcripts (gitignored)
├── docs/               # Additional documentation
├── requirements.txt    # Python dependencies
└── tests/              # Test files (if any)
```

## UI Architecture

The main interface (`templates/index.html`) features:

- **Two-column layout**: Left column (YouTube preview + transcript), Right column (Chat + AI Features)
- **Dark/Light mode**: CSS custom properties with `data-theme` attribute, persisted in localStorage
- **History tab**: Tabs switch between "New Download" and "History" views
- **Progress bar**: Animated progress indicator for download (0-50%) and transcription (50-100%)
- **Collapsible sections**: AI features organized in expandable categories
- **Single-action button**: "Transcribe Video" combines download + transcription

## AI Features Architecture

The app includes 20+ AI-powered features for transcript analysis:

- **Backend**: `AI_FEATURE_PROMPTS` dictionary in `app.py` defines prompts for each feature
- **API**: `/api/ai-feature/<podcast_id>` endpoint processes transcripts via Ollama
- **Frontend**: AI Features panel in `index.html` with search/filter functionality

### Adding New AI Features

1. Add a new entry to `AI_FEATURE_PROMPTS` in `app.py`:
   ```python
   "your_feature": {
       "name": "Your Feature Name",
       "prompt": """Your prompt template with {transcript} placeholder."""
   }
   ```

2. Add the feature button in `index.html` under the appropriate category

3. Update `list_ai_features()` endpoint if needed

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Add logging for important operations

## Making Changes

### Branching Strategy

- `main` - stable production code
- `develop` - integration branch for features
- `feature/*` - new features
- `fix/*` - bug fixes

### Pull Request Process

1. Fork the repository
2. Create a feature branch from `develop`
3. Make your changes
4. Test thoroughly
5. Submit a pull request with a clear description

### Commit Messages

Use clear, descriptive commit messages:
```
feat: add support for multiple audio formats
fix: resolve transcription timeout issue
docs: update installation instructions
refactor: improve chunk processing logic
```

## Testing

Before submitting a PR:

1. Test the one-click "Transcribe Video" button with various YouTube URLs
2. Verify progress bar updates correctly (0-50% download, 50-100% transcription)
3. Test the chat feature with different queries
4. Test AI features (Summary, Flashcards, Q&A, etc.)
5. Test dark/light mode toggle and persistence
6. Verify History tab loads and displays past transcriptions
7. Check that user authentication flows work
8. Ensure no sensitive data is logged or exposed

## Reporting Issues

When reporting bugs, please include:

- Python version
- macOS/Linux version
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output

## Feature Requests

Feature requests are welcome! Please:

- Check existing issues first
- Check the [Future Improvements](README.md#-future-improvements) roadmap
- Describe the use case
- Explain the expected behavior
- Consider backward compatibility

### Priority Areas for Contribution

We especially welcome contributions in these areas:

| Area | Examples |
|------|----------|
| **Cloud LLM support** | OpenAI, Groq, Together.ai integration |
| **Export options** | PDF, DOCX, SRT subtitle generation |
| **Speaker diarization** | Integrate Pulse STT speaker ID |
| **Database** | PostgreSQL adapter for production |
| **Deployment** | Docker Compose, Railway/Render configs |

## Security

- Never commit API keys or secrets
- Report security vulnerabilities privately
- Follow secure coding practices

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Questions? Open an issue or reach out to the maintainers.
