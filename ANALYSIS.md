# ReVolt — Codebase Analysis

_Reviewed 2026-10-05 on branch `New-test`. Line numbers for `main.py` refer to the **working tree**, which has one uncommitted change: the stray first line has been removed (see H1). No files other than this report were modified._

**How this review was done:** I read every tracked file (`main.py`, `knowledge.py`, `labels.py`, `static/index.html`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `README.md`, `TODO`, `.gitignore`) and the git history. There is no test suite, so I ran a throwaway smoke script from a scratch directory outside the repo. It exercised the label decoders, `enrich_analysis`, and the HTTP endpoints through FastAPI's `TestClient`, with Ollama deliberately unreachable. Findings marked **[verified]** were reproduced that way. Findings marked **[code reading]** come from reading the code and were not run in a browser.

---

## 1. Overview

ReVolt is a privacy-focused e-waste scanner built for the Congressional App Challenge. A phone browser captures a camera frame. A **locally hosted** Ollama vision model identifies the item, and the app shows hazards, salvage value, specs, and nearby CT drop-off locations.

**Architecture** (the README is out of date: it still says Streamlit, see `README.md:8`):

| Layer | Tech | File |
|---|---|---|
| Frontend | One-file vanilla HTML/CSS/JS SPA (camera, drawer UI, modals) | `static/index.html` |
| Backend | FastAPI + httpx | `main.py` |
| Curated safety data | Python dict | `knowledge.py` |
| Label decoding | Regex parsers for RAM and drive labels | `labels.py` |
| Inference | Ollama (`gemma3:12b` for vision, a Qwen model for the "double-check") | external |
| Persistence | SQLite `scans` table (server analytics) + browser `localStorage` (history) | `main.py:38-70`, `index.html:1158-1168` |
| Deploy | Docker / docker-compose behind Tailscale | `Dockerfile`, `docker-compose.yml` |

**Data flow (single scan):**

1. `index.html:1059` `triggerScan()` grabs a frame to a canvas, producing a JPEG data URI (`captureFrameURI`, `:899`).
2. The data URI is converted to a Blob and sent as multipart `POST /api/scan` (`:1073-1075`).
3. `main.py:137` reads the whole upload, base64-encodes it, and calls `query_ollama_vision` (`:106`).
4. That posts to Ollama `/api/generate` with `format: "json"` and the system prompt (`main.py:23-35`), then `json.loads` the response (`:120`).
5. `enrich_analysis` (`main.py:72`) maps the model's category/item onto a `knowledge.INFO` key by substring match. It fills in hazards/salvage/dispose **only where the model left them empty**, attaches sources, and runs `labels.decode` on `text_lines` to override `specs`.
6. The result is logged to SQLite (`main.py:141`) and returned as JSON.
7. The frontend can optionally send that JSON to `POST /api/double-check` (`index.html:1078-1087`). There, a second, text-only model rewrites it and `enrich_analysis` runs again (`main.py:165-187`).
8. `displayAnalysisResults` (`index.html:955`) renders it via `innerHTML`, and `saveToHistory` stores the result plus the full image in `localStorage`.

Multi-angle mode (`/api/scan-multi`, `main.py:150`) works the same way with up to 3 images.

## 2. Key components

- **`main.py`** is the entire backend: config (`:17-21`), prompt (`:23-35`), DB init/logging (`:38-70`), **enrichment/business logic (`enrich_analysis`, `:72-104`)**, Ollama client (`:106-134`), 4 API routes plus static serving.
- **`knowledge.py`** is the hand-curated hazard, salvage, and dispose data per category. Its docstring (`:1-5`) says "the AI never invents hazards" and "sources=None means UNVERIFIED and the app says so on screen". The code honors neither promise (see M3, M4).
- **`labels.py`** is the cleanest module. It holds deterministic, well-scoped regex decoders for RAM (`decode_ram`, `:29`) and drives (`decode_drive`, `:68`). In my smoke checks it correctly decoded `PC4-2666V`, `PC3L-12800S` → DDR3L 1600, `DDR4 3200MHz`, `1TB 7200RPM SATA 3.5"`, and `NVMe M.2`.
- **`static/index.html`** holds all UI state, camera handling, drawer gestures, rendering, history, and analytics. About 490 of its 1250 lines are JS.

The core business logic is split between `enrich_analysis` (category matching and safety-data merge) and the prompt (`main.py:23-35`). Much of the "rules" logic lives in natural-language prompt text rather than code.

---

## 3. Code quality

### Definite problems
- **Duplicated scan pipeline in the frontend.** `index.html:1072-1094` and `:1114-1138` are near-copies (fetch → parse → optional double-check → display → save). Both have the same missing `res.ok` check.
- **Duplicated route bodies.** `main.py:136-147` and `:149-162` differ only in how files are read and in `scan_mode`. The Ollama POST/parse code is also duplicated between `query_ollama_vision` (`:114-121`) and `double_check` (`:178-184`).
- **Dead code / unused values:**
  - `labels.decode` returns `complete` ("ask for a label close-up") but `main.py:100` discards it.
  - `hazard_hotspots` is requested in the prompt (`main.py:28,32`) but only used to compute a confidence number (`index.html:960-963`). It is never drawn.
  - `text_lines` and `dispose` are never displayed (see M5).
  - `imageURI` parameter of `displayAnalysisResults` is unused (`index.html:955`).
  - `parseRawModelOutput` (`index.html:925-953`) handles `response`/`content`/`message` shapes that the backend never returns; the backend already parses.
  - `requirements.txt:4-5` lists `ollama` and `pillow`, but neither is imported.
- **Unlisted direct dependency.** `main.py:5` imports `httpx`, which is not in `requirements.txt`. It only installs today because the unused `ollama` package depends on it. If you delete `ollama`, the app breaks.
- **Import-time side effects.** `init_db()` runs at module import (`main.py:57`), and `StaticFiles(directory="static")` / `FileResponse("static/index.html")` (`:215-219`) use CWD-relative paths.
- **Module-level mutable name `prompt`** (`main.py:23`) shadows a common identifier and doubles as a default argument (`:106`).

### Style / preference (not bugs)
- `print()` instead of `logging` (`main.py:70,123,186`).
- Unused imports `Optional`, `JSONResponse` (`main.py:6,9`).
- Large amounts of inline `style=` in JS template strings. A component approach or `textContent` builders would be easier to maintain.
- Git hygiene: `.gitignore` only ignores `__pycache__/`, so `.venv/` and `revolt.db` show as untracked. Many commit messages ("Update print statement from 'Hello' to 'Goodbye'") don't describe the changes.
- `README.md` is stale (Streamlit) and its Quickstart stops after step 1 (`README.md:13-15`).

---

## 4. Bugs and risks

### H1 — Committed `main.py` does not run **[verified]**
At `HEAD` (`17b15ce`), line 1 of `main.py` is several hundred spaces followed by `main.py`. Parsing it fails with `IndentationError: unexpected indent`. The fix exists only as an uncommitted change in the working tree. Anyone who clones or builds from `HEAD` gets a container that crashes at startup.

### H2 — Ollama failures return a fabricated result that looks real **[verified]**
`main.py:122-134`: if anything goes wrong, the user gets a hardcoded "PCB Circuit Board" with invented precious-metal amounts and "12V DC". Triggers include Ollama down, timeout, bad JSON, and any exception inside `enrich_analysis`. The UI shows it with a "92% Match" badge, and it is logged to analytics as a real scan.
- Repro: with Ollama unreachable, `POST /api/scan` returned `200 {"item": "PCB Circuit Board", "precious_metals": {"gold_mg": 45, ...}}`, and `/api/analytics` then listed it.
- For a **safety** app this is the most serious issue. A user who scans a swollen lithium battery while the GPU box is down is told it is a circuit board.

### H3 — Multi-angle mode probably can't get past angle 1 **[code reading, high confidence; not run in a browser]**
- After the first capture, `triggerScan` calls `snapDrawer(true)` (`index.html:1103`). That adds `body.drawer-open`, which hides the shutter and sets `pointer-events: none` on it (`:198-202`).
- The only ways to get the shutter back are dragging the drawer down or pressing reset. Both call `snapDrawer(false)`, which calls `resetCameraState()` (`:876`), and that clears `capturedImages = []` (`:881`).
- So the counter returns to 0 every time, and `/api/scan-multi` is unreachable from the UI.

### H4 — Category matching is a naive substring scan, so items get the wrong safety data **[verified]**
`main.py:78-82` returns the first `knowledge.INFO` key that is a substring of `category` or `item`, in dict order. Observed:

| Model says | Matched | Effect |
|---|---|---|
| "Digital **frame**" / "Pictu**re fram**e" | `ram` | No hazards; RAM label decoder runs on it |
| "Head**phone**s", "**Phone** charger" | `phone` | Wrong guidance ("factory reset it") |
| "**Laptop** battery" | `laptop` (before `battery`) | Battery-specific advice ("tape the terminals") lost |
| "SSD", "HDD", "Samsung SSD" | `other` | Drive guidance and **drive label decoding never run** unless the model literally says "hard drive" |
| "USB cable" | `other` | `cable_or_charger` can never match, because the key itself never appears as a substring |

### M1 — Malformed model output crashes enrichment and falls into H2 **[verified]**
`enrich_analysis` assumes types. `specs` as a string raises `AttributeError: 'str' object has no attribute 'update'` (`main.py:102`). A top-level JSON array or a `hazards` string also fails. In `/api/scan`, any of these becomes the fake PCB result (H2). On the frontend, a string `hazards` makes `data.hazards.join` (`index.html:1001`) throw, and a string `text_lines` is decoded per character.

### M2 — The frontend never checks HTTP status
`index.html:1076, 1085, 1120, 1129` call `res.json()` without `res.ok`. A 422/500 body such as `{"detail": ...}` is rendered as "Unknown Circuit Board — 92% Match" (`:956-959`).

### M3 — Knowledge base hazards are overridden by the model, contradicting the design
`knowledge.py:1` says "the AI never invents hazards". However:
- `main.py:87-92` uses the curated hazards only when the model returns none, and the prompt explicitly asks the model for hazards (`main.py:31`).
- The prompt also says "DO NOT list lead as a hazard" (`main.py:27`), while `knowledge.py:22` lists lead solder for motherboards.

The two sources of truth disagree. Model-estimated precious-metal amounts (`main.py:29`) are also shown as fact.

### M4 — Unverified data is labelled "Verified EPA"
- `knowledge.py:4` promises that `sources=None` shows as UNVERIFIED. The UI shows nothing in that case.
- When sources do exist, the heading says "Verified EPA Safety Citations" (`index.html:1030`), but one of the two sources is a Purdue press release (`knowledge.py:9-10`).
- The "AI Double-Check" toggle promises "verified accuracy" (`index.html:731`). The double-check model never sees the image (`main.py:172-177`; the default model `qwen2.5:14b-instruct` is text-only). It can only rewrite JSON.

### M5 — Disposal guidance is never shown
`data.dispose` is computed in `main.py:91-92` but never rendered. The "Dispose Guidance" button opens the Settings modal (`index.html:1050`), which shows a hardcoded list of CT locations. Also:
- When a Li-ion or mercury keyword matches, the specific hazard strings (e.g., "Tape the terminals…", "Older boards may contain lead solder") are replaced by generic copy (`index.html:975-1004`).
- `"battery"` matches the motherboard coin-cell warning and labels it a "High Priority Li-Ion" hazard.

### M6 — Salvage button breaks on any apostrophe **[code reading, plus confirmation that `'` is left unescaped]**
`index.html:1036` builds `onclick="showSalvageModal('${encodeURIComponent(JSON.stringify(data))}')"`. `encodeURIComponent` does not encode `'`, so an item like "Dell's laptop" ends the string literal early. The button then throws a syntax error, and the gap is also an injection vector (see S1).

### M7 — History quota can turn a successful scan into an error *(likely)*
`saveToHistory` stores up to 25 full-resolution JPEG data URIs in `localStorage` (`index.html:1158-1167`). At 1280×720 and quality 0.85, each is roughly 100–300 KB. That likely exceeds the ~5 MB quota on Safari or iOS. The `setItem` call is inside the scan `try` block (`:1089`), so the `QuotaExceededError` lands in `catch`, which overwrites the just-rendered results with "Scan error". `JSON.parse` of a corrupted `revolt_history` would also throw (`:1159, :1172`). I am inferring the quota threshold, not measuring it.

### M8 — Deployment config is inconsistent
- **Port mismatch:** the Dockerfile listens on **8502** (`Dockerfile:6-7`), but compose maps host 8502 → container **8501** (`docker-compose.yml:59`). The service would be unreachable.
- `build: ./revolt` (`docker-compose.yml:54`) and `./searxng` (`:48`) don't exist in this repo. I assume the compose file lives one directory up on the server, but I can't confirm that.
- The default `DOUBLE_CHECK_MODEL` in code (`main.py:20`) differs from compose (`qwen2.5vl:7b`, `docker-compose.yml:63`).

### Low
- **Timeouts can fall back to the fake result.** 60 s (`main.py:114`) may be too short for a cold load of a 12B vision model, and a timeout lands in H2.
- **Splash logo is missing.** Neither `static/logo.png` nor the fallback image exists in `static/`, so the splash shows a broken image. The `onerror` handler (`index.html:599`) points at another missing file, which may cause repeated requests; I have not verified that.
- **Possible SQLite connection leak.** In `get_analytics` (`main.py:191-213`) and `log_scan_analytics` (`:61-68`), an exception before `conn.close()` leaves the connection open. Use `with closing(...)` / context managers.
- **Unhandled torch errors.** `toggleFlash` (`index.html:800-810`) has no `try` around `applyConstraints`, and the `getCapabilities` call is missing on some browsers.
- **Drawer collapse wipes the result.** In single mode, the user cannot glance back at the camera without losing the displayed result.
- **The 92% default confidence is invented** (`index.html:959`).

---

## 5. Security

The app is designed to run on a private Tailscale network, bound to `127.0.0.1`. That deployment model limits the impact of everything below. Severity assumes someone other than the owner can reach the app (e.g., Tailscale sharing or a future public deployment).

### S1 — XSS via model output and `innerHTML` (High)
Model-controlled strings are inserted into HTML unescaped: `item`, `category`, `specs` keys and values, `hazards`, history titles, and analytics rows (`index.html:964-967, 1001, 1016-1022, 1182, 1198, 1208`). The model is asked to **transcribe printed text** (`main.py:25`), so a label or sticker reading `<img src=x onerror=...>` can flow straight into the DOM.
- `item` and `category` are **persisted in SQLite** and shown to **every** user in the analytics modal, which makes this stored XSS.
- `/api/double-check` reflects arbitrary client JSON. **[verified]** It echoed `<img src=x onerror=alert(1)>` back unchanged.
- `sources` hrefs are rendered without validation (`:1031`). If the model emits its own `sources` for a category without curated ones, a `javascript:` URL would be clickable.

Fix: build DOM nodes with `textContent`, or escape every interpolation.

### S2 — No authentication or rate limiting on any endpoint (Medium)
`main.py:136-219`. Anyone who can reach the port can:
- run GPU inference without limit (`/api/scan`, `/api/scan-multi`, `/api/double-check`),
- read scan history via `/api/analytics`.

The design relies entirely on network placement. That is acceptable for a demo, but write it down.

### S3 — Unbounded uploads (Medium)
- No size, count, or content-type checks (`main.py:138, 151-154`).
- Each file is read fully into memory, then base64-inflated by about 33%.
- `/api/scan-multi` accepts any number of files.
- Non-images are accepted. **[verified]** `b"not an image"` was accepted (it then hit the fake fallback).

### S4 — Internal error strings are exposed (Low)
`main.py:213` returns `str(e)` to the client.

### S5 — Infrastructure issues (Medium)
- `open-webui` is published on **all interfaces** (`docker-compose.yml:26`, `"3000:8080"`), unlike the other services, whose comments say they are deliberately bound to localhost. It has Prometheus metrics enabled (`:28-31`).
- `SEARXNG_SECRET=` is empty (`:51`).
- All images are unpinned `:latest` / `:main` (`:3, 22, 41`), and `requirements.txt` has no version pins. Builds are not reproducible, and a compromised or broken upstream release would flow straight in.
- The container runs as root (`Dockerfile` has no `USER`).

### S6 — Third-party CDN load (Low)
Font Awesome is loaded from cdnjs without SRI (`index.html:7`). This contradicts the README's "NO cloud dependence" claim (`README.md:4`) and leaks client IPs to a CDN.

### S7 — Prompt injection (Low–Medium)
`main.py:25` tells the model to treat printed text as data. That is a good mitigation but not a guarantee. The double-check prompt pastes untrusted JSON directly into the instruction text (`main.py:170`). TODO #13 ("AI guard rail") acknowledges this.

**No hardcoded secrets were found** in tracked files.

---

## 6. Performance

The app has one server and one GPU, and the bottleneck is model inference. Most of these issues only matter under concurrency.

- **Blocking SQLite in async handlers.** Sync `sqlite3` calls inside `async def` routes (`main.py:141, 156, 192`) block the event loop. They are tiny writes, so the effect is negligible today. Use `def` routes or `run_in_threadpool`.
- **New HTTP client per request.** A new `httpx.AsyncClient` is created for each request (`main.py:114, 178`), so there is no connection reuse. Minor.
- **No image resizing.** 1280×720 frames are sent at full size to the model, three times in multi mode (TODO #11). Downscaling to around 768–1024 px on the long edge on the client would cut upload size, inference time, and `localStorage` usage (M7).
- **No concurrency control around Ollama.** Several simultaneous scans queue on the GPU while each request holds a 60 s timeout. Under load, timeouts lead to H2 fake results.
- **Synchronous double-check.** When enabled, the double-check is a second sequential LLM call, which roughly doubles latency.
- **Model loading is not managed.** Two different 7–14B models alternate on one GPU, which can cause load/unload thrashing. This depends on VRAM and Ollama's `keep_alive` setting; I have not measured it.

---

## 7. Testing

**There is no test suite**: no `tests/` directory, no pytest config, and no CI. I ran an ad-hoc smoke script from a scratch directory, without adding it to the repo. Results:

| Check | Result |
|---|---|
| `labels.decode_ram` on PC4-2666 / PC3L-12800S / DDR4 3200MHz | ✅ correct |
| `labels.decode_drive` on HDD / NVMe M.2 / "64MB cache 2TB" | ✅ correct |
| `enrich_analysis` category matching | ❌ see H4 table |
| `enrich_analysis` with `specs` as a string | ❌ `AttributeError` |
| `/api/scan` with Ollama down | ❌ returns fabricated PCB result, logs it |
| `/api/double-check` with HTML payload | ⚠️ reflects unchanged |
| Committed `HEAD:main.py` parses | ❌ `IndentationError` |

**Critical paths with no coverage (in priority order):**
1. `enrich_analysis`: category matching, merging, and type robustness. This is the safety-critical logic.
2. Error paths in `query_ollama_vision` / `double_check`, using a mocked Ollama.
3. `labels.py`: a table-driven test of real label strings. It is pure and easy to test.
4. API contract tests with `TestClient`, covering upload limits, multi-file, and the analytics shape.
5. Frontend multi-angle flow (H3) and rendering escapes (S1), e.g., with Playwright.
6. A `python -m py_compile *.py` check in CI, which would have caught H1.

---

## 8. Recommendations

Effort: **S** < 2 h, **M** half-day to a day, **L** multiple days.

### High
| # | Action | Fixes | Effort |
|---|---|---|---|
| 1 | Commit the `main.py` line-1 fix; add a CI or pre-commit `py_compile` check | H1 | S |
| 2 | Delete the fake fallback; return an explicit error (HTTP 503 with `{"error": ...}`), show "Scan failed, try again" in the UI, and don't log failed scans | H2, M2 | S |
| 3 | Escape all model output in the frontend (`textContent` or an `escapeHtml` helper); validate `sources` URLs; replace inline `onclick` with `addEventListener` and keep `data` in a closure | S1, M6 | M |
| 4 | Fix multi-angle: don't call `resetCameraState()` from `snapDrawer(false)`; reset only when the user starts a new scan | H3 | S |
| 5 | Replace substring matching with explicit categories. Have the model choose from the exact `knowledge.INFO` keys (enum in the prompt), plus a synonym map (`ssd`/`hdd` → `hard_drive`, `charger`/`cable` → `cable_or_charger`) using whole-word matching | H4 | M |
| 6 | Make `knowledge.py` the authority for hazards: always show curated hazards and show model hazards as "AI-observed (unverified)"; show "Unverified" when `sources is None`; rename the "Verified EPA" heading | M3, M4 | S–M |

### Medium
| # | Action | Fixes | Effort |
|---|---|---|---|
| 7 | Validate model output with a Pydantic schema (coerce types, drop unknown keys) before enrichment | M1 | M |
| 8 | Render `dispose` steps and the specific hazard strings in the drawer; point "Dispose Guidance" at them | M5 | S |
| 9 | Add upload limits (size, count ≤ 3, image MIME check) and a semaphore around Ollama calls | S3, perf | S |
| 10 | Store thumbnails (about 128 px) in history instead of full frames; wrap `localStorage` calls in try/catch; move `saveToHistory` out of the scan `try` | M7 | S |
| 11 | Fix compose: port 8502↔8501 mismatch, bind open-webui to `127.0.0.1`, set `SEARXNG_SECRET`, pin image tags | M8, S5 | S |
| 12 | Pin `requirements.txt`; add `httpx`; remove unused `ollama` and `pillow` (or use Pillow for server-side resizing) | deps | S |
| 13 | Add a pytest suite for `labels.py` and `enrich_analysis`, and mocked-Ollama API tests | §7 | M |
| 14 | Either give the double-check model the image (a vision model) or relabel the feature honestly | M4 | S |

### Low
| # | Action | Effort |
|---|---|---|
| 15 | Deduplicate the single and multi scan code (frontend and backend) | S |
| 16 | Switch to `logging`, use context-managed SQLite connections, and use sync routes for DB work | S |
| 17 | Self-host Font Awesome (or use inline SVG) to honor the "no cloud" promise | S |
| 18 | Add the missing logo asset; add `.venv/`, `*.db`, `.DS_Store` to `.gitignore` | S |
| 19 | Update the README (FastAPI, not Streamlit; complete Quickstart; document the Tailscale-only trust model) | S |
| 20 | Add a resize step before upload (TODO #11) and test the iOS torch API with error handling | S |

---

### Uncertainties
- Whether `docker-compose.yml` is meant to be used from a parent directory (where `./revolt` and `./searxng` would exist).
- The exact `localStorage` limit at which M7 triggers on the target devices.
- Whether the splash `onerror` fallback actually loops in practice.
- H3 is based on code reading; I did not drive the UI in a browser.
