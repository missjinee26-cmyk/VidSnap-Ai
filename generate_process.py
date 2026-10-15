import os
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


def generate_ai_script(folder, images_info=None):
    """Generate an engaging script for the reel using AI."""
    desc_path = f"user_uploads/{folder}/desc.txt"
    if not os.path.exists(desc_path):
        return None

    with open(desc_path, encoding="utf-8") as f:
        user_text = f.read().strip()

    if not user_text:
        return None

    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not openai_key and not gemini_key:
        return user_text

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
        if OPENAI_AVAILABLE and openai_key:
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=500
            )
            result = json.loads(response.choices[0].message.content)
            return result

        elif GEMINI_AVAILABLE and gemini_key:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            result = json.loads(response.text)
            return result

    except Exception as e:
        print(f"AI script generation failed: {e}")

    return user_text


def text_to_audio(folder):
    print("TTA -", folder)
    desc_path = f"user_uploads/{folder}/desc.txt"
    if not os.path.exists(desc_path):
        print(f"Description file not found for {folder}")
        return

    with open(desc_path, encoding="utf-8") as f:
        text = f.read()
    voice_path = f"user_uploads/{folder}/voice.txt"
    voice = "adam"
    if os.path.exists(voice_path):
        with open(voice_path, encoding="utf-8") as f:
            voice = f.read().strip() or "adam"
    print(text, folder, f"[voice={voice}]")
    text_to_speech_file(text, folder, voice)


def _ffmpeg_exe():
    """Use bundled ffmpeg (ffmpeg/bin/ffmpeg.exe) first, fall back to PATH."""
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


def create_reel(folder):
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

    audio_dur = get_audio_duration(audio_path)
    if audio_dur:
        print(f"Audio duration: {audio_dur:.2f}s")
    else:
        print("Could not probe audio duration, using slideshow length as-is")

    # -stream_loop loops the slideshow so a single image (or short clip)
    # can cover the full voiceover; -t trims the result to the audio length.
    # Without this, a single image yields 1 frame (~0.04s) and -shortest
    # chops the voiceover off.
    command = [
        _ffmpeg_exe(), '-y',
        '-stream_loop', '10',
        '-f', 'concat', '-safe', '0', '-i', input_path,
        '-i', audio_path,
        '-c:v', 'libx264', '-c:a', 'aac',
        '-pix_fmt', 'yuv420p',
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
    ]
    if audio_dur:
        command += ['-t', f"{audio_dur:.3f}"]
    else:
        command += ['-shortest']
    command += [output_path]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"CR - Reel created: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error for {folder}: {e.stderr[-2000:] if e.stderr else e}")
        return False
    except FileNotFoundError:
        print("FFmpeg not found (checked bundled ffmpeg/bin + PATH).")
        return False


def process_with_ai(folder):
    """Enhanced processing with AI-generated script."""
    print(f"AI Processing: {folder}")

    ai_script = generate_ai_script(folder)
    if ai_script and isinstance(ai_script, dict):
        script_text = " ".join([scene.get("voiceover", "") for scene in ai_script.get("scenes", [])])
        if script_text:
            desc_path = f"user_uploads/{folder}/desc.txt"
            with open(desc_path, "w") as f:
                f.write(script_text)
            print(f"AI-enhanced script saved for {folder}")

    text_to_audio(folder)
    create_reel(folder)


if __name__ == "__main__":
    while True:
        print("Processing queue....")
        done_folders = []
        if os.path.exists("done.txt"):
            with open("done.txt", "r") as f:
                done_folders = [line.strip() for line in f.readlines()]

        folders = []
        if os.path.exists("user_uploads"):
            folders = [f for f in os.listdir("user_uploads") if os.path.isdir(os.path.join("user_uploads", f))]

        for folder in folders:
            if folder not in done_folders:
                print(f"Processing folder: {folder}")
                process_with_ai(folder)
                with open("done.txt", "a") as f:
                    f.write(folder + "\n")
        time.sleep(4)