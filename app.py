import os
import tempfile
import threading
import uuid

from flask import Flask, render_template, request, send_file, flash, redirect, jsonify
from faster_whisper import WhisperModel

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # cámbiala si algún día esto sale de tu máquina

# Modelo: "tiny", "base", "small", "medium", "large-v3"
# "tiny" funciona bien en hostings gratuitos con poca RAM (ej. Render free tier).
# En tu Mac, mientras desarrollas, puedes subir a "base" o "small" si quieres
# más precisión (edita esta línea o usa la variable de entorno MODEL_SIZE).
MODEL_SIZE = os.environ.get("MODEL_SIZE", "tiny")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac", "webm", "mp4"}

# Guarda el estado de cada transcripción en memoria: {job_id: {...}}
# Suficiente para un solo usuario/instancia. Si algún día corres varias
# instancias del servidor a la vez, esto habría que moverlo a algo como Redis.
jobs = {}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def run_transcription(job_id: str, tmp_path: str):
    try:
        segments, info = model.transcribe(tmp_path, beam_size=5)
        text = " ".join(segment.text.strip() for segment in segments)
        jobs[job_id] = {"status": "done", "text": text}
    except Exception as e:
        jobs[job_id] = {"status": "error", "error": str(e)}
    finally:
        os.remove(tmp_path)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/transcribe", methods=["POST"])
def transcribe():
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

    thread = threading.Thread(target=run_transcription, args=(job_id, tmp_path))
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
