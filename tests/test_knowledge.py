import knowledge

LEVELS = {"danger", "caution", "privacy"}


def test_every_hazard_has_a_level_and_text():
    for category, info in knowledge.INFO.items():
        for hazard in info["hazards"]:
            assert hazard["level"] in LEVELS, category
            assert hazard["text"].strip(), category


def test_every_category_has_a_label_weight_and_disposal_steps():
    for category, info in knowledge.INFO.items():
        assert category in knowledge.LABELS
        assert knowledge.TYPICAL_WEIGHT_KG[category] > 0
        assert info["dispose"], category


def test_sources_are_https_links():
    for category, info in knowledge.INFO.items():
        for name, url in info["sources"] or []:
            assert name and url.startswith("https://"), category
