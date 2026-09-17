# Transcriptor de Audio

App web en Flask que transcribe audio a texto usando `faster-whisper`
(local, sin API keys, sin costo por transcripción). Pensada para desarrollarse
en Mac y desplegarse como servicio web, así se usa desde cualquier navegador
(incluyendo tu Windows del trabajo) sin instalar nada ahí.

## 1. Desarrollo local (en tu Mac)

### Requisito: ffmpeg

```bash
brew install ffmpeg
```

### Instalar y correr

```bash
cd transcriptor-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abre http://localhost:5000. Mientras desarrollas en Mac puedes usar un modelo
más grande y preciso así:

```bash
MODEL_SIZE=base python app.py
```

## 2. Desplegar para usarlo desde Windows (o cualquier navegador)

La forma más sencilla y gratuita es **Render**:

1. Sube esta carpeta a un repo de GitHub (público o privado).
2. Entra a https://render.com, crea cuenta (no pide tarjeta para el plan free).
3. "New" → "Web Service" → conecta tu repo.
4. Configuración:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app` (ya viene en el `Procfile`)
   - **Instance type:** Free
5. Deploy. Render te da una URL tipo `https://tu-app.onrender.com`.
6. Desde el Windows del trabajo, solo abres esa URL en el navegador, subes
   el audio y descargas el `.txt`. Cero instalaciones ahí.

### Notas sobre el plan gratuito de Render

- Tiene poca RAM, por eso dejé el modelo en `tiny` por defecto para producción
  (más rápido y ligero, algo menos preciso que `base`).
- El servicio "duerme" tras un rato sin uso en el plan free — el primer
  request tras dormir tarda ~30-60 seg en despertar. Normal, no es un bug.
- Si con el tiempo necesitas más precisión o velocidad, puedes subir a un
  plan pagado con más RAM y usar `MODEL_SIZE=small` o `medium` como variable
  de entorno en Render.

### Alternativas a Render

- **Railway** (railway.app) — similar, también con plan gratuito limitado.
- **Fly.io** — más control, requiere un poco más de configuración (Dockerfile).

## Notas generales

- Formatos soportados: mp3, wav, m4a, ogg, flac, webm, mp4.
- Audios largos tardan más, sobre todo en el plan free (CPU compartida).
  Para pruebas, usa clips cortos (1-3 min) al inicio.
- Cuando quieras ir agregando features (resúmenes, chat sobre el contenido,
  etc.), esa transcripción en texto plano es el punto de partida para
  meterla a un LLM — no hace falta LangChain para esta primera versión.
