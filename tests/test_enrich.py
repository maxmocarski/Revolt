import pytest

import main


@pytest.mark.parametrize("category, item, expected", [
    ("ram", "anything", "ram"),                      # exact key
    ("Hard Drive", "x", "hard_drive"),               # key with a space
    ("Battery", "Laptop battery", "battery"),        # the part, not the device it came from
    ("Charger", "Laptop charger", "cable_or_charger"),
    ("SSD", "Samsung SSD", "hard_drive"),
    ("Memory", "RAM Module", "ram"),
    ("Cable", "USB cable", "cable_or_charger"),
    ("Storage", "microSD card", "hard_drive"),
    ("Audio", "Headphones", "other"),                # "phone" inside a word doesn't count
    ("Picture frame", "Digital frame", "other"),     # neither does "ram" inside "frame"
    ("", "", "other"),
])
def test_match_category(category, item, expected):
    assert main.match_category(category, item) == expected


def test_curated_hazards_come_with_levels_and_ai_duplicates_are_dropped():
    result = main.enrich_analysis({
        "item": "battery pack", "category": "battery",
        "hazards": ["Contains a lithium-ion battery: fire risk if punctured or crushed.", "Casing is dented"],
    })
    assert [h["level"] for h in result["hazards"]] == ["danger", "caution"]
    assert result["ai_hazards"] == ["Casing is dented"]
    assert result["typical_weight_kg"] > 0


def test_label_specs_and_ai_specs_are_kept_apart():
    result = main.enrich_analysis({
        "item": "RAM stick", "category": "ram",
        "specs": {"Speed": "fast", "Color": "green", "Voltage": "Unknown"},
        "text_lines": ["8GB PC4-2666V SODIMM"],
    })
    assert result["specs"]["Speed"] == "2666 MT/s"                 # from the label
    assert result["ai_specs"] == {"Color": "green"}                 # label wins; placeholder dropped
    assert result["label_hint"] is False


def test_incomplete_label_asks_for_close_up():
    result = main.enrich_analysis({"item": "RAM", "category": "ram", "text_lines": ["DDR4 8GB"]})
    assert result["label_hint"] is True


def test_messy_model_output_is_cleaned():
    result = main.enrich_analysis({
        "item": "  ", "category": "laptop",
        "hazards": "single string", "salvage": [{"name": "Webcam"}, None, 3],
        "specs": "not a dict",
        "precious_metals": {"gold_mg": "12", "copper_g": None, "silver_mg": "lots"},
        "hazard_hotspots": [{"x_pct": 500, "y_pct": -3, "confidence": 2}, "junk"],
    })
    assert result["item"] == "Unidentified item"
    assert result["ai_hazards"] == ["single string"]
    assert result["ai_salvage"] == ["Webcam", "3"]
    assert result["ai_specs"] == {}
    assert result["precious_metals"] == {"gold_mg": 12.0}
    assert result["hazard_hotspots"][0]["x_pct"] == 100
    assert result["hazard_hotspots"][0]["y_pct"] == 0
    assert result["hazard_hotspots"][0]["confidence"] == 1


@pytest.mark.parametrize("raw", [[1, 2], "text", None, 42])
def test_non_object_model_output_is_rejected(raw):
    with pytest.raises(ValueError):
        main.enrich_analysis(raw)


def test_ai_reported_lead_is_dropped_but_similar_words_are_kept():
    result = main.enrich_analysis({
        "item": "board", "category": "motherboard",
        "hazards": ["Contains lead solder", "LEAD in the joints", "Loose leads on the capacitors", "Bulging capacitor"],
    })
    assert result["ai_hazards"] == ["Loose leads on the capacitors", "Bulging capacitor"]


def test_markdown_fenced_model_json_is_parsed():
    assert main._parse_model_json('```json\n{"item": "x"}\n```') == {"item": "x"}
    assert main._parse_model_json('{"item": "y"}') == {"item": "y"}


def test_both_setting_names_are_accepted(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://gpu-box:11434")
    assert main._env("OLLAMA_HOST", "OLLAMA_BASE_URL", default="d") == "http://gpu-box:11434"
    monkeypatch.setenv("OLLAMA_HOST", "http://preferred:11434")
    assert main._env("OLLAMA_HOST", "OLLAMA_BASE_URL", default="d") == "http://preferred:11434"
    assert main._env("NOT_SET_ANYWHERE", default="fallback") == "fallback"
