# Speech-to-Text MVP (Django + Whisper + Docker)

Simple web app that records microphone audio in the browser, sends it to a Django API, transcribes it on the server with a lightweight Whisper model (`faster-whisper`), and shows the text result.

## What It Does

1. Open the frontend in a browser.
2. Click **Start Listening**.
3. Speak into the microphone.
4. Click **Stop Listening**.
5. Browser uploads recording to `POST /api/transcribe/`.
6. Django transcribes audio with Whisper on the server (CPU by default).
7. Frontend displays the transcription.

## Stack

- Backend: Django, Django REST Framework, `faster-whisper`, Gunicorn
- Frontend: plain HTML/CSS/JavaScript (`MediaRecorder`)
- Containers: Docker + Docker Compose
- Frontend serving: Nginx (also proxies `/api/` to backend)

## Why `faster-whisper` + `small` model (default)

- Uses CTranslate2 backend for efficient inference, especially on CPU.
- `small` gives better quality for real-world speech.
- Automatic fallback to `tiny` is available for low-memory situations.
- Default config is CPU-friendly:
	- `WHISPER_DEVICE=cpu`
	- `WHISPER_COMPUTE_TYPE=int8`

## Project Structure

```text
speech-to-text/
├── backend/
│   ├── config/
│   ├── transcription/
│   ├── Dockerfile
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── index.html
│   ├── style.css
│   └── app.js
├── docker-compose.yml
├── .env.example
├── .dockerignore
├── .gitignore
└── README.md
```

## Prerequisites

- Docker
- Docker Compose plugin (`docker compose`)

No manual Python/system dependency installation is needed on the VPS.

## Environment Variables

1. Copy the example:

```bash
cp .env.example .env
```

2. Edit values for your environment.

Important ones:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `FRONTEND_PORT`
- Whisper settings (`WHISPER_*`)
	- `WHISPER_MODEL_SIZE` (primary model, default `small`)
	- `WHISPER_FALLBACK_MODEL_SIZE` (used when OOM is detected, default `tiny`)
	- `WHISPER_ALLOWED_LANGUAGES` (default `mk,en`)
- Gunicorn tuning (`GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`)
- Optional `HF_TOKEN` (Hugging Face access token) to reduce rate limits during first model download

## Run Locally With Docker

From project root:

```bash
docker compose up --build
```

Then open:

- Frontend: `http://localhost:8080` (or your `FRONTEND_PORT`)
- Backend API (optional direct): `http://localhost:8000/api/health/`

## API Contract

### `POST /api/transcribe/`

- Content-Type: `multipart/form-data`
- Field name: `audio_file`

Example response:

```json
{
	"text": "This is the transcribed speech."
}
```

Error responses return JSON with details and proper HTTP status.

## Frontend/Backend Communication

Flow:

```text
Browser (MediaRecorder)
	-> POST /api/transcribe/ (multipart/form-data)
	-> Django API
	-> Whisper model
	-> JSON response
	-> Text rendered in UI
```

Nginx in the frontend container proxies `/api/` to backend service `http://backend:8000/api/`, so browser calls stay same-origin.

## Whisper Model Download & Cache

- The model is downloaded and loaded during backend startup (`python manage.py warmup_whisper`).
- Model files are stored in `WHISPER_MODEL_DIR` (default `/models`).
- Docker Compose mounts a named volume (`whisper-cache`) at `/models`.
- This avoids downloading the model on every container restart.
- Startup can take longer on first run because model download happens before serving requests.
- If your network is rate-limited, set `HF_TOKEN` in `.env` for more reliable downloads.

## Language Behavior (Macedonian / English)

- Default language preference is controlled by `WHISPER_ALLOWED_LANGUAGES=mk,en`.
- The backend first runs auto-detection.
- If detected language is not in the allowed list, it retries using allowed languages (`mk`, then `en` by default).
- You can change order or languages in `.env`.

## OOM Fallback Behavior

- Primary transcription uses `WHISPER_MODEL_SIZE` (default `small`).
- If backend detects a probable out-of-memory failure, it retries once with `WHISPER_FALLBACK_MODEL_SIZE` (default `tiny`).
- This keeps quality high by default but improves stability on modest VPS instances.

## Production Notes (VPS)

- Backend runs with Gunicorn (not Django dev server).
- Set `DJANGO_DEBUG=False`.
- Configure `DJANGO_ALLOWED_HOSTS` for your domain/IP.
- If behind HTTPS reverse proxy, set:
	- `DJANGO_SECURE_SSL_REDIRECT=True`
	- `DJANGO_SESSION_COOKIE_SECURE=True`
	- `DJANGO_CSRF_COOKIE_SECURE=True`
- Frontend container exposes port `80` internally and maps to `${FRONTEND_PORT}` on host.
- Backend maps `${BACKEND_PORT}` for optional direct diagnostics.

## Reverse Proxy / HTTPS (Optional)

You can place a host-level Nginx/Caddy/Traefik in front of this compose stack:

1. Route public traffic to frontend container port.
2. Terminate TLS at reverse proxy.
3. Keep backend private to internal network if desired.

## Ports

- Frontend: host `${FRONTEND_PORT}` -> container `80` (default `8080:80`)
- Backend: host `${BACKEND_PORT}` -> container `8000` (default `8000:8000`)

## Deployment Quick Steps (Linux VPS)

```bash
git clone <your-repo-url>
cd speech-to-text
cp .env.example .env
# edit .env with production values
docker compose up -d --build
docker compose logs -f
```

## Minimal UI Behavior

- One large toggle button (`Start Listening` / `Stop Listening`)
- Recording indicator while active
- Loading indicator during transcription
- Output area for transcribed text
- Error message area for failures

