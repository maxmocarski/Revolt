"""Hand-written safety data. NOT model output: the AI never invents hazards.

Each entry: hazards, salvage, dispose, sources. sources=None means UNVERIFIED and
the app says so on screen. Only add a source after you have actually read it.

Every hazard has a level, which sets its colour and the verdict at the top of a result:
  danger  - can hurt someone (fire, toxic material)
  caution - handle or sort it carefully
  privacy - personal data to protect
"""


def danger(text):
    return {"level": "danger", "text": text}


def caution(text):
    return {"level": "caution", "text": text}


def privacy(text):
    return {"level": "privacy", "text": text}


# Display names for the INFO keys below.
LABELS = {
    "motherboard": "Motherboard / circuit board",
    "ram": "RAM (memory)",
    "laptop": "Laptop",
    "phone": "Phone",
    "battery": "Battery",
    "hard_drive": "Hard drive / SSD",
    "gpu": "Graphics card",
    "cable_or_charger": "Cable or charger",
    "printer": "Printer",
    "display": "Monitor / display",
    "other": "Other e-waste",
}

# Rough typical weights, used only for the "≈ kg of e-waste" estimate on the home screen.
TYPICAL_WEIGHT_KG = {
    "motherboard": 0.5,
    "ram": 0.03,
    "laptop": 2.0,
    "phone": 0.2,
    "battery": 0.1,
    "hard_drive": 0.4,
    "gpu": 0.8,
    "cable_or_charger": 0.2,
    "printer": 6.0,
    "display": 5.0,
    "other": 0.5,
}

BATTERY_WARNING = danger("Contains a lithium-ion battery: fire risk if punctured or crushed.")

_LCD_SOURCES = [
    ("Purdue (EPA-funded research)",
     "https://www.purdue.edu/newsroom/releases/2012/Q4/holiday-shopping-adds-to-e-waste,-but-help-is-on-the-way.html"),
    ("EPA research abstract on LCD recycling",
     "https://cfpub.epa.gov/ncer_abstracts/index.cfm/fuseaction/display.abstractDetail/abstract_id/9847/report/F"),
]
_RECYCLE = ["Do not put it in household trash.",
            "Take it to an e-waste recycler or a retailer take-back program."]
_MERCURY = danger("Screens made before about 2009 use fluorescent backlights that contain "
                  "mercury. Do not break or crush the screen.")

INFO = {
    "motherboard": {
        "hazards": [caution("May hold a lithium coin cell. Remove it and recycle it separately."),
                    caution("Older boards may contain lead solder.")],
        "salvage": ["RAM", "CPU", "Coin cell battery", "Heatsinks"],
        "dispose": _RECYCLE, "sources": None},
    "ram": {
        "hazards": [], "salvage": ["The whole module, if it fits your other machines"],
        "dispose": ["Reuse it if it still works.", *_RECYCLE], "sources": None},
    "laptop": {
        "hazards": [BATTERY_WARNING, _MERCURY],
        "salvage": ["RAM", "SSD/HDD (wipe data first)", "Battery", "Screen", "Charger"],
        "dispose": ["Remove and wipe the drive first.", "Take the battery out if you can.", *_RECYCLE],
        "sources": None},
    "phone": {
        "hazards": [BATTERY_WARNING, danger("A swollen battery is a fire risk: do not charge or puncture it.")],
        "salvage": ["Screen", "Camera", "Battery", "Charging port"],
        "dispose": ["Sign out of your accounts and factory reset it.", *_RECYCLE], "sources": None},
    "battery": {
        "hazards": [BATTERY_WARNING, caution("Tape the terminals to prevent short circuits.")],
        "salvage": [],
        "dispose": ["Use a battery drop-off, not the trash or curbside recycling."], "sources": None},
    "hard_drive": {
        "hazards": [privacy("Holds personal data: wipe or physically destroy it before recycling.")],
        "salvage": ["The whole drive, if it works (wipe it first)", "Magnets from spinning disks"],
        "dispose": ["Wipe or destroy the data first.", *_RECYCLE], "sources": None},
    "gpu": {
        "hazards": [], "salvage": ["The whole card, if it works", "Fans", "Heatsink"],
        "dispose": ["Reuse or sell it if it works.", *_RECYCLE], "sources": None},
    "cable_or_charger": {
        "hazards": [], "salvage": ["A working charger", "Copper wire"],
        "dispose": _RECYCLE, "sources": None},
    "printer": {
        "hazards": [caution("Remove ink and toner cartridges first. Toner is a fine powder: do not spill or inhale it.")],
        "salvage": ["Cartridges (many makers take them back)", "Motors and gears", "Power supply"],
        "dispose": ["Take the cartridges out first.", *_RECYCLE], "sources": None},
    "display": {
        "hazards": [_MERCURY], "salvage": ["Power supply", "Stand", "Cables"],
        "dispose": ["Keep it intact and take it to an e-waste recycler.", "Do not put it in the trash."],
        "sources": _LCD_SOURCES},
    "other": {
        "hazards": [caution("Unknown item: check for batteries and do not crush or puncture it.")],
        "salvage": [], "dispose": _RECYCLE, "sources": None},
}
