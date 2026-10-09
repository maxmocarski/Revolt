"""Regenerate fixtures.json (canned scan results for run_ui_tests.mjs) from the real backend logic.

Run from the repo root:  .venv/bin/python tests/ui/make_fixtures.py
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("REVOLT_DB_PATH", os.path.join(tempfile.mkdtemp(), "fixtures.db"))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import main  # noqa: E402

FIXTURES = {
    "laptop": main.enrich_analysis({
        "item": "Dell Latitude laptop", "category": "laptop", "hazards": ["Battery looks swollen near hinge"],
        "specs": {"Form Factor": "Folding laptop", "Screen": "14 inch"}, "salvage": ["Webcam"],
        "precious_metals": {"gold_mg": 150, "copper_g": 20}}),
    "drive": main.enrich_analysis({
        "item": "WD Blue 1TB drive (Dell's)", "category": "hard_drive", "text_lines": ["WD 1TB 7200 RPM SATA 3.5 IN"]}),
    "ram": main.enrich_analysis({"item": "Kingston RAM stick", "category": "ram", "text_lines": ["DDR4 8GB"]}),
    "printer": main.enrich_analysis({"item": "HP inkjet printer", "category": "printer"}),
}

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures.json"), "w") as f:
    json.dump(FIXTURES, f, indent=1)
print("wrote", len(FIXTURES), "fixtures")
