from carcompass.data.catalog import all_cars, get_car
from carcompass.llm import rule_parse
from carcompass.tools import best_paths, check_passport, rank_matches, search_marketplace, wish_matches

PITCH = "Need 5 Camrys, 2018+, under $12K, clean title, delivered to Rochester by Friday."


def test_rule_parse_pitch_sentence():
    req = rule_parse(PITCH)
    assert (req.make, req.model) == ("Toyota", "Camry")
    assert req.min_year == 2018 and req.max_price == 12000
    assert req.quantity == 5 and req.title == "clean"
    assert req.destination_city == "Rochester" and req.deadline == "Friday"


def test_rule_parse_variants():
    req = rule_parse("Looking for 2 F-150s 2019-2022 under $30,000 any title, Pittsburgh")
    assert req.model == "F-150" and req.quantity == 2
    assert (req.min_year, req.max_year) == (2019, 2022)
    assert req.title == "any" and req.destination_city == "Pittsburgh"


def test_catalog_is_deterministic_and_sized():
    cars = all_cars()
    assert len(cars) == len({c["id"] for c in cars}) > 300
    assert all_cars()[50] == cars[50]


def test_pitch_search_finds_three_clean_and_one_trap():
    req = rule_parse(PITCH)
    candidates = search_marketplace("ACV", req)["candidates"] + search_marketplace("Copart", req)["candidates"]
    passports = {c["id"]: check_passport(c) for c in candidates}
    flagged = [cid for cid, p in passports.items() if p["status"] == "flagged"]
    clean = [c for c in candidates if passports[c["id"]]["status"] == "clean"]
    assert flagged == ["ACV-20733"]
    assert passports["ACV-20733"]["flags"][0]["type"] == "hidden_salvage"
    assert {c["id"] for c in clean} == {"ACV-20418", "ACV-20561", "CPRT-51207"}


def test_odometer_rollback_flag():
    flags = check_passport(get_car("ACV-20990"))["flags"]
    assert [f["type"] for f in flags] == ["odometer_rollback"]


def test_rank_bids_never_exceed_budget():
    req = rule_parse(PITCH)
    ranked = rank_matches([get_car("ACV-20418"), get_car("ACV-20561"), get_car("CPRT-51207")], req)
    assert all(c["price"] <= c["recommended_bid"] <= 12000 for c in ranked)
    assert all(c["transport"]["cost"] > 0 for c in ranked)


def test_best_path_prefers_acv_for_camry_on_truck_lot():
    result = best_paths("Toyota", "Camry", 2019, 61000, 4.0)
    assert result["best"] == "ACV dealer auction"
    assert sum(r["best"] for r in result["rows"]) == 1


def test_wish_matching():
    wish = {"make": "Toyota", "model": "Camry", "min_year": 2017, "max_price": 12500, "title": "clean"}
    assert wish_matches(wish, get_car("ACV-20418"))[0]
    assert not wish_matches(wish, get_car("ACV-20877"))[0]  # over budget
    assert not wish_matches(wish, get_car("CPRT-51388"))[0]  # salvage title
