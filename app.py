"""
Podcast Chat App - Download YouTube audio, transcribe, and chat with podcasts

A production-ready application that leverages Smallest AI's Pulse STT API
for accurate speech-to-text transcription, combined with local LLM (Ollama)
for intelligent podcast conversations.

Author: Shivashish Jaiswal
License: MIT
"""
import os
import uuid
import json
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import yt_dlp
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('podcast_chat.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'downloads'
app.config['TRANSCRIPTS_FOLDER'] = Path(__file__).parent / 'transcripts'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# Create directories
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['TRANSCRIPTS_FOLDER'].mkdir(exist_ok=True)

# Initialize authentication
from auth import init_auth
from flask_login import login_required, current_user
init_auth(app)

# Smallest AI API configuration
SMALLEST_API_KEY = os.environ.get("SMALLEST_API_KEY")
SMALLEST_API_URL = "https://waves-api.smallest.ai/api/v1/pulse/get_text"

# Ollama configuration (local LLM)
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# In-memory storage for transcripts (use database in production)
podcasts_db = {}

# AI Feature prompts for transcript processing
AI_FEATURE_PROMPTS = {
    # Popular Features
    "summary": {
        "name": "Summary",
        "prompt": """Create a comprehensive summary of this podcast/video transcript. Include:
- Main topic and purpose
- Key points discussed
- Important conclusions or takeaways
- Any action items mentioned

Transcript:
{transcript}

Provide a well-structured summary:"""
    },
    "key_insights": {
        "name": "Key Insights",
        "prompt": """Extract the main takeaways and key insights from this transcript. Focus on:
- Core messages and themes
- Important learnings
- Actionable insights
- Unique perspectives shared

Transcript:
{transcript}

List the key insights:"""
    },
    "clean_transcript": {
        "name": "Clean Transcript",
        "prompt": """Clean this transcript by removing filler words (um, uh, like, you know, etc.), false starts, repetitions, and verbal tics while preserving the original meaning and flow of conversation.

Original transcript:
{transcript}

Cleaned transcript:"""
    },
    "proper_notes": {
        "name": "Proper Notes",
        "prompt": """Create comprehensive, well-organized notes from this transcript. Include:
- Main headings and subheadings
- Bullet points for key information
- Important definitions or concepts
- Notable examples or case studies

Transcript:
{transcript}

Organized notes:"""
    },
    
    # Basic Content
    "micro_summary": {
        "name": "Micro Summary",
        "prompt": """Create a very brief 2-3 sentence summary of this transcript capturing only the most essential point.

Transcript:
{transcript}

Micro summary:"""
    },
    "short_summary": {
        "name": "Short Summary",
        "prompt": """Create a short paragraph summary (4-6 sentences) of this transcript highlighting the main topic and key points.

Transcript:
{transcript}

Short summary:"""
    },
    "bullet_points": {
        "name": "Bullet Points",
        "prompt": """Convert this transcript into clear, concise bullet points. Each bullet should capture one distinct idea or piece of information.

Transcript:
{transcript}

Bullet points:"""
    },
    "notable_quotes": {
        "name": "Notable Quotes",
        "prompt": """Extract the most notable, impactful, or memorable quotes from this transcript. Include quotes that are:
- Insightful or thought-provoking
- Memorable or quotable
- Key statements that represent main ideas

Transcript:
{transcript}

Notable quotes:"""
    },
    
    # Analysis
    "extract_ideas": {
        "name": "Extract Ideas",
        "prompt": """Extract all distinct ideas mentioned in this transcript. Categorize them by:
- Main ideas
- Supporting ideas
- Novel or unique ideas
- Ideas for further exploration

Transcript:
{transcript}

Extracted ideas:"""
    },
    "extract_insights": {
        "name": "Extract Insights",
        "prompt": """Identify and explain the deeper insights from this transcript. Look for:
- Hidden meanings or implications
- Connections between concepts
- Lessons learned
- Strategic insights

Transcript:
{transcript}

Deep insights:"""
    },
    "extract_patterns": {
        "name": "Extract Patterns",
        "prompt": """Identify recurring patterns, themes, and structures in this transcript:
- Repeated concepts or ideas
- Common threads
- Structural patterns in arguments
- Recurring examples or references

Transcript:
{transcript}

Patterns identified:"""
    },
    "extract_wisdom": {
        "name": "Extract Wisdom",
        "prompt": """Extract timeless wisdom and life lessons from this transcript. Focus on:
- Universal truths
- Practical wisdom
- Life advice
- Principles that can be applied broadly

Transcript:
{transcript}

Wisdom extracted:"""
    },
    
    # Study & Education
    "flashcards": {
        "name": "Flashcards",
        "prompt": """Create study flashcards from this transcript. Format each as:
Q: [Question]
A: [Answer]

Create 10-15 flashcards covering the main concepts, definitions, and key facts.

Transcript:
{transcript}

Flashcards:"""
    },
    "concept_map": {
        "name": "Concept Map",
        "prompt": """Create a text-based concept map showing the relationships between ideas in this transcript. Use this format:
[Main Concept]
├── [Related Concept 1]
│   ├── [Sub-concept]
│   └── [Sub-concept]
├── [Related Concept 2]
└── [Related Concept 3]

Transcript:
{transcript}

Concept map:"""
    },
    "qa": {
        "name": "Q&A",
        "prompt": """Generate comprehensive Q&A pairs based on this transcript. Include:
- Factual questions
- Conceptual questions
- Application questions
- Analysis questions

Transcript:
{transcript}

Q&A pairs:"""
    },
    "outline_notes": {
        "name": "Outline Notes",
        "prompt": """Create a structured outline of this transcript using Roman numerals, letters, and numbers:
I. Main Topic
   A. Subtopic
      1. Detail
      2. Detail
   B. Subtopic

Transcript:
{transcript}

Outline:"""
    },
    "cornell_notes": {
        "name": "Cornell Notes",
        "prompt": """Format this transcript into Cornell Notes style:

CUES/QUESTIONS | NOTES
----------------|-------
[Key questions] | [Detailed notes]

SUMMARY:
[Brief summary of main points]

Transcript:
{transcript}

Cornell Notes:"""
    },
    "rapid_logging": {
        "name": "Rapid Logging",
        "prompt": """Convert this transcript into rapid logging (bullet journal) format using:
• Tasks/Actions
- Notes/Facts
○ Events
* Important points

Transcript:
{transcript}

Rapid log:"""
    },
    "t_note_method": {
        "name": "T-Note Method",
        "prompt": """Create T-Notes from this transcript:

MAIN IDEAS          | DETAILS
--------------------|--------------------
[Key concept 1]     | [Supporting details]
[Key concept 2]     | [Supporting details]

Transcript:
{transcript}

T-Notes:"""
    },
    "charting_method": {
        "name": "Charting Method",
        "prompt": """Create a chart/table organizing information from this transcript:

| Category | Key Point | Details | Examples |
|----------|-----------|---------|----------|

Transcript:
{transcript}

Chart:"""
    },
    "qec_method": {
        "name": "QEC Method",
        "prompt": """Apply the QEC (Question, Evidence, Conclusion) method to this transcript:

QUESTION: What is being discussed?
EVIDENCE: What facts/examples support it?
CONCLUSION: What can we conclude?

Transcript:
{transcript}

QEC Analysis:"""
    },
    "qa_split_page": {
        "name": "Q&A Split Page",
        "prompt": """Create a split-page Q&A study format:

LEFT SIDE (Questions)     | RIGHT SIDE (Answers)
--------------------------|------------------------
1. [Question]             | [Detailed answer]
2. [Question]             | [Detailed answer]

Generate 10-15 questions covering the main content.

Transcript:
{transcript}

Split-page Q&A:"""
    }
}


def load_saved_podcasts():
    """Load previously saved podcasts from disk on startup"""
    transcripts_folder = Path(__file__).parent / 'transcripts'
    downloads_folder = Path(__file__).parent / 'downloads'
    
    if not transcripts_folder.exists():
        return
    
    for transcript_file in transcripts_folder.glob('*_transcript.json'):
        try:
            with open(transcript_file, 'r') as f:
                data = json.load(f)
            
            podcast_id = data.get('id')
            if not podcast_id or podcast_id in podcasts_db:
                continue
            
            # Find the audio file
            audio_files = list(downloads_folder.glob(f'{podcast_id}_*.wav'))
            file_path = str(audio_files[0]) if audio_files else None
            filename = audio_files[0].name if audio_files else None
            
            # Get file size for display
            file_size = None
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
            
            # Reconstruct the podcast entry
            transcript = data.get('transcript', '')
            podcasts_db[podcast_id] = {
                'id': podcast_id,
                'user_id': data.get('user_id'),
                'title': data.get('title', 'Unknown'),
                'duration': data.get('duration', 0),
                'file_path': file_path,
                'filename': filename,
                'file_size': file_size,
                'status': 'transcribed' if transcript else 'downloaded',
                'transcript': transcript,
                'chunks': chunk_transcript(transcript) if transcript else None,
                'utterances': data.get('utterances', []),
                'words': data.get('words', []),
                'saved_at': os.path.getmtime(transcript_file)
            }
            logger.info(f"Loaded saved podcast: {data.get('title', podcast_id)}")
        except Exception as e:
            logger.error(f"Error loading {transcript_file}: {e}")


def download_youtube_audio(url: str, output_path: Path) -> dict:
    """Download audio from YouTube video"""
    unique_id = str(uuid.uuid4())[:8]
    output_template = str(output_path / f'{unique_id}_%(title)s.%(ext)s')
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get('title', 'Unknown')
        duration = info.get('duration', 0)
        
        # Find the downloaded file
        for file in output_path.glob(f'{unique_id}_*.wav'):
            return {
                'id': unique_id,
                'title': title,
                'duration': duration,
                'file_path': str(file),
                'filename': file.name
            }
    
    raise Exception("Failed to download audio")


def transcribe_audio(file_path: str, language: str = "en") -> dict:
    """Transcribe audio using Smallest AI Pulse API, handling large files by chunking
    
    Audio is compressed to mono 16kHz to reduce file size, then chunked based on duration:
    - < 3 min: Single chunk (no splitting)
    - 3-10 min: 3-minute chunks
    - 10-30 min: 5-minute chunks
    - 30-60 min: 7-minute chunks
    - > 60 min: 5-minute chunks (more chunks but reliable)
    """
    if not SMALLEST_API_KEY:
        raise ValueError("SMALLEST_API_KEY environment variable not set")
    
    from pydub import AudioSegment
    import tempfile
    
    # Load audio file
    audio = AudioSegment.from_wav(file_path)
    duration_s = len(audio) / 1000  # Duration in seconds
    duration_ms = len(audio)
    
    # Compress audio: convert to mono 16kHz for smaller file size
    # This is key to avoiding "Audio data too large" errors
    audio = audio.set_channels(1).set_frame_rate(16000)
    logger.info(f"Compressed audio to mono 16kHz")
    
    # Dynamically determine chunk size based on total duration
    if duration_s <= 180:  # < 3 minutes
        max_chunk_ms = duration_ms  # No chunking needed
        logger.info(f"Short audio ({duration_s:.1f}s) - single chunk")
    elif duration_s <= 600:  # 3-10 minutes
        max_chunk_ms = 3 * 60 * 1000  # 3-minute chunks
        logger.info(f"Medium audio ({duration_s:.1f}s) - using 3-minute chunks")
    elif duration_s <= 1800:  # 10-30 minutes
        max_chunk_ms = 5 * 60 * 1000  # 5-minute chunks
        logger.info(f"Long audio ({duration_s:.1f}s) - using 5-minute chunks")
    elif duration_s <= 3600:  # 30-60 minutes
        max_chunk_ms = 7 * 60 * 1000  # 7-minute chunks
        logger.info(f"Very long audio ({duration_s:.1f}s) - using 7-minute chunks")
    else:  # > 60 minutes
        max_chunk_ms = 5 * 60 * 1000  # 5-minute chunks (more reliable for very long)
        logger.info(f"Extra long audio ({duration_s:.1f}s) - using 5-minute chunks")
    
    if duration_ms <= max_chunk_ms:
        # Small file, transcribe directly
        logger.info(f"Transcribing single chunk ({duration_s:.1f}s)")
        
        # Save compressed audio to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            audio.export(tmp.name, format='wav')
            tmp_path = tmp.name
        
        try:
            return transcribe_chunk(tmp_path, language)
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass
    
    # Large file, split into chunks
    num_chunks = int(duration_ms / max_chunk_ms) + 1
    logger.info(f"Audio is {duration_s:.1f}s, splitting into ~{num_chunks} chunks...")
    
    chunks = []
    start = 0
    chunk_num = 0
    
    while start < duration_ms:
        end = min(start + max_chunk_ms, duration_ms)
        chunk = audio[start:end]
        chunks.append(chunk)
        start = end
        chunk_num += 1
    
    logger.info(f"Split into {len(chunks)} chunks")
    
    # Transcribe each chunk
    all_transcriptions = []
    all_words = []
    all_utterances = []
    time_offset = 0
    
    for i, chunk in enumerate(chunks):
        logger.info(f"Transcribing chunk {i+1}/{len(chunks)}...")
        
        # Save chunk to temp file (already compressed)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            chunk.export(tmp.name, format='wav')
            tmp_path = tmp.name
        
        try:
            result = transcribe_chunk(tmp_path, language)
            
            # Add transcription
            if result.get('transcription'):
                all_transcriptions.append(result['transcription'])
            
            # Adjust word timestamps
            if result.get('words'):
                for word in result['words']:
                    word['start'] = word.get('start', 0) + time_offset
                    word['end'] = word.get('end', 0) + time_offset
                    all_words.append(word)
            
            # Adjust utterance timestamps
            if result.get('utterances'):
                for utt in result['utterances']:
                    utt['start'] = utt.get('start', 0) + time_offset
                    utt['end'] = utt.get('end', 0) + time_offset
                    all_utterances.append(utt)
            
            # Update time offset for next chunk
            time_offset += len(chunk) / 1000  # Convert ms to seconds
            
        finally:
            # Clean up temp file
            try:
                os.remove(tmp_path)
            except:
                pass
    
    return {
        'status': 'success',
        'transcription': ' '.join(all_transcriptions),
        'words': all_words,
        'utterances': all_utterances
    }


def transcribe_chunk(file_path: str, language: str = "en") -> dict:
    """Transcribe a single audio chunk using Smallest AI Pulse API"""
    with open(file_path, 'rb') as audio_file:
        response = requests.post(
            SMALLEST_API_URL,
            params={
                "model": "pulse",
                "language": language,
                "word_timestamps": "true",
                "diarize": "true"
            },
            headers={
                "Authorization": f"Bearer {SMALLEST_API_KEY}",
                "Content-Type": "audio/wav",
            },
            data=audio_file.read(),
            timeout=300  # 5 minutes timeout
        )
    
    if response.status_code != 200:
        raise Exception(f"Transcription failed: {response.text}")
    
    return response.json()


def chunk_transcript(transcript: str, chunk_size: int = 1000) -> list:
    """Split transcript into chunks for better context retrieval"""
    words = transcript.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1
        
        if current_length >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_length = 0
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks


def find_relevant_context(query: str, chunks: list, top_k: int = 3) -> str:
    """Find relevant chunks based on keyword matching (simple approach)"""
    query_words = set(query.lower().split())
    scored_chunks = []
    
    for chunk in chunks:
        chunk_words = set(chunk.lower().split())
        score = len(query_words & chunk_words)
        scored_chunks.append((score, chunk))
    
    # Sort by score and get top chunks
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    relevant = [chunk for score, chunk in scored_chunks[:top_k] if score > 0]
    
    if not relevant:
        # Return first few chunks as fallback
        relevant = chunks[:top_k]
    
    return '\n\n'.join(relevant)


def generate_chat_response(query: str, context: str, transcript: str, podcast_title: str = "the podcast") -> str:
    """Generate a response using Ollama (local LLM) based on the transcript context"""
    
    # Create a prompt for Ollama
    prompt = f"""You are a helpful assistant that answers questions about a podcast called "{podcast_title}". 
You have access to the transcript and should answer questions based ONLY on the information from the podcast.
If the answer is not in the transcript, say so. Be conversational and helpful, as if you're discussing the podcast with a friend.
Keep your response concise but informative.

Here is the relevant section of the transcript:
---
{context}
---

For additional context, here's a broader excerpt from the transcript:
---
{transcript[:3000] if len(transcript) > 3000 else transcript}
---

User's question: {query}

Answer:"""
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1000
                }
            },
            timeout=120
        )
        
        if response.status_code != 200:
            return f"Error: Ollama returned status {response.status_code}. Make sure Ollama is running (ollama serve)."
        
        result = response.json()
        return result.get('response', 'No response generated')
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to Ollama. Make sure Ollama is running (run 'ollama serve' in terminal)."
    except Exception as e:
        return f"Error generating response: {str(e)}"


def check_ollama_status():
    """Check if Ollama is running and model is available"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m.get('name', '').split(':')[0] for m in models]
            return {
                'running': True,
                'model_available': 'llama3.2' in model_names or any('llama3.2' in n for n in model_names),
                'models': model_names
            }
    except:
        pass
    return {'running': False, 'model_available': False, 'models': []}


def start_ollama():
    """Start Ollama server automatically if not running"""
    logger.info("Checking if Ollama is running...")
    status = check_ollama_status()
    
    if status['running']:
        logger.info("✓ Ollama is already running")
        if status['model_available']:
            logger.info(f"✓ Model '{OLLAMA_MODEL}' is available")
        else:
            logger.warning(f"Model '{OLLAMA_MODEL}' not found. Available models: {status['models']}")
            logger.info(f"Run: ollama pull {OLLAMA_MODEL}")
        return True
    
    logger.info("Starting Ollama...")
    try:
        # Start Ollama serve in the background
        subprocess.Popen(
            ['ollama', 'serve'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        # Wait for Ollama to start (up to 10 seconds)
        for i in range(10):
            time.sleep(1)
            status = check_ollama_status()
            if status['running']:
                logger.info("✓ Ollama started successfully")
                if status['model_available']:
                    logger.info(f"✓ Model '{OLLAMA_MODEL}' is available")
                else:
                    logger.warning(f"Model '{OLLAMA_MODEL}' not found. Run: ollama pull {OLLAMA_MODEL}")
                return True
            logger.debug(f"Waiting for Ollama to start... ({i+1}/10)")
        
        logger.error("Failed to start Ollama within timeout")
        return False
        
    except FileNotFoundError:
        logger.error("Ollama not installed. Install it from: https://ollama.ai")
        return False
    except Exception as e:
        logger.error(f"Error starting Ollama: {e}")
        return False


@app.route('/')
@login_required
def index():
    """Serve the main page"""
    return render_template('index.html', user=current_user)


@app.route('/api/status', methods=['GET'])
def get_status():
    """Check system status (Ollama, API keys, etc.)"""
    ollama_status = check_ollama_status()
    return jsonify({
        'ollama_running': ollama_status['running'],
        'ollama_model_available': ollama_status['model_available'],
        'transcription_available': bool(SMALLEST_API_KEY),
        'status': 'ready' if (ollama_status['running'] and ollama_status['model_available'] and SMALLEST_API_KEY) else 'setup_needed'
    })


@app.route('/api/download', methods=['POST'])
@login_required
def download_audio():
    """Download audio from YouTube URL"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        logger.warning("Download request missing URL")
        return jsonify({'error': 'No URL provided'}), 400
    
    logger.info(f"Starting download for URL: {url[:50]}...")
    start_time = time.time()
    
    try:
        result = download_youtube_audio(url, app.config['UPLOAD_FOLDER'])
        
        # Store in database with user ownership
        podcasts_db[result['id']] = {
            'id': result['id'],
            'user_id': current_user.id,
            'title': result['title'],
            'duration': result['duration'],
            'file_path': result['file_path'],
            'filename': result['filename'],
            'status': 'downloaded',
            'transcript': None,
            'chunks': None
        }
        
        elapsed = time.time() - start_time
        logger.info(f"Download completed: '{result['title']}' ({result['duration']}s) in {elapsed:.1f}s")
        
        return jsonify({
            'success': True,
            'podcast_id': result['id'],
            'title': result['title'],
            'duration': result['duration'],
            'message': 'Audio downloaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Download failed for {url}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/transcribe/<podcast_id>', methods=['POST'])
@login_required
def transcribe(podcast_id):
    """Transcribe downloaded audio using Smallest AI Pulse STT"""
    if podcast_id not in podcasts_db:
        logger.warning(f"Transcription requested for unknown podcast: {podcast_id}")
        return jsonify({'error': 'Podcast not found'}), 404
    
    podcast = podcasts_db[podcast_id]
    
    # Verify ownership
    if podcast.get('user_id') != current_user.id:
        return jsonify({'error': 'Podcast not found'}), 404
    
    if not SMALLEST_API_KEY:
        logger.error("Transcription failed: SMALLEST_API_KEY not configured")
        return jsonify({'error': 'SMALLEST_API_KEY not configured'}), 500
    
    logger.info(f"Starting transcription for: '{podcast['title']}'")
    start_time = time.time()
    
    try:
        data = request.get_json() or {}
        language = data.get('language', 'en')
        
        result = transcribe_audio(podcast['file_path'], language)
        
        transcript = result.get('transcription', '')
        chunks = chunk_transcript(transcript)
        
        # Update database
        podcast['transcript'] = transcript
        podcast['chunks'] = chunks
        podcast['utterances'] = result.get('utterances', [])
        podcast['words'] = result.get('words', [])
        podcast['status'] = 'transcribed'
        
        # Save transcript to file
        transcript_path = app.config['TRANSCRIPTS_FOLDER'] / f'{podcast_id}_transcript.json'
        with open(transcript_path, 'w') as f:
            json.dump({
                'id': podcast_id,
                'user_id': podcast.get('user_id'),
                'title': podcast['title'],
                'duration': podcast.get('duration', 0),
                'transcript': transcript,
                'utterances': podcast['utterances'],
                'words': podcast['words']
            }, f, indent=2)
        
        elapsed = time.time() - start_time
        word_count = len(transcript.split())
        logger.info(f"Transcription completed: {word_count} words in {elapsed:.1f}s")
        
        return jsonify({
            'success': True,
            'transcript': transcript,
            'word_count': word_count,
            'message': 'Transcription completed'
        })
        
    except Exception as e:
        logger.error(f"Transcription failed for {podcast_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/<podcast_id>', methods=['POST'])
@login_required
def chat(podcast_id):
    """Chat with the podcast based on transcript using local LLM"""
    if podcast_id not in podcasts_db:
        logger.warning(f"Chat requested for unknown podcast: {podcast_id}")
        return jsonify({'error': 'Podcast not found'}), 404
    
    podcast = podcasts_db[podcast_id]
    
    # Verify ownership
    if podcast.get('user_id') != current_user.id:
        return jsonify({'error': 'Podcast not found'}), 404
    
    if not podcast.get('transcript'):
        logger.warning(f"Chat requested for non-transcribed podcast: {podcast_id}")
        return jsonify({'error': 'Podcast not transcribed yet'}), 400
    
    data = request.get_json()
    query = data.get('message', '').strip()
    
    if not query:
        return jsonify({'error': 'No message provided'}), 400
    
    logger.info(f"Chat query for '{podcast['title']}': {query[:50]}...")
    start_time = time.time()
    
    try:
        # Find relevant context from transcript chunks
        context = find_relevant_context(query, podcast['chunks'])
        
        # Generate response using local LLM (Ollama)
        response = generate_chat_response(query, context, podcast['transcript'], podcast.get('title', 'the podcast'))
        
        elapsed = time.time() - start_time
        logger.info(f"Chat response generated in {elapsed:.1f}s")
        
        return jsonify({
            'success': True,
            'response': response,
            'context_used': context[:500] + '...' if len(context) > 500 else context
        })
        
    except Exception as e:
        logger.error(f"Chat failed for {podcast_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai-feature/<podcast_id>', methods=['POST'])
@login_required
def ai_feature(podcast_id):
    """Apply an AI feature to the podcast transcript using Ollama"""
    if podcast_id not in podcasts_db:
        logger.warning(f"AI feature requested for unknown podcast: {podcast_id}")
        return jsonify({'error': 'Podcast not found'}), 404
    
    podcast = podcasts_db[podcast_id]
    
    # Verify ownership
    if podcast.get('user_id') != current_user.id:
        return jsonify({'error': 'Podcast not found'}), 404
    
    if not podcast.get('transcript'):
        logger.warning(f"AI feature requested for non-transcribed podcast: {podcast_id}")
        return jsonify({'error': 'Podcast not transcribed yet'}), 400
    
    data = request.get_json()
    feature_type = data.get('feature', '').strip()
    
    if not feature_type or feature_type not in AI_FEATURE_PROMPTS:
        return jsonify({'error': f'Invalid feature type. Available: {list(AI_FEATURE_PROMPTS.keys())}'}), 400
    
    feature = AI_FEATURE_PROMPTS[feature_type]
    logger.info(f"AI feature '{feature['name']}' for '{podcast['title']}'")
    start_time = time.time()
    
    try:
        # Prepare the transcript (truncate if too long for context)
        transcript = podcast['transcript']
        max_transcript_length = 12000  # Limit to avoid token overflow
        if len(transcript) > max_transcript_length:
            transcript = transcript[:max_transcript_length] + "\n\n[Transcript truncated for processing...]"
        
        # Build the prompt
        prompt = feature['prompt'].format(transcript=transcript)
        
        # Call Ollama
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 4000
                }
            },
            timeout=180  # 3 minutes timeout for longer features
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'Ollama returned status {response.status_code}. Make sure Ollama is running.'}), 500
        
        result = response.json()
        ai_response = result.get('response', 'No response generated')
        
        elapsed = time.time() - start_time
        logger.info(f"AI feature '{feature['name']}' completed in {elapsed:.1f}s")
        
        return jsonify({
            'success': True,
            'feature': feature_type,
            'feature_name': feature['name'],
            'result': ai_response,
            'processing_time': round(elapsed, 2)
        })
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Cannot connect to Ollama. Make sure Ollama is running (ollama serve).'}), 500
    except Exception as e:
        logger.error(f"AI feature failed for {podcast_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai-features', methods=['GET'])
def list_ai_features():
    """List all available AI features"""
    features = {
        'popular': [
            {'id': 'summary', 'name': 'Summary', 'description': 'Comprehensive overview'},
            {'id': 'key_insights', 'name': 'Key Insights', 'description': 'Main takeaways'},
            {'id': 'clean_transcript', 'name': 'Clean Transcript', 'description': 'Remove filler words'},
            {'id': 'proper_notes', 'name': 'Proper Notes', 'description': 'Comprehensive notes'}
        ],
        'basic_content': [
            {'id': 'clean_transcript', 'name': 'Clean Transcript', 'description': 'Remove filler words'},
            {'id': 'micro_summary', 'name': 'Micro Summary', 'description': '2-3 sentences'},
            {'id': 'short_summary', 'name': 'Short Summary', 'description': 'Brief paragraph'},
            {'id': 'bullet_points', 'name': 'Bullet Points', 'description': 'Key points as bullets'},
            {'id': 'summary', 'name': 'Summary', 'description': 'Full summary'},
            {'id': 'key_insights', 'name': 'Key Insights', 'description': 'Main takeaways'},
            {'id': 'notable_quotes', 'name': 'Notable Quotes', 'description': 'Memorable quotes'}
        ],
        'analysis': [
            {'id': 'extract_ideas', 'name': 'Extract Ideas', 'description': 'All distinct ideas'},
            {'id': 'extract_insights', 'name': 'Extract Insights', 'description': 'Deeper insights'},
            {'id': 'extract_patterns', 'name': 'Extract Patterns', 'description': 'Recurring themes'},
            {'id': 'extract_wisdom', 'name': 'Extract Wisdom', 'description': 'Life lessons'}
        ],
        'study_education': [
            {'id': 'flashcards', 'name': 'Flashcards', 'description': 'Study cards'},
            {'id': 'concept_map', 'name': 'Concept Map', 'description': 'Visual relationships'},
            {'id': 'qa', 'name': 'Q&A', 'description': 'Questions and answers'},
            {'id': 'outline_notes', 'name': 'Outline Notes', 'description': 'Structured outline'},
            {'id': 'cornell_notes', 'name': 'Cornell Notes', 'description': 'Cornell format'},
            {'id': 'rapid_logging', 'name': 'Rapid Logging', 'description': 'Bullet journal style'},
            {'id': 't_note_method', 'name': 'T-Note Method', 'description': 'Two-column notes'},
            {'id': 'charting_method', 'name': 'Charting Method', 'description': 'Table format'},
            {'id': 'qec_method', 'name': 'QEC Method', 'description': 'Question-Evidence-Conclusion'},
            {'id': 'qa_split_page', 'name': 'Q&A Split Page', 'description': 'Side-by-side Q&A'}
        ]
    }
    return jsonify({'features': features})


@app.route('/api/podcasts', methods=['GET'])
@login_required
def list_podcasts():
    """List all downloaded podcasts for current user"""
    podcasts = []
    for pid, podcast in podcasts_db.items():
        # Only show podcasts belonging to current user
        if podcast.get('user_id') != current_user.id:
            continue
        podcasts.append({
            'id': podcast['id'],
            'title': podcast['title'],
            'duration': podcast['duration'],
            'status': podcast['status'],
            'has_transcript': podcast['transcript'] is not None
        })
    return jsonify({'podcasts': podcasts})


@app.route('/api/podcast/<podcast_id>', methods=['GET'])
@login_required
def get_podcast(podcast_id):
    """Get podcast details"""
    if podcast_id not in podcasts_db:
        return jsonify({'error': 'Podcast not found'}), 404
    
    podcast = podcasts_db[podcast_id]
    
    # Verify ownership
    if podcast.get('user_id') != current_user.id:
        return jsonify({'error': 'Podcast not found'}), 404
    
    return jsonify({
        'id': podcast['id'],
        'title': podcast['title'],
        'duration': podcast['duration'],
        'status': podcast['status'],
        'has_transcript': podcast['transcript'] is not None,
        'transcript_preview': podcast['transcript'][:500] if podcast['transcript'] else None
    })


@app.route('/api/podcast/<podcast_id>', methods=['DELETE'])
@login_required
def delete_podcast(podcast_id):
    """Delete a podcast"""
    if podcast_id not in podcasts_db:
        return jsonify({'error': 'Podcast not found'}), 404
    
    podcast = podcasts_db[podcast_id]
    
    # Verify ownership
    if podcast.get('user_id') != current_user.id:
        return jsonify({'error': 'Podcast not found'}), 404
    
    # Delete audio file
    try:
        if os.path.exists(podcast['file_path']):
            os.remove(podcast['file_path'])
    except Exception:
        pass
    
    # Delete transcript file
    transcript_path = app.config['TRANSCRIPTS_FOLDER'] / f'{podcast_id}_transcript.json'
    try:
        if transcript_path.exists():
            transcript_path.unlink()
    except Exception:
        pass
    
    del podcasts_db[podcast_id]
    
    return jsonify({'success': True, 'message': 'Podcast deleted'})


@app.route('/downloads/<filename>')
def serve_audio(filename):
    """Serve downloaded audio files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Get saved podcasts for current user"""
    history = []
    for pid, podcast in podcasts_db.items():
        # Only show podcasts belonging to current user
        if podcast.get('user_id') != current_user.id:
            continue
        file_size_mb = None
        if podcast.get('file_size'):
            file_size_mb = round(podcast['file_size'] / (1024 * 1024), 1)
        elif podcast.get('file_path') and os.path.exists(podcast['file_path']):
            file_size_mb = round(os.path.getsize(podcast['file_path']) / (1024 * 1024), 1)
        
        history.append({
            'id': podcast['id'],
            'title': podcast['title'],
            'duration': podcast.get('duration', 0),
            'status': podcast['status'],
            'has_transcript': podcast.get('transcript') is not None,
            'transcript_preview': podcast['transcript'][:200] + '...' if podcast.get('transcript') and len(podcast['transcript']) > 200 else podcast.get('transcript'),
            'file_size_mb': file_size_mb,
            'saved_at': podcast.get('saved_at')
        })
    
    # Sort by saved_at (newest first)
    history.sort(key=lambda x: x.get('saved_at') or 0, reverse=True)
    return jsonify({'history': history})


@app.route('/api/history/<podcast_id>/load', methods=['POST'])
@login_required
def load_from_history(podcast_id):
    """Load a podcast from history for chatting"""
    if podcast_id not in podcasts_db:
        return jsonify({'error': 'Podcast not found in history'}), 404
    
    podcast = podcasts_db[podcast_id]
    
    # Verify ownership
    if podcast.get('user_id') != current_user.id:
        return jsonify({'error': 'Podcast not found in history'}), 404
    
    return jsonify({
        'success': True,
        'podcast_id': podcast['id'],
        'title': podcast['title'],
        'duration': podcast.get('duration', 0),
        'status': podcast['status'],
        'has_transcript': podcast.get('transcript') is not None,
        'transcript': podcast.get('transcript'),
        'word_count': len(podcast['transcript'].split()) if podcast.get('transcript') else 0
    })


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("Podcast Chat App - Starting")
    logger.info("=" * 50)
    
    # Auto-start Ollama
    start_ollama()
    
    # Load saved podcasts from disk
    load_saved_podcasts()
    logger.info(f"Loaded {len(podcasts_db)} saved podcast(s)")
    
    if not SMALLEST_API_KEY:
        logger.warning("SMALLEST_API_KEY not set! Set it in .env file")
    else:
        logger.info("Smallest AI API key configured")
    
    # Production vs Development mode
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"Starting server at http://localhost:{port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info("=" * 50)
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
