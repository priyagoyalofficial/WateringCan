import json

import pytest

from agent import storage
from agent.tools import Toolbox, ToolError

TODAY = "2026-09-26"


def run(box, tool, **args):
    return json.loads(box.run(tool, args))


def test_add_log_and_list(data_dir):
    box = Toolbox(TODAY)
    added = run(box, "add_plant", name="Kitchen pothos", species="pothos", where="in", pot="plastic",
                pot_width_in=7, soil="regular", last_watered="2026-09-20")
    pid = added["plant"]["id"]
    assert storage.read()["plants"][0]["size"] == 6  # snapped to a width the page offers

    run(box, "log_care", plant_id=pid, action="still_damp")
    run(box, "log_care", plant_id=pid, action="fertilized")
    listed = run(box, "list_plants")
    assert listed["count"] == 1
    assert "rechecking" in listed["plants"][0]["watering"]
    assert box.changed and box.actions[0] == "Added: Kitchen pothos"


def test_other_species_needs_profile(data_dir):
    box = Toolbox(TODAY)
    with pytest.raises(ToolError):
        run(box, "add_plant", name="Mystery", species="other", where="in", pot="plastic", pot_width_in=6, soil="regular")
    added = run(box, "add_plant", name="String of hearts", species="other", where="in", pot="terracotta",
                pot_width_in=4, soil="cactus", custom_profile={
                    "common_name": "String of hearts", "grown": "in", "days": 10, "dry": "Mostly dry",
                    "light": "Bright indirect", "feed": 30, "style": "dry", "tip": "Water less in winter."})
    assert added["plant"]["type"] == "String of hearts"


def test_rejects_unknown_plant_and_future_dates(data_dir):
    box = Toolbox(TODAY)
    with pytest.raises(ToolError, match="No plant"):
        run(box, "log_care", plant_id="nope", action="watered")
    added = run(box, "add_plant", name="Rose", species="rose", where="out", pot="ground", pot_width_in=20, soil="garden")
    with pytest.raises(ToolError, match="future"):
        run(box, "log_care", plant_id=added["plant"]["id"], action="watered", date="2026-12-01")


def test_stale_write_is_refused(data_dir):
    rev = storage.write([])
    storage.write([])
    with pytest.raises(storage.Conflict):
        storage.write([], expected_rev=rev)


def test_remove_needs_confirmation(data_dir):
    box = Toolbox(TODAY)
    pid = run(box, "add_plant", name="Basil", species="basil", where="out", pot="plastic", pot_width_in=6, soil="regular")["plant"]["id"]
    with pytest.raises(ToolError, match="confirm"):
        run(box, "remove_plant", plant_id=pid, confirmed=False)
    run(box, "remove_plant", plant_id=pid, confirmed=True)
    assert storage.read()["plants"] == [] and box.actions[-1] == "Removed: Basil"
