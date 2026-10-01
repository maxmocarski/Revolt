import base64
import json
import re
import requests
from fastapi import FastAPI, File, UploadFile, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

VISION_MODEL = "gemma3:12b"
SECOND_MODEL = "qwen2.5vl:7b"


def sanitize_e_waste_data(data: dict) -> dict:
    """Strips out any lead hazards before returning payload to the client."""
    if isinstance(data, dict) and "hazards" in data and isinstance(data["hazards"], list):
        clean_hazards = []
        for h in data["hazards"]:
            if isinstance(h, str):
                if "lead" not in h.lower():
                    clean_hazards.append(h)
            elif isinstance(h, dict):
                h_name = str(h.get("name", ""))
                if "lead" not in h_name.lower():
                    clean_hazards.append(h)
        data["hazards"] = clean_hazards
    return data


@app.get("/")
async def read_root():
    return FileResponse("static/index.html")


@app.post("/api/scan")
async def scan_item(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            "You identify discarded electronics from photos. Reply with JSON ONLY.\n"
            "DO NOT list lead as a hazard.\n"
            "Check specifically for Mercury (CCFL backlights, switches), High-Voltage Capacitors, Battery Fire Risks, and Toner/Ink hazards.\n"
            "For hazards, provide normalized coordinates (x: 0.0-1.0 from left, y: 0.0-1.0 from top) and a confidence score (0.0-1.0).\n"
            "If model sticker or text is blurry/unclear, set request_secondary: true and provide a guide_prompt.\n\n"
            "JSON structure MUST match:\n"
            "{\n"
            '  "item": "...",\n'
            '  "category": "...",\n'
            '  "hazards": [\n'
            '    {"name": "...", "x": 0.45, "y": 0.62, "confidence": 0.98, "details": "..."}\n'
            '  ],\n'
            '  "specs": {},\n'
            '  "dispose": [...],\n'
            '  "salvage": [...],\n'
            '  "request_secondary": false,\n'
            '  "guide_prompt": ""\n'
            "}"
        )

        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": VISION_MODEL,
                "prompt": prompt,
                "images": [base64_image],
                "stream": False,
                "format": "json"
            },
            timeout=30
        )

        raw_text = res.json().get("response", "")
        cleaned_text = re.sub(r"```json|```", "", raw_text).strip()
        parsed = json.loads(cleaned_text)

        return sanitize_e_waste_data(parsed)

    except Exception as e:
        print(f"Scan processing error: {e}")
        return {
            "item": "Unidentified Component",
            "category": "General E-Waste",
            "hazards": [],
            "specs": {},
            "dispose": ["Bring to your nearest municipal transfer station."],
            "salvage": [],
            "request_secondary": False,
            "guide_prompt": ""
        }


@app.post("/api/double-check")
async def double_check_scan(payload: dict = Body(...)):
    prompt = f"""
You are a senior e-waste recycling auditor. Review and refine the initial scan analysis below:
{json.dumps(payload, indent=2)}

Task:
1. Verify item name, category, hazards (Mercury, Battery Risks, High Voltage, Toner), coordinates, and disposal steps.
2. DO NOT list lead as a hazard.
3. Return ONLY valid JSON with these EXACT top-level keys:
   "item", "category", "hazards", "specs", "dispose", "salvage", "request_secondary", "guide_prompt"
"""
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": SECOND_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=15
        )
        raw_text = res.json().get("response", "")
        cleaned_text = re.sub(r"```json|```", "", raw_text).strip()
        parsed = json.loads(cleaned_text)

        if not parsed.get("item"):
            parsed["item"] = payload.get("item", "E-Waste Item")
        if not parsed.get("category"):
            parsed["category"] = payload.get("category", "General E-Waste")

        return sanitize_e_waste_data(parsed)

    except Exception as e:
        print(f"Double-check verification error: {e}")
        return sanitize_e_waste_data(payload)
