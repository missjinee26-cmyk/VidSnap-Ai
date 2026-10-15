# AI Reel Generator (VidSnapAI)

A Flask-based web application for creating Instagram Reels from images/videos with AI-powered voiceover.

## Features

- Upload multiple images/videos
- Add custom text for AI voiceover (ElevenLabs)
- AI-enhanced script generation (OpenAI/Gemini)
- Automatic video compilation with ffmpeg
- Gallery to view created reels

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install ffmpeg:**
   - Windows: Download from https://ffmpeg.org/download.html
   - Mac: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Required API Keys:**
   - **ElevenLabs** (required): Get from https://elevenlabs.io
   - **OpenAI** (optional): For AI script generation
   - **Gemini** (optional): Alternative AI for script generation

## Running the Application

1. **Start the web server:**
   ```bash
   python main.py
   ```
   Access at http://localhost:5000

2. **Start the background processor (in a separate terminal):**
   ```bash
   python generate_process.py
   ```

## Usage

1. Go to `/create` page
2. Upload images/videos (drag & drop or file picker)
3. Enter text for voiceover
4. Click "Create Reel"
5. Check `/gallery` for the generated reel

## Project Structure

```
Ai/
├── main.py              # Flask web application
├── generate_process.py  # Background video processing
├── text_to_audio.py     # ElevenLabs TTS integration
├── config.py            # Configuration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── templates/           # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── create.html
│   └── gallery.html
├── static/              # Static assets
│   ├── css/
│   ├── reels/           # Generated reels output
│   └── songs/           # Background music
└── user_uploads/        # User uploaded files (auto-created)
```

## API Integration

The app supports two AI providers for script enhancement:
- **OpenAI GPT-3.5/4**: Set `OPENAI_API_KEY`
- **Google Gemini**: Set `GEMINI_API_KEY`

At least one is optional but recommended for better scripts.

## Troubleshooting

- **FFmpeg not found**: Ensure ffmpeg is in PATH
- **ElevenLabs error**: Check API key and quota
- **Permission errors**: Ensure write access to `user_uploads/` and `static/reels/`