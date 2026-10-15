"""Background worker: turns uploads in user_uploads/<id>/ into reels.

Pipeline per folder: AI script polish (optional) -> ElevenLabs TTS -> ffmpeg.
Uploads provide: desc.txt (voiceover text), voice.txt (voice pick),
input.txt (ffmpeg concat list of the uploaded files).
"""
import math
import os
import re
import time
import subprocess
import json
from dotenv import load_dotenv
from text_to_audio import text_to_speech_file

load_dotenv()

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except (ImportError, TypeError):
    GEMINI_AVAILABLE = False

POLL_INTERVAL = 2  # seconds between queue checks
PLACEHOLDER_KEY_HINTS = ("your_", "here", "placeholder", "changeme", "xxx")


def valid_key(value):
    """Real API key, or an unset/placeholder value not worth attempting."""
    if not value or not str(value).strip():
        return False
    v = str(value).strip()
    if len(v) < 20:
        return False
    return not any(h in v.lower() for h in PLACEHOLDER_KEY_HINTS)


def generate_ai_script(folder):
    """Polish the user's text into a reel script. Falls back to raw text."""
    desc_path = f"user_uploads/{folder}/desc.txt"
    if not os.path.exists(desc_path):
        return None

    with open(desc_path, encoding="utf-8") as f:
        user_text = f.read().strip()

    if not user_text:
        return None

    openai_key = os.getenv("OPENAI_API_KEY") if OPENAI_AVAILABLE else None
    gemini_key = os.getenv("GEMINI_API_KEY") if GEMINI_AVAILABLE else None
    if not valid_key(openai_key):
        openai_key = None
    if not valid_key(gemini_key):
        gemini_key = None

    if not openai_key and not gemini_key:
        return user_text  # no usable key -> skip AI instantly

    prompt = f"""Create an engaging, viral-worthy Instagram Reel script (30-60 seconds) based on this user input: "{user_text}"

Requirements:
- Hook in first 3 seconds
- Clear narrative arc
- Call to action at the end
- Conversational, energetic tone
- Include visual cues for each scene
- Max 150 words for voiceover

Format as JSON:
{{
    "scenes": [
        {{"visual": "description", "voiceover": "text", "duration": 5}},
        ...
    ],
    "total_duration": 30
}}"""

    try:
        if openai_key:
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=500,
            )
            result = json.loads(response.choices[0].message.content)
            return result

        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        return json.loads(response.text)

    except Exception as e:
        print(f"AI script generation failed, using raw text: {e}")
        return user_text


def text_to_audio(folder):
    print("TTA -", folder)
    desc_path = f"user_uploads/{folder}/desc.txt"
    if not os.path.exists(desc_path):
        print(f"Description file not found for {folder}")
        return False

    with open(desc_path, encoding="utf-8") as f:
        text = f.read()

    voice = "adam"
    voice_path = f"user_uploads/{folder}/voice.txt"
    if os.path.exists(voice_path):
        with open(voice_path, encoding="utf-8") as f:
            voice = f.read().strip() or "adam"

    print(f"{folder} [voice={voice}]")
    text_to_speech_file(text, folder, voice)
    return True


def _ffmpeg_exe():
    """Bundled Windows build first, system ffmpeg otherwise (Render/Linux)."""
    here = os.path.dirname(os.path.abspath(__file__))
    bundled = os.path.join(here, "ffmpeg", "bin", "ffmpeg.exe")
    if os.path.exists(bundled):
        return bundled
    return "ffmpeg"


def _ffprobe_exe():
    here = os.path.dirname(os.path.abspath(__file__))
    bundled = os.path.join(here, "ffmpeg", "bin", "ffprobe.exe")
    if os.path.exists(bundled):
        return bundled
    return "ffprobe"


def get_audio_duration(audio_path):
    try:
        r = subprocess.run(
            [_ffprobe_exe(), "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, check=True,
        )
        return float(r.stdout.strip())
    except Exception:
        return None


def slideshow_duration(input_path):
    """Total seconds the concat slideshow covers (sum of `duration N` lines)."""
    total = 0.0
    try:
        with open(input_path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*duration\s+([\d.]+)", line)
                if m:
                    total += float(m.group(1))
    except OSError:
        pass
    return total if total > 0 else None


def create_reel(folder):
    t0 = time.time()
    input_path = f"user_uploads/{folder}/input.txt"
    audio_path = f"user_uploads/{folder}/audio.mp3"
    output_path = f"static/reels/{folder}.mp4"

    if not os.path.exists(input_path):
        print(f"Input file not found for {folder}")
        return False
    if not os.path.exists(audio_path):
        print(f"Audio file not found for {folder}")
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Idempotent: skip work already done (e.g. after a restart/redeploy).
    if os.path.exists(output_path) and os.path.getmtime(output_path) >= max(
        os.path.getmtime(input_path), os.path.getmtime(audio_path)
    ):
        print(f"Reel already up to date: {output_path}")
        return True

    audio_dur = get_audio_duration(audio_path)
    if audio_dur:
        print(f"Audio duration: {audio_dur:.2f}s")

    # Loop the slideshow just enough to cover the voiceover (not a fixed 10x:
    # that decoded 10x frames on a tiny CPU and threw them away).
    loops = 1
    slide_dur = slideshow_duration(input_path)
    if audio_dur and slide_dur:
        loops = min(max(1, math.ceil(audio_dur / slide_dur)), 50)

    command = [
        _ffmpeg_exe(), "-y",
        "-stream_loop", str(loops),
        "-f", "concat", "-safe", "0", "-i", input_path,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
    ]
    if audio_dur:
        command += ["-t", f"{audio_dur:.3f}"]
    else:
        command += ["-shortest"]
    command += [output_path]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"CR - Reel created in {time.time() - t0:.1f}s: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        err = e.stderr[-2000:] if e.stderr else e
        print(f"FFmpeg error for {folder}: {err}")
        return False
    except FileNotFoundError:
        print("FFmpeg not found (checked bundled ffmpeg/bin + PATH).")
        return False


def process_with_ai(folder):
    """Full pipeline for one upload. Never raises (poison uploads get error.txt)."""
    print(f"AI Processing: {folder}")
    t0 = time.time()
    try:
        ai_script = generate_ai_script(folder)
        if ai_script and isinstance(ai_script, dict):
            script_text = " ".join(
                scene.get("voiceover", "") for scene in ai_script.get("scenes", [])
            )
            if script_text:
                with open(f"user_uploads/{folder}/desc.txt", "w", encoding="utf-8") as f:
                    f.write(script_text)
                print(f"AI-enhanced script saved for {folder}")

        if not text_to_audio(folder):
            raise RuntimeError("voiceover generation failed")
        if not create_reel(folder):
            raise RuntimeError("reel rendering failed")
        print(f"Done {folder} in {time.time() - t0:.1f}s")
    except Exception as e:
        print(f"FAILED {folder}: {e}")
        with open(f"user_uploads/{folder}/error.txt", "w", encoding="utf-8") as f:
            f.write(f"{type(e).__name__}: {e}\n")


if __name__ == "__main__":
    while True:
        print("Processing queue....")
        done_folders = []
        if os.path.exists("done.txt"):
            with open("done.txt", encoding="utf-8") as f:
                done_folders = [line.strip() for line in f if line.strip()]

        folders = []
        if os.path.exists("user_uploads"):
            folders = [
                f for f in os.listdir("user_uploads")
                if os.path.isdir(os.path.join("user_uploads", f))
            ]

        for folder in folders:
            if folder not in done_folders:
                print(f"Processing folder: {folder}")
                process_with_ai(folder)
                with open("done.txt", "a", encoding="utf-8") as f:
                    f.write(folder + "\n")
        time.sleep(POLL_INTERVAL)
