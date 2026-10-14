from agent import care

TODAY = "2026-09-26"


def plant(**kw):
    base = {"id": "p1", "name": "Pothos", "species": "pothos", "where": "in", "pot": "plastic", "size": 6,
            "soil": "regular", "learned": 1, "log": []}
    return {**base, **kw}


def test_water_amounts():
    assert care.amount(plant())["short"] == "About 1¾ cups (420 ml)"
    assert care.amount(plant(species="snake", size=4, soil="cactus"))["short"] == "About ½ cup (110 ml)"
    assert care.amount(plant(species="citrus", where="out", size=14, pot="terracotta"))["short"] == "About 6 quarts (5.8 L)"
    assert care.amount(plant(species="orchid"))["short"].startswith("Soak")


def test_new_plant_is_due_today():
    ws = care.water_status(plant(), TODAY)
    assert ws["kind"] == "new" and ws["due"] == TODAY


def test_still_damp_snoozes_and_lengthens():
    p = plant(lastWatered="2026-09-17")
    assert care.water_status(p, TODAY)["kind"] == "late"
    p2 = care.log_still_damp(p, TODAY)
    ws = care.water_status(p2, TODAY)
    assert ws["kind"] == "snooze" and ws["d"] >= 1
    assert p2["learned"] > 1


def test_bone_dry_shortens_schedule():
    p = care.log_watering(plant(lastWatered="2026-09-20"), TODAY, bone_dry=True)
    assert p["learned"] < 1 and p["lastWatered"] == TODAY
    assert p["log"][0] == {"t": "water", "d": TODAY, "note": "bone dry"}


def test_past_watering_does_not_learn():
    p = care.log_watering(plant(lastWatered="2026-09-10"), TODAY, when="2026-09-20")
    assert p["lastWatered"] == "2026-09-20" and p["learned"] == 1


def test_fertilizer_pauses_in_winter():
    assert care.feed_status(plant(), "2026-01-15")["kind"] == "rest"
    assert care.feed_status(plant(), "2026-05-15")["kind"] == "due"
