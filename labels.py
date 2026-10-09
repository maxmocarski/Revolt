"""Decode text printed on labels (RAM, hard drives, SSDs) into clean specs.

Plain code on purpose: the vision model only READS the label; this file decides
what it means. That is far more reliable than asking the model to guess.
"""
import re

# type of CPU pattern, basically size of cpu... intel core, intel xeon, amd ryzena and amd threadripper.
_CPU_PATTERNS = [
    r"\b(I[3579][-\s]?\d{4,5}[A-Z]{0,3})\b",
    r"\b(E[357][-\s]?\d{4}[A-Z0-9]?|W[-\s]?\d{4}[A-Z]?|(?:BRONZE|SILVER|GOLD|PLATINUM)\s?\d{4}[A-Z]?)\b",
    r"\b(?:RYZEN\s?[3579]|R[3579])\s?(\d{4}[A-Z0-9]*)\b",
    r"\b(EPYC\s?\d{4}[A-Z]?|THREADRIPPER\s?\d{4}[A-Z]*)\b",
]

# type of socket for motherboard
_SOCKET_PATTERNS = [
    r"\b(LGA\s?\d{3,4})\b",
    r"\b(AM[2-5][+]?)\b",
    r"\b(TR4|sTRX4|sWRX8)\b",
]
# type of chipset for motherboard
_CHIPSET_PATTERNS = [
    r"\b([ABZHX]\d{3,4}[A-Z]?)\b", 
    r"\b(TRX\d{2})\b",
]

# PSU wattages and ratings
_80PLUS_RATINGS = ["TITANIUM","PLATINUM","GOLD","SILVER","BRONZE","80 PLUS",]

# Standard speeds (MT/s) per DDR generation, used to snap label numbers.
_STANDARD = {
    2: [400, 533, 667, 800, 1066],
    3: [800, 1066, 1333, 1600, 1866, 2133],
    4: [1600, 1866, 2133, 2400, 2666, 2933, 3200],
    5: [4000, 4400, 4800, 5200, 5600, 6000, 6400, 6800, 7200, 8000],
}
_RAM_SIZES_GB = {1, 2, 4, 8, 16, 32, 48, 64, 96, 128}




def _snap(gen: int, value: int) -> int:
    return min(_STANDARD[gen], key=lambda s: abs(s - value))


def _speed_from_pc(gen: int, n: int) -> int:
    """PC-codes are sometimes MT/s (PC4-2666) and sometimes bandwidth (PC4-21300 = 8 x MT/s)."""
    is_bandwidth = ((gen == 2 and n >= 3000) or (gen == 3 and n >= 5000)
                    or (gen == 4 and n >= 10000) or (gen == 5 and n >= 20000))
    return _snap(gen, round(n / 8) if is_bandwidth else n)


def decode_ram(lines):
    text = " ".join(lines).upper().replace("SO-DIMM", "SODIMM")
    gen = speed = None
    m = re.search(r"PC([2-5])L?[-\s]?(\d{3,5})", text)
    if m:
        gen = int(m.group(1))
        speed = _speed_from_pc(gen, int(m.group(2)))
    else:
        m = re.search(r"DDR([2-5])L?[-\s]?(\d{3,4})", text)
        if m:
            gen = int(m.group(1))
            speed = _snap(gen, int(m.group(2)))
        else:
            m = re.search(r"DDR([2-5])", text)
            if m:
                gen = int(m.group(1))
    if speed is None and gen:
        m = re.search(r"(\d{3,4})\s?(?:MHZ|MT/S)", text)
        if m:
            speed = _snap(gen, int(m.group(1)))

    specs = {}
    if gen:
        specs["Type"] = f"DDR{gen}" + ("L (low voltage)" if re.search(r"PC3L|DDR3L", text) else "")
    if speed:
        specs["Speed"] = f"{speed} MT/s"
    for m in re.finditer(r"(\d{1,3})\s?GB", text):
        if int(m.group(1)) in _RAM_SIZES_GB:
            specs["Capacity"] = f"{m.group(1)} GB"
            break
    if "SODIMM" in text:
        specs["Form factor"] = "SODIMM (laptop)"
    elif re.search(r"\b(LRDIMM|RDIMM|FBDIMM)\b", text):
        specs["Form factor"] = "Server RDIMM"
    elif "DIMM" in text:
        specs["Form factor"] = "DIMM (desktop)"
    return specs, bool(gen and speed)


def decode_drive(lines):
    text = " ".join(lines).upper()
    specs = {}
    rpm = re.search(r"(\d{4,5})\s?RPM", text)
    interface = next((n for n in ("NVME", "SATA", "SAS", "IDE", "PATA") if n in text), None)
    if "SSD" in text or interface == "NVME" or "M.2" in text:
        specs["Type"] = "SSD"
    elif rpm:
        specs["Type"] = "Hard disk (HDD)"
    m = re.search(r"(\d+(?:\.\d+)?)\s?(TB|GB)", text)
    if m:
        specs["Capacity"] = f"{m.group(1)} {m.group(2)}"
    if rpm:
        specs["Speed"] = f"{rpm.group(1)} RPM"
    if interface:
        specs["Interface"] = {"NVME": "NVMe"}.get(interface, interface)
    m = re.search(r"(2\.5|3\.5)\s?(?:\"|IN\b|INCH)", text)
    if m:
        specs["Size"] = f'{m.group(1)}"'
    elif "M.2" in text:
        specs["Size"] = "M.2"
    return specs, bool("Capacity" in specs and ("Interface" in specs or "Speed" in specs))


    
def decode_psu(lines):
    text = " ".join(lines).upper()
    specs = {}

    # Total Output Wattage (e.g., 750W, 750 W, 1000W, MAX OUTPUT: 650W)
    m = re.search(r"(\d{3,4})\s?W\b", text)
    if m:
        specs["Wattage"] = f"{m.group(1)}W"

    # 80 PLUS Efficiency Rating
    for rating in _80PLUS_RATINGS:
        if rating in text:
            if rating == "80 PLUS":
                specs["Efficiency"] = "80 PLUS (White/Standard)"
            else:
                specs["Efficiency"] = f"80 PLUS {rating.capitalize()}"
            break

    # Modularity
    if "FULLY MODULAR" in text or "FULL MODULAR" in text:
        specs["Modularity"] = "Fully Modular"
    elif "SEMI-MODULAR" in text or "SEMI MODULAR" in text:
        specs["Modularity"] = "Semi-Modular"
    elif "NON-MODULAR" in text or "DIRECT CABLE" in text:
        specs["Modularity"] = "Non-Modular"

    # Form Factor
    if "SFX-L" in text:
        specs["Form factor"] = "SFX-L"
    elif "SFX" in text:
        specs["Form factor"] = "SFX (Compact)"
    elif "TFX" in text:
        specs["Form factor"] = "TFX"
    elif "FLEX" in text or "FLEX-ATX" in text:
        specs["Form factor"] = "Flex-ATX"
    elif "ATX" in text:
        specs["Form factor"] = "ATX (Standard)"

    # AC Input Voltage Range (e.g., 100-240V or 115V/230V)
    m = re.search(r"(\d{3}(?:[-/]\d{3})?)\s?V\b", text)
    if m:
        specs["AC Input"] = f"{m.group(1)}V"

    # A PSU spec read is 'complete' if we found at least the Wattage
    return specs, bool("Wattage" in specs)

def decode_motherboard(lines):
    text = " ".join(lines).upper()
    specs = {}

    # Chipset 
    for pattern in _CHIPSET_PATTERNS:
        m = re.search(pattern, text)
        if m:
            specs["Chipset"] = m.group(1)
            break

    # CPU Socket 
    for pattern in _SOCKET_PATTERNS:
        m = re.search(pattern, text)
        if m:
            specs["Socket"] = m.group(1)
            break

    # Supported RAM Type
    m = re.search(r"\b(DDR[3-5])\b", text)
    if m:
        specs["Memory support"] = m.group(1)

    # Form Factor
    if "E-ATX" in text or "EXTENDED ATX" in text:
        specs["Form factor"] = "E-ATX"
    elif "MINI-ITX" in text or "ITX" in text:
        specs["Form factor"] = "Mini-ITX"
    elif "MICRO-ATX" in text or "MATX" in text or "M-ATX" in text:
        specs["Form factor"] = "Micro-ATX"
    elif "ATX" in text:
        specs["Form factor"] = "ATX"

    # A motherboard spec read is considered complete if we found at least the Chipset or Socket
    return specs, bool("Chipset" in specs or "Socket" in specs)


def decode_cpu(lines):
    text = " ".join(lines).upper()
    specs = {}

    # Model / Processor Name
    # 1. Check Intel Core / Xeon / EPYC / Threadripper
    for pattern in _CPU_PATTERNS:
        m = re.search(pattern, text)
        if m:
            specs["Model"] = m.group(0).replace("  ", " ")
            break

    # 2. Check standalone AMD Ryzen pattern if full string wasn't captured above
    if "Model" not in specs and "RYZEN" in text:
        m = re.search(r"\bRYZEN\b.*?\b(\d{4}[A-Z0-9]*)\b", text)
        if m:
            specs["Model"] = f"AMD Ryzen {m.group(1)}"

    # Base Clock / Speed (e.g., 3.60GHZ, 2.8 GHZ)
    m = re.search(r"(\d\.\d{1,2})\s?GHZ", text)
    if m:
        specs["Base clock"] = f"{m.group(1)} GHz"

    # Core count 
    m = re.search(r"(\d{1,2})[-\s]?CORE", text)
    if m:
        specs["Cores"] = f"{m.group(1)} Cores"

    # Socket (if printed)
    m = re.search(r"\b(LGA\s?\d{3,4}|AM[45]|sTRX4)\b", text)
    if m:
        specs["Socket"] = m.group(1)

    return specs, bool("Model" in specs)


def decode(category: str, lines):
    """Return (specs, complete). complete=False means: ask for a label close-up."""
    if category == "ram":
        return decode_ram(lines)
    if category == "hard_drive":
        return decode_drive(lines)
    if category in ("psu", "power_supply"):
        return decode_psu(lines)
    if category == "motherboard":
        return decode_motherboard(lines)
    if category in ("cpu", "processor"):
        return decode_cpu(lines)
    return {}, True
