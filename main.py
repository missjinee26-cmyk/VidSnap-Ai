from flask import Flask, render_template, request, redirect, url_for, flash
import uuid
from werkzeug.utils import secure_filename
import os

UPLOAD_FOLDER = 'user_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi', 'mkv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static/reels', exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/create", methods=["GET", "POST"])
def create():
    myid = uuid.uuid1()
    if request.method == "POST":
        rec_id = request.form.get("uuid") or str(myid)
        desc = request.form.get("text", "")
        voice = request.form.get("voice", "adam")
        input_files = []

        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], rec_id)
        os.makedirs(upload_dir, exist_ok=True)

        for key, file in request.files.items():
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(upload_dir, filename))
                input_files.append(filename)

        if input_files:
            with open(os.path.join(upload_dir, "desc.txt"), "w", encoding="utf-8") as f:
                f.write(desc)

            with open(os.path.join(upload_dir, "voice.txt"), "w", encoding="utf-8") as f:
                f.write(voice)

            # ffmpeg concat quirk: the duration of the LAST file is ignored
            # unless that file is listed again, so repeat the final entry.
            with open(os.path.join(upload_dir, "input.txt"), "w", encoding="utf-8") as f:
                for fl in input_files:
                    f.write(f"file '{fl}'\n duration 2\n")
                f.write(f"file '{input_files[-1]}'\n")

            # Do NOT write to done.txt here — generate_process.py appends
            # to done.txt only after it finishes processing a folder.
            # Writing here would make the worker skip this upload entirely.

            flash("Files uploaded successfully! Reel is being processed.", "success")
            return redirect(url_for('gallery'))
        else:
            flash("No valid files uploaded.", "error")

    return render_template("create.html", myid=myid)


def _folder_voice(fid):
    """Voice pick for an upload folder (for status display)."""
    voice_path = os.path.join(app.config['UPLOAD_FOLDER'], fid, "voice.txt")
    try:
        with open(voice_path, encoding="utf-8") as f:
            return f.read().strip() or "adam"
    except OSError:
        return "adam"


@app.route("/gallery")
def gallery():
    reels = []
    reels_dir = "static/reels"
    if os.path.exists(reels_dir):
        reels = sorted(
            (f for f in os.listdir(reels_dir)
             if f.endswith(('.mp4', '.mov', '.avi', '.mkv'))),
            key=lambda f: os.path.getmtime(os.path.join(reels_dir, f)),
            reverse=True,
        )

    done = set()
    if os.path.exists("done.txt"):
        with open("done.txt", encoding="utf-8") as f:
            done = {line.strip() for line in f if line.strip()}

    pending, failed = [], []
    uploads_dir = app.config['UPLOAD_FOLDER']
    if os.path.exists(uploads_dir):
        folders = sorted(
            (d for d in os.listdir(uploads_dir)
             if os.path.isdir(os.path.join(uploads_dir, d))),
            key=lambda d: os.path.getmtime(os.path.join(uploads_dir, d)),
            reverse=True,
        )
        for fid in folders:
            fdir = os.path.join(uploads_dir, fid)
            err_path = os.path.join(fdir, "error.txt")
            reel_path = os.path.join(reels_dir, fid + ".mp4")
            if os.path.exists(err_path) and not os.path.exists(reel_path):
                try:
                    with open(err_path, encoding="utf-8") as f:
                        err = f.read().strip().splitlines()[0][:120]
                except OSError:
                    err = "Render failed."
                failed.append({"id": fid, "error": err, "voice": _folder_voice(fid)})
            elif not os.path.exists(reel_path) and fid not in done:
                pending.append({"id": fid, "voice": _folder_voice(fid)})

    return render_template("gallery.html", reels=reels, pending=pending, failed=failed)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)