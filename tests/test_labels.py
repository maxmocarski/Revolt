import pytest

import labels


@pytest.mark.parametrize("lines, expected", [
    (["8GB 1Rx8 PC4-2666V-SA1-11", "SODIMM"],
     {"Type": "DDR4", "Speed": "2666 MT/s", "Capacity": "8 GB", "Form factor": "SODIMM (laptop)"}),
    (["4GB PC3L-12800S"], {"Type": "DDR3L (low voltage)", "Speed": "1600 MT/s", "Capacity": "4 GB"}),
    (["16GB PC4-21300 DIMM"], {"Type": "DDR4", "Speed": "2666 MT/s", "Capacity": "16 GB", "Form factor": "DIMM (desktop)"}),
    (["DDR4 16GB 3200MHz"], {"Type": "DDR4", "Speed": "3200 MT/s", "Capacity": "16 GB"}),
    (["32GB DDR5-4800 RDIMM"], {"Type": "DDR5", "Speed": "4800 MT/s", "Capacity": "32 GB", "Form factor": "Server RDIMM"}),
])
def test_ram_labels(lines, expected):
    specs, complete = labels.decode("ram", lines)
    assert specs == expected
    assert complete


def test_ram_without_speed_is_incomplete():
    specs, complete = labels.decode("ram", ["DDR4 8GB"])
    assert specs == {"Type": "DDR4", "Capacity": "8 GB"}
    assert not complete


@pytest.mark.parametrize("lines, expected", [
    (["WD 1TB 7200 RPM SATA 3.5 IN"],
     {"Type": "Hard disk (HDD)", "Capacity": "1 TB", "Speed": "7200 RPM", "Interface": "SATA", "Size": '3.5"'}),
    (["Samsung 970 EVO 500GB NVMe M.2"], {"Type": "SSD", "Capacity": "500 GB", "Interface": "NVMe", "Size": "M.2"}),
    # "64MB" cache must not be mistaken for the drive's capacity.
    (["64MB Cache", "2TB SATA 5400RPM"],
     {"Type": "Hard disk (HDD)", "Capacity": "2 TB", "Speed": "5400 RPM", "Interface": "SATA"}),
])
def test_drive_labels(lines, expected):
    specs, complete = labels.decode("hard_drive", lines)
    assert specs == expected
    assert complete


def test_other_categories_are_not_decoded():
    assert labels.decode("laptop", ["DDR4 8GB 2666"]) == ({}, True)
