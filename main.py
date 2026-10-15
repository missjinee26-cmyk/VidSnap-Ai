from flask import Flask, render_template, request, redirect, url_for, flash
import uuid
from werkzeug.utils import secure_filename
import os

UPLOAD_FOLDER = 'user_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi', 'mkv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'your-secret-key-change-in-production'

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


@app.route("/gallery")
def gallery():
    reels = []
    reels_dir = "static/reels"
    if os.path.exists(reels_dir):
        reels = [f for f in os.listdir(reels_dir) if f.endswith(('.mp4', '.mov', '.avi', '.mkv'))]
    return render_template("gallery.html", reels=reels)


if __name__ == "__main__":
    app.run(debug=True)