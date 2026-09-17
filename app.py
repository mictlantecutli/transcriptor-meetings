import os
import tempfile
import threading
import uuid

import requests
from flask import Flask, render_template, request, send_file, flash, redirect, jsonify

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # cámbiala si algún día esto sale de tu máquina

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
# whisper-large-v3-turbo: rápido y barato, buena precisión para reuniones.
GROQ_MODEL = "whisper-large-v3-turbo"

ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac", "webm", "mp4"}

# Guarda el estado de cada transcripción en memoria: {job_id: {...}}
jobs = {}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def run_transcription(job_id: str, tmp_path: str, original_filename: str):
    try:
        with open(tmp_path, "rb") as f:
            response = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": (original_filename, f)},
                data={"model": GROQ_MODEL, "response_format": "text"},
                timeout=600,
            )

        if response.status_code != 200:
            jobs[job_id] = {
                "status": "error",
                "error": f"Groq respondió {response.status_code}: {response.text[:300]}",
            }
            return

        jobs[job_id] = {"status": "done", "text": response.text}
    except Exception as e:
        jobs[job_id] = {"status": "error", "error": str(e)}
    finally:
        os.remove(tmp_path)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if not GROQ_API_KEY:
        flash("Falta configurar GROQ_API_KEY en las variables de entorno.")
        return redirect("/")

    if "audio" not in request.files:
        flash("No se subió ningún archivo.")
        return redirect("/")

    file = request.files["audio"]

    if file.filename == "" or not allowed_file(file.filename):
        flash("Sube un archivo de audio válido (mp3, wav, m4a, ogg, flac, webm, mp4).")
        return redirect("/")

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing"}

    thread = threading.Thread(
        target=run_transcription, args=(job_id, tmp_path, file.filename)
    )
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    job = jobs.get(job_id)
    if job is None:
        return jsonify({"status": "not_found"}), 404
    return jsonify(job)


@app.route("/download", methods=["POST"])
def download():
    text = request.form.get("transcript", "")

    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=".txt", mode="w", encoding="utf-8"
    )
    tmp.write(text)
    tmp.close()

    return send_file(tmp.name, as_attachment=True, download_name="transcripcion.txt")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
