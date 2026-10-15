import os
from dotenv import load_dotenv
from elevenlabs import set_api_key, generate, Voice, VoiceSettings

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

if ELEVENLABS_API_KEY:
    set_api_key(ELEVENLABS_API_KEY)


# Curated reel-friendly voices (verified against your ElevenLabs account).
VOICE_PRESETS = {
    "adam": ("Adam — Deep, Dominant", "pNInz6obpgDQGcFmaJgB"),
    "sarah": ("Sarah — Mature, Confident", "EXAVITQu4vr4xnSDxMaL"),
    "liam": ("Liam — Energetic Creator", "TX3LPaxmHKxFdv7VOQHJ"),
    "bella": ("Bella — Bright, Warm", "hpp4J3VqNfWAUOO0d1Us"),
    "charlie": ("Charlie — Deep, Energetic", "IKne3meq5aSn9XLyUdCD"),
    "jessica": ("Jessica — Playful, Bright", "cgSgspJ2msm6clMCkdW9"),
    "alice": ("Alice — Clear Educator", "Xb7hH8MSUJpSbSDYk0k2"),
    "brian": ("Brian — Deep, Comforting", "nPczCjzI2devNBz1zQrb"),
}
DEFAULT_VOICE = "adam"


def resolve_voice_id(voice: str) -> str:
    """Accept a preset key or raw voice_id; fall back to default."""
    if not voice:
        return VOICE_PRESETS[DEFAULT_VOICE][1]
    voice = voice.strip()
    if voice in VOICE_PRESETS:
        return VOICE_PRESETS[voice][1]
    return voice  # assume raw ElevenLabs voice_id


def text_to_speech_file(text: str, folder: str, voice: str = DEFAULT_VOICE) -> str:
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY not set in environment variables")

    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    voice = Voice(
        voice_id=resolve_voice_id(voice),
        settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
        ),
    )

    audio_bytes = generate(
        text=text.strip(),
        voice=voice,
        model="eleven_turbo_v2_5",
    )

    save_file_path = os.path.join(f"user_uploads/{folder}", "audio.mp3")

    os.makedirs(os.path.dirname(save_file_path), exist_ok=True)

    with open(save_file_path, "wb") as f:
        f.write(audio_bytes)

    print(f"{save_file_path}: A new audio file was saved successfully!")
    return save_file_path


if __name__ == "__main__":
    text_to_speech_file("Hey I am a good boy and its the best python course", "test_folder")