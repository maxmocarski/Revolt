"""Hand-written safety data. NOT model output: the AI never invents hazards.

Each entry: hazards, salvage, dispose, sources. sources=None means UNVERIFIED and
the app says so on screen. Only add a source after you have actually read it.
"""
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

BATTERY_WARNING ="Contains a lithium-ion battery: fire risk if punctured or crushed."

_LCD_SOURCES = [
    ("Purdue (EPA-funded research)",
     "https://www.purdue.edu/newsroom/releases/2012/Q4/holiday-shopping-adds-to-e-waste,-but-help-is-on-the-way.html"),
    ("EPA research abstract on LCD recycling",
     "https://cfpub.epa.gov/ncer_abstracts/index.cfm/fuseaction/display.abstractDetail/abstract_id/9847/report/F"),
]
_RECYCLE = ["Do not put it in household trash.",
            "Take it to an e-waste recycler or a retailer take-back program."]
_MERCURY = ("Screens made before about 2009 use fluorescent backlights that contain "
            "mercury. Do not break or crush the screen.")

INFO = {
    "motherboard": {
        "hazards": ["May hold a lithium coin cell. Remove it and recycle it separately.",
                    "Older boards may contain lead solder."],
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
        "hazards": [BATTERY_WARNING, "A swollen battery is a fire risk: do not charge or puncture it."],
        "salvage": ["Screen", "Camera", "Battery", "Charging port"],
        "dispose": ["Sign out of your accounts and factory reset it.", *_RECYCLE], "sources": None},
    "battery": {
        "hazards": [BATTERY_WARNING, "Tape the terminals to prevent short circuits."],
        "salvage": [],
        "dispose": ["Use a battery drop-off, not the trash or curbside recycling."], "sources": None},
    "hard_drive": {
        "hazards": ["Holds personal data: wipe or physically destroy it before recycling."],
        "salvage": ["The whole drive, if it works (wipe it first)", "Magnets from spinning disks"],
        "dispose": ["Wipe or destroy the data first.", *_RECYCLE], "sources": None},
    "gpu": {
        "hazards": [], "salvage": ["The whole card, if it works", "Fans", "Heatsink"],
        "dispose": ["Reuse or sell it if it works.", *_RECYCLE], "sources": None},
    "cable_or_charger": {
        "hazards": [], "salvage": ["A working charger", "Copper wire"],
        "dispose": _RECYCLE, "sources": None},
    "printer": {
        "hazards": ["Remove ink and toner cartridges first. Toner is a fine powder: do not spill or inhale it."],
        "salvage": ["Cartridges (many makers take them back)", "Motors and gears", "Power supply"],
        "dispose": ["Take the cartridges out first.", *_RECYCLE], "sources": None},
    "display": {
        "hazards": [_MERCURY], "salvage": ["Power supply", "Stand", "Cables"],
        "dispose": ["Keep it intact and take it to an e-waste recycler.", "Do not put it in the trash."],
        "sources": _LCD_SOURCES},
    "other": {
        "hazards": ["Unknown item: check for batteries and do not crush or puncture it."],
        "salvage": [], "dispose": _RECYCLE, "sources": None},
}
