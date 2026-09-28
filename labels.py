"""Decode text printed on labels (RAM, hard drives, SSDs) into clean specs.

Plain code on purpose: the vision model only READS the label; this file decides
what it means. That is far more reliable than asking the model to guess.
"""
import re

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


def decode(category: str, lines):
    """Return (specs, complete). complete=False means: ask for a label close-up."""
    if category == "ram":
        return decode_ram(lines)
    if category == "hard_drive":
        return decode_drive(lines)
    return {}, True
