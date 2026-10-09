# ReVolt: E-Waste Scanner

ReVolt is an open-source e-waste scanner that helps people dispose of old electronics safely. Point your phone's camera at a device or part, from a laptop to a microSD card, and ReVolt tells you what it is, whether it contains hazardous materials like lithium batteries or mercury, what's worth salvaging, and how and where to dispose of it.

It's privacy-first: photos are analyzed by vision models running on your own server through [Ollama](https://ollama.com), with **no cloud AI service**. Scan history stays on the user's phone.

Built for the Congressional App Challenge (CT-04).

## How it works

```
Phone browser ──HTTPS (Tailscale)──▶ ReVolt (FastAPI) ──▶ Ollama vision model (e.g. gemma3:12b)
                                        │
                                        ├─ knowledge.py  hand-written hazards, salvage and disposal steps
                                        └─ labels.py     decodes RAM / drive label text into specs
```

1. The phone takes a photo and uploads it, resized to 1024 px.
2. The vision model identifies the item, picks a category, and transcribes any label text.
3. ReVolt combines that with **curated safety data** from `knowledge.py`. The AI never writes the safety guidance; anything extra it notices is shown separately and marked "not verified".
4. For RAM and drives, `labels.py` decodes the label text (for example `PC4-2666V` → DDR4, 2666 MT/s).
5. The phone shows a verdict (Handle with care / Recycle with care / Protect your data first / Safe to recycle), the hazards, numbered disposal steps, and nearby drop-off locations.

## Project layout

| Path | What it is |
|---|---|
| `main.py` | FastAPI backend: scan endpoints, model calls, validation, usage statistics (SQLite) |
| `knowledge.py` | Curated safety data per category; every hazard tagged `danger`, `caution` or `privacy` |
| `labels.py` | Regex decoders for RAM and drive labels |
| `static/index.html` | The whole web app (HTML, CSS, JS); Font Awesome icons are self-hosted in `static/vendor/` |
| `tests/` | pytest suite and browser UI checks |
| `Dockerfile`, `docker-compose.yml` | Server deployment |

## Run it locally

You need Python 3.10+ and access to an Ollama server with a vision model.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Point at an Ollama server (your own machine or one on your tailnet)
OLLAMA_HOST=http://localhost:11434 \
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8502 --reload --reload-exclude .venv
```

Open http://localhost:8502. If Ollama runs on this machine, pull the model first: `ollama pull gemma3:12b`.

### Test on your phone

The camera only works over HTTPS. With [Tailscale](https://tailscale.com) on both devices:

```bash
tailscale serve --bg 8502
```

Then open `https://<your-machine>.<your-tailnet>.ts.net` on the phone. (The first time, Tailscale may ask you to enable HTTPS certificates for your tailnet.)

## Deploy with Docker

`docker-compose.yml` runs Ollama and ReVolt together (it also defines Open WebUI and SearXNG, which ReVolt doesn't need).

```bash
# The ReVolt container runs as UID 10001 and stores its statistics database here:
sudo mkdir -p /srv/revolt-data && sudo chown -R 10001:10001 /srv/revolt-data

docker compose up -d --build revolt
docker exec ollama ollama pull gemma3:12b
tailscale serve --bg 8502
```

If the data folder isn't writable, ReVolt still scans normally but logs a warning and disables usage statistics.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `OLLAMA_HOST` (or `OLLAMA_BASE_URL`) | `http://localhost:11434` | Ollama server URL |
| `REVOLT_MODEL` (or `VISION_MODEL`) | `gemma3:12b` | Vision model used for scans |
| `REVOLT_MODEL_2` (or `SECOND_MODEL`) | `qwen2.5vl:7b` | Model for the optional "AI Second Opinion" setting |
| `REVOLT_DB_PATH` | `revolt.db` next to `main.py` | SQLite file for server usage statistics |
| `REVOLT_TIMEOUT` | `120` | Seconds to wait for the model (a cold model load can take ~1 minute) |
| `REVOLT_MAX_CONCURRENT_SCANS` | `2` | Scans allowed to use the model at once; others wait their turn |

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests
```

Browser UI checks (headless Chrome at iPhone size, with canned scan results, so no model is needed). Start the app, then:

```bash
node tests/ui/run_ui_tests.mjs http://127.0.0.1:8502
```

If you change the backend's result format, regenerate the canned results with `.venv/bin/python tests/ui/make_fixtures.py`.

## Editing the safety data

All hazard and disposal guidance lives in `knowledge.py`. Each hazard needs a level:

- `danger(...)`: can hurt someone (fire, toxic material). Makes the verdict "Handle with care".
- `caution(...)`: handle or sort it carefully.
- `privacy(...)`: personal data to protect.

Only add a source to `sources` after you've actually read it. Items without sources are shown as "Unverified" in the app.

## Security notes

- ReVolt has no login. It's designed to be reached only over a private Tailscale network, bound to `127.0.0.1` on the server.
- Ollama has no password either. Don't expose port 11434 beyond the server or your tailnet.
- In `docker-compose.yml`, consider these for the other services: Open WebUI is published on all network interfaces (`3000:8080`), `SEARXNG_SECRET` is empty, and images use `latest` / `main` tags. They're left as-is because changing them could break other tools on the server.
