"""End-to-end stress tests for the MissionCart cart-building pipeline.

These tests intentionally do not import backend code or mock external services.
They exercise the running API at http://localhost:8000.
"""

from __future__ import annotations

import json
import time
from typing import Any, Iterable

import httpx
import pytest


BASE_URL = "http://localhost:8000"
BIRTHDAY_GOAL = "Birthday party for 12 kids tomorrow under 4000"
BIRTHDAY_BUDGET = 4000
REQUEST_TIMEOUT_SECONDS = 20.0


def _dump(payload: Any) -> str:
    try:
        return json.dumps(payload, indent=2, sort_keys=True, default=str)
    except Exception:
        return repr(payload)


def _check(condition: Any, message: str, payload: Any) -> None:
    assert condition, f"{message}\nFull response:\n{_dump(payload)}"


def _response_payload(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"status_code": response.status_code, "text": response.text}


def _post_build(
    client: httpx.Client,
    goal: str,
    budget_max: float | None = None,
    headcount: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"goal": goal}
    if budget_max is not None:
        # The deployed API currently calls this field `budget`; budget_max is
        # included as a compatibility assertion against the documented schema.
        payload["budget"] = budget_max
        payload["budget_max"] = budget_max
    if headcount is not None:
        payload["headcount"] = headcount

    started = time.perf_counter()
    response = client.post("/api/mission/build", json=payload)
    elapsed = time.perf_counter() - started
    return {
        "status_code": response.status_code,
        "elapsed": elapsed,
        "request": payload,
        "json": _response_payload(response),
    }


def _successful_build(
    client: httpx.Client,
    goal: str,
    budget_max: float | None = None,
    headcount: int | None = None,
) -> dict[str, Any]:
    case = _post_build(client, goal, budget_max, headcount)
    _check(case["status_code"] == 200, "Expected build endpoint status 200", case)
    envelope = case["json"]
    _check(isinstance(envelope, dict), "Expected a JSON object response", case)
    _check(envelope.get("success") is True, "Expected success == True", case)
    _check(isinstance(envelope.get("data"), dict), "Expected data to be an object", case)
    return case


def _data(case: dict[str, Any]) -> dict[str, Any]:
    envelope = case.get("json", {})
    value = envelope.get("data", {}) if isinstance(envelope, dict) else {}
    _check(isinstance(value, dict), "Expected response data to be an object", case)
    return value


def _items(case: dict[str, Any]) -> list[dict[str, Any]]:
    value = _data(case).get("cart_items")
    _check(isinstance(value, list), "Expected data.cart_items to be a list", case)
    return value


def _find_item(
    case: dict[str, Any],
    *,
    label_terms: Iterable[str] = (),
    categories: Iterable[str] = (),
) -> dict[str, Any]:
    terms = tuple(term.lower() for term in label_terms)
    allowed_categories = set(categories)
    for item in _items(case):
        label = str(item.get("need_label", "")).lower()
        label_matches = not terms or any(term in label for term in terms)
        category_matches = not allowed_categories or item.get("category") in allowed_categories
        if label_matches and category_matches:
            return item
    _check(False, f"Expected cart item matching labels={terms}, categories={allowed_categories}", case)
    raise AssertionError("unreachable")


def _categories(case: dict[str, Any]) -> set[str]:
    return {str(item.get("category", "")) for item in _items(case)}


def _success_or_clarification(case: dict[str, Any]) -> bool:
    envelope = case.get("json", {})
    if not isinstance(envelope, dict):
        return False
    data = envelope.get("data") or {}
    return envelope.get("success") is True or (
        isinstance(data, dict) and data.get("needs_clarification") is True
    )


@pytest.fixture(scope="session")
def client() -> Iterable[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS) as session:
        yield session


@pytest.fixture(scope="session")
def birthday_build(client: httpx.Client) -> dict[str, Any]:
    # This is the first birthday build made by the suite. Its elapsed time is
    # reused by the first-call performance assertion in Section 12.
    return _successful_build(client, BIRTHDAY_GOAL, BIRTHDAY_BUDGET, headcount=12)


# ---------------------------------------------------------------------------
# Section 1: Core happy path - birthday party
# ---------------------------------------------------------------------------


def test_1_1_kids_birthday_achieves_full_coverage(birthday_build: dict[str, Any]) -> None:
    data = _data(birthday_build)
    coverage = data.get("coverage_score", {})
    _check(coverage.get("fraction") == 1.0, "Expected coverage fraction 1.0", birthday_build)
    _check(coverage.get("covered") == 8, "Expected exactly 8 covered needs", birthday_build)
    _check(len(_items(birthday_build)) == 8, "Expected exactly 8 cart items", birthday_build)
    _check(data.get("total_cost", 4001) <= 4000, "Expected total cost within Rs4000", birthday_build)
    _check(data.get("total_cost", 0) > 0, "Expected positive total cost", birthday_build)


def test_1_2_candles_are_not_decorative_holders(birthday_build: dict[str, Any]) -> None:
    item = _find_item(birthday_build, label_terms=("candle",))
    _check(item.get("price", 201) <= 200, "Expected birthday candles priced at Rs200 or less", birthday_build)
    _check(item.get("category") in {"candles", "cake_knife"}, "Expected a candle/cake-knife category", birthday_build)
    title = str(item.get("title", "")).lower()
    banned = ("holder", "stand", "decor", "décor", "hurricane", "pillar")
    _check(not any(word in title for word in banned), "Expected no decorative candle-holder product", birthday_build)


def test_1_3_napkins_are_cheap_party_napkins(birthday_build: dict[str, Any]) -> None:
    item = _find_item(birthday_build, label_terms=("napkin", "tissue"))
    _check(item.get("price", 251) <= 250, "Expected party napkins priced at Rs250 or less", birthday_build)
    _check(item.get("category") in {"napkins", "tissue_pack"}, "Expected napkins/tissue category", birthday_build)
    title = str(item.get("title", "")).lower()
    _check(not any(word in title for word in ("wedding", "linen", "premium cloth")), "Expected no wedding/linen napkin product", birthday_build)


def test_1_4_balloons_are_actual_balloons(birthday_build: dict[str, Any]) -> None:
    item = _find_item(
        birthday_build,
        label_terms=("balloon",),
        categories=("balloon_set", "balloons", "decorations"),
    )
    _check(item.get("price", 501) <= 500, "Expected balloon set priced at Rs500 or less", birthday_build)
    _check(item.get("category") in {"balloon_set", "balloons"}, "Expected actual balloon category", birthday_build)
    title = str(item.get("title", "")).lower()
    _check(not any(word in title for word in ("topper", "sign", "garland garland")), "Expected no topper/sign product", birthday_build)


def test_1_5_budget_efficiency_leaves_room(birthday_build: dict[str, Any]) -> None:
    total = _data(birthday_build).get("total_cost", 0)
    _check(total >= 500, "Expected meaningful spend of at least Rs500", birthday_build)
    _check(total <= 3500, "Expected total spend no greater than Rs3500", birthday_build)
    _check(4000 - total > 500, "Expected more than Rs500 remaining", birthday_build)


def test_1_6_all_items_meet_tomorrow_delivery(birthday_build: dict[str, Any]) -> None:
    for item in _items(birthday_build):
        deliverable = item.get("amazon_now_eligible") is True or item.get("delivery_eta") in {
            "now_20min", "today", "tomorrow"
        }
        _check(deliverable, f"Expected on-time delivery for {item.get('title')}", birthday_build)


def test_1_7_plate_quantity_covers_12_kids(birthday_build: dict[str, Any]) -> None:
    item = _find_item(birthday_build, label_terms=("plate", "utensil"), categories=("plates", "disposable_plates"))
    quantity = item.get("packs_quantity", 0)
    price = item.get("price", 0)
    _check(quantity >= 1, "Expected at least one plate pack", birthday_build)
    _check(item.get("total_cost") == price * quantity, "Expected plate total_cost == price * packs_quantity", birthday_build)
    _check(quantity * item.get("pack_size", 0) >= 12, "Expected enough plates for 12 kids", birthday_build)


def test_1_8_all_items_have_required_fields(birthday_build: dict[str, Any]) -> None:
    for item in _items(birthday_build):
        for field in ("cart_item_id", "asin", "title", "need_label"):
            _check(isinstance(item.get(field), str) and bool(item[field].strip()), f"Expected non-empty string field {field}", birthday_build)
        for field in ("price", "total_cost"):
            value = item.get(field)
            _check(isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0, f"Expected positive numeric field {field}", birthday_build)
        _check(isinstance(item.get("packs_quantity"), int) and item["packs_quantity"] >= 1, "Expected packs_quantity >= 1", birthday_build)
        score = item.get("community_adoption_score")
        _check(isinstance(score, (int, float)) and 0 < score <= 1.0, "Expected community_adoption_score in (0, 1]", birthday_build)
        _check(isinstance(item.get("sessions_analyzed"), int) and item["sessions_analyzed"] > 0, "Expected sessions_analyzed > 0", birthday_build)
        checks = item.get("constraint_checks_passed")
        _check(isinstance(checks, list) and bool(checks), "Expected non-empty constraint_checks_passed", birthday_build)


# ---------------------------------------------------------------------------
# Section 2: Budget edge cases
# ---------------------------------------------------------------------------


def test_2_1_tight_budget_selects_must_haves_only(client: httpx.Client) -> None:
    case = _successful_build(client, "Birthday party for 6 kids today under 800", 800, headcount=6)
    data = _data(case)
    for item in _items(case):
        _check(item.get("price", 481) <= 480, "Expected every item price <= 60% of budget", case)
        _check(item.get("price", 401) <= 400, "Expected no item over Rs400", case)
    _check(data.get("total_cost", 801) <= 800, "Expected tight cart within Rs800", case)
    categories = _categories(case)
    for aliases in ({"plates", "disposable_plates"}, {"cups", "disposable_cups"}, {"candles", "cake_knife"}):
        _check(bool(categories & aliases), f"Expected must-have category from {aliases}", case)


def test_2_2_very_tight_budget_returns_partial_cart(client: httpx.Client) -> None:
    case = _successful_build(client, "Birthday party for 5 kids under 300", 300, headcount=5)
    _check(len(_items(case)) >= 1, "Expected at least one partial-cart item", case)
    _check(_data(case).get("total_cost", 301) <= 300, "Expected partial cart within Rs300", case)


def test_2_3_large_budget_allows_large_party(client: httpx.Client) -> None:
    case = _successful_build(client, "Birthday party for 20 kids this weekend under 15000", 15000, headcount=20)
    data = _data(case)
    _check(data.get("coverage_score", {}).get("covered", 0) >= 6, "Expected at least 6 covered needs", case)
    _check(data.get("total_cost", 15001) <= 15000, "Expected cart within Rs15000", case)
    _check(any(item.get("packs_quantity", 0) >= 2 for item in _items(case)), "Expected at least one multi-pack item", case)


def test_2_4_budget_1000_fits_four_must_haves(client: httpx.Client) -> None:
    case = _successful_build(client, "Birthday party for 8 kids tomorrow under 1000", 1000, headcount=8)
    _check(_data(case).get("total_cost", 1001) <= 1000, "Expected cart within Rs1000", case)
    _check(len(_items(case)) >= 4, "Expected at least four must-have items", case)


# ---------------------------------------------------------------------------
# Section 3: Headcount scaling
# ---------------------------------------------------------------------------


def test_3_1_small_party_plate_quantity(client: httpx.Client) -> None:
    case = _successful_build(client, "Birthday party for 4 kids tomorrow under 2000", 2000, headcount=4)
    item = _find_item(case, label_terms=("plate", "utensil"), categories=("plates", "disposable_plates"))
    units = item.get("packs_quantity", 0) * item.get("pack_size", 0)
    _check(units >= 4, "Expected at least four plates", case)
    _check(units < 30, "Expected fewer than 30 plates for four people", case)


def test_3_2_large_party_plate_quantity(client: httpx.Client) -> None:
    case = _successful_build(client, "Birthday party for 50 people this weekend under 10000", 10000, headcount=50)
    item = _find_item(case, label_terms=("plate", "utensil"), categories=("plates", "disposable_plates"))
    _check(item.get("packs_quantity", 0) * item.get("pack_size", 0) >= 50, "Expected at least 50 plates", case)
    _check(_data(case).get("total_cost", 10001) <= 10000, "Expected cart within Rs10000", case)


def test_3_3_office_party_uses_multiple_packs(client: httpx.Client) -> None:
    case = _successful_build(client, "Office team party for 30 people tomorrow under 5000", 5000, headcount=30)
    _check(_data(case).get("total_cost", 5001) <= 5000, "Expected office-party cart within Rs5000", case)
    _check(any(item.get("packs_quantity", 0) >= 2 for item in _items(case)), "Expected a multi-pack consumable", case)


# ---------------------------------------------------------------------------
# Section 4: Different occasion types
# ---------------------------------------------------------------------------


def test_4_1_home_setup(client: httpx.Client) -> None:
    case = _post_build(client, "New flat setup for 2 people this weekend under 15000", 15000, headcount=2)
    _check(case["status_code"] == 200, "Expected home setup status 200", case)
    _check(_success_or_clarification(case), "Expected success or needs_clarification", case)
    if case["json"].get("success") is True:
        _check(len(_items(case)) >= 3, "Expected at least three home items", case)
        home = {"mattress", "bedsheet", "pillow", "led_bulb", "extension_board", "towels"}
        _check(bool(_categories(case) & home), "Expected at least one home-setup category", case)


def test_4_2_travel_occasion(client: httpx.Client) -> None:
    case = _post_build(client, "Trek to Coorg for 4 people this weekend under 5000", 5000, headcount=4)
    _check(case["status_code"] == 200, "Expected travel build status 200", case)
    _check(_success_or_clarification(case), "Expected success or needs_clarification", case)
    if case["json"].get("success") is True:
        _check(len(_items(case)) >= 2, "Expected at least two travel items", case)
        travel = {"backpack", "water_bottle", "first_aid_kit", "power_bank", "torch"}
        _check(bool(_categories(case) & travel), "Expected at least one travel category", case)


def test_4_3_grocery_essentials(client: httpx.Client) -> None:
    case = _successful_build(client, "Weekly groceries for 2 people under 2000", 2000, headcount=2)
    _check(len(_items(case)) >= 3, "Expected at least three grocery items", case)
    grocery = {"atta", "rice", "dal", "cooking_oil", "detergent", "soap"}
    _check(bool(_categories(case) & grocery), "Expected grocery categories", case)


def test_4_4_diwali_celebration(client: httpx.Client) -> None:
    case = _successful_build(client, "Diwali decoration for home under 3000", 3000)
    data = _data(case)
    _check(len(_items(case)) >= 2, "Expected at least two Diwali items", case)
    domain = data.get("domain")
    _check(isinstance(domain, str) and bool(domain.strip()), "Expected a valid parsed domain", case)


# ---------------------------------------------------------------------------
# Section 5: Product quality gate
# ---------------------------------------------------------------------------


def test_5_1_no_low_rated_products(birthday_build: dict[str, Any]) -> None:
    for item in _items(birthday_build):
        _check(item.get("rating", 0) >= 3.5, f"Expected rating >= 3.5 for {item.get('title')}", birthday_build)


def test_5_2_no_high_return_risk_products(birthday_build: dict[str, Any]) -> None:
    for item in _items(birthday_build):
        _check("return_risk" in item, f"Expected return_risk field for {item.get('title')}", birthday_build)
        _check(item.get("return_risk", 1) <= 0.30, f"Expected return_risk <= 0.30 for {item.get('title')}", birthday_build)


def test_5_3_no_out_of_stock_products(birthday_build: dict[str, Any]) -> None:
    for item in _items(birthday_build):
        _check("stock_available" in item, f"Expected stock_available field for {item.get('title')}", birthday_build)
        _check(item.get("stock_available") is True, f"Expected in-stock product {item.get('title')}", birthday_build)


def test_5_4_no_single_item_over_half_budget(birthday_build: dict[str, Any]) -> None:
    for item in _items(birthday_build):
        _check(item.get("price", 2001) <= 2000, f"Expected item price <= Rs2000 for {item.get('title')}", birthday_build)


@pytest.mark.parametrize("budget", [2000, 3000, 4000, 5000, 8000])
def test_5_5_total_never_exceeds_budget(client: httpx.Client, budget: int) -> None:
    case = _successful_build(client, f"Birthday party for 10 kids tomorrow under {budget}", budget, headcount=10)
    _check(_data(case).get("total_cost", budget + 1) <= budget, f"Expected total within Rs{budget}", case)


# ---------------------------------------------------------------------------
# Section 6: Response schema validation
# ---------------------------------------------------------------------------


def test_6_1_top_level_data_shape(client: httpx.Client) -> None:
    case = _successful_build(client, "Birthday party for 8 kids under 3000", 3000, headcount=8)
    data = _data(case)
    required = {"cart_items", "total_cost", "coverage_score", "domain", "occasion", "headcount", "budget_max", "simulated_data"}
    _check(required <= set(data), f"Expected data keys {sorted(required)}", case)
    _check(isinstance(data.get("cart_items"), list), "Expected cart_items list", case)
    _check(isinstance(data.get("total_cost"), (int, float)), "Expected numeric total_cost", case)
    coverage = data.get("coverage_score", {})
    coverage_keys = {"fraction", "covered", "total", "display", "all_must_haves_covered", "missing"}
    _check(isinstance(coverage, dict) and coverage_keys <= set(coverage), "Expected complete coverage_score object", case)
    _check(isinstance(data.get("domain"), str), "Expected domain string", case)
    _check(isinstance(data.get("occasion"), str), "Expected occasion string", case)
    _check(isinstance(data.get("headcount"), int), "Expected headcount integer", case)
    _check(isinstance(data.get("budget_max"), (int, float)), "Expected numeric budget_max", case)
    _check(data.get("simulated_data") is True, "Expected simulated_data == True", case)


def test_6_2_coverage_score_is_consistent(client: httpx.Client) -> None:
    case = _successful_build(client, "Birthday party for 8 kids under 3000", 3000, headcount=8)
    coverage = _data(case).get("coverage_score", {})
    covered = coverage.get("covered")
    total = coverage.get("total")
    _check(covered == len(_items(case)), "Expected covered count to match cart item count", case)
    _check(isinstance(total, int) and total > 0, "Expected positive coverage total", case)
    _check(coverage.get("fraction") == pytest.approx(covered / total), "Expected fraction == covered / total", case)
    _check(0.0 <= coverage.get("fraction", -1) <= 1.0, "Expected coverage fraction in [0, 1]", case)
    _check(coverage.get("display") == f"{covered}/{total}", "Expected consistent coverage display", case)


def test_6_3_simulated_data_is_always_true(client: httpx.Client) -> None:
    case = _successful_build(client, "Birthday party for 8 kids under 3000", 3000, headcount=8)
    _check(_data(case).get("simulated_data") is True, "Expected sacred simulated_data flag == True", case)


def test_6_4_cart_items_include_community_evidence(client: httpx.Client) -> None:
    case = _successful_build(client, "Birthday party for 8 kids under 3000", 3000, headcount=8)
    for item in _items(case):
        score = item.get("community_adoption_score")
        _check(isinstance(score, (int, float)) and 0.5 <= score <= 1.0, "Expected community score in [0.5, 1]", case)
        _check(item.get("sessions_analyzed", 0) >= 1000, "Expected at least 1000 analyzed sessions", case)
        _check(isinstance(item.get("quantity_basis"), str) and bool(item["quantity_basis"].strip()), "Expected quantity_basis", case)
        _check(isinstance(item.get("evidence_source"), str) and bool(item["evidence_source"].strip()), "Expected evidence_source", case)


# ---------------------------------------------------------------------------
# Section 7: Occasion taxonomy routing
# ---------------------------------------------------------------------------


def test_7_1_kids_birthday_routes_balloon_needs(birthday_build: dict[str, Any]) -> None:
    _check(any("balloon" in str(item.get("need_label", "")).lower() for item in _items(birthday_build)), "Expected a balloon need label", birthday_build)
    _check(any(item.get("category") == "balloon_set" for item in _items(birthday_build)), "Expected primary balloon_set category", birthday_build)


def test_7_2_need_labels_cover_expected_categories(birthday_build: dict[str, Any]) -> None:
    labels = [str(item.get("need_label", "")).lower() for item in _items(birthday_build)]
    for alternatives in (("plate", "utensil"), ("cup", "drink"), ("candle",), ("balloon", "decoration"), ("napkin", "tissue")):
        _check(any(any(term in label for term in alternatives) for label in labels), f"Expected need label matching {alternatives}", birthday_build)


def test_7_3_generic_party_uses_event_adapter(client: httpx.Client) -> None:
    case = _successful_build(client, "House party for 15 adults next week under 5000", 5000, headcount=15)
    _check(len(_items(case)) >= 4, "Expected at least four party items", case)
    _check(_data(case).get("domain") == "event", "Expected event domain", case)


# ---------------------------------------------------------------------------
# Section 8: Retrieval engine behavior
# ---------------------------------------------------------------------------


def test_8_1_out_of_index_demo_products_appear(birthday_build: dict[str, Any]) -> None:
    expected = {"B0PARTY021", "B0PARTY022", "B0PARTY013", "B0PARTY014", "B0PARTY009", "B0PARTY010"}
    actual = {str(item.get("asin")) for item in _items(birthday_build)}
    _check(len(expected & actual) >= 2, "Expected at least two post-index demo ASINs", birthday_build)


def test_8_2_price_fit_prefers_cheap_candles(birthday_build: dict[str, Any]) -> None:
    item = _find_item(birthday_build, label_terms=("candle",))
    _check(item.get("price", 201) <= 200, "Expected cheap candles to win price-fit scoring", birthday_build)


def test_8_3_categories_are_exclusive(birthday_build: dict[str, Any]) -> None:
    categories = [item.get("category") for item in _items(birthday_build)]
    _check(len(categories) == len(set(categories)), "Expected no duplicate cart categories", birthday_build)


# ---------------------------------------------------------------------------
# Section 9: Concurrent and repeat builds
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_9_1_repeated_goal_has_consistent_coverage(client: httpx.Client) -> None:
    first = _successful_build(client, BIRTHDAY_GOAL, BIRTHDAY_BUDGET, headcount=12)
    second = _successful_build(client, BIRTHDAY_GOAL, BIRTHDAY_BUDGET, headcount=12)
    core_aliases = (
        {"plates", "disposable_plates"},
        {"cups", "disposable_cups"},
        {"candles", "cake_knife"},
        {"balloon_set", "balloons"},
        {"napkins", "tissue_pack"},
    )
    for case in (first, second):
        _check(_data(case).get("coverage_score", {}).get("covered", 0) >= 6, "Expected at least six covered needs", case)
        categories = _categories(case)
        for aliases in core_aliases:
            _check(bool(categories & aliases), f"Expected stable core category from {aliases}", case)
    difference = abs(_data(first).get("total_cost", 0) - _data(second).get("total_cost", 0))
    _check(difference < 500, "Expected repeated-build cost difference under Rs500", {"first": first, "second": second})


@pytest.mark.slow
def test_9_2_five_rapid_builds_do_not_degrade(client: httpx.Client) -> None:
    cases = [_successful_build(client, BIRTHDAY_GOAL, BIRTHDAY_BUDGET, headcount=12) for _ in range(5)]
    for index, case in enumerate(cases, start=1):
        _check(_data(case).get("coverage_score", {}).get("covered", 0) >= 6, f"Expected build {index} coverage >= 6", case)
        _check(case["elapsed"] <= 10, f"Expected build {index} within 10 seconds", case)


@pytest.mark.slow
def test_9_3_different_goals_do_not_interfere(client: httpx.Client) -> None:
    birthday_12 = _successful_build(client, BIRTHDAY_GOAL, 4000, headcount=12)
    trek = _successful_build(client, "Trek to Coorg for 4 people under 3000", 3000, headcount=4)
    birthday_8 = _successful_build(client, "Birthday party for 8 kids under 2500", 2500, headcount=8)
    _check(_data(birthday_12).get("domain") == "event", "Expected first birthday event domain", birthday_12)
    _check(_data(trek).get("domain") in {"travel", "travel_prep"}, "Expected trek travel domain", trek)
    _check(_data(birthday_8).get("domain") == "event", "Expected second birthday event domain", birthday_8)
    trekking = {"backpack", "water_bottle", "first_aid_kit", "power_bank", "torch", "trekking_socks", "rain_jacket"}
    for case in (birthday_12, birthday_8):
        _check(not (_categories(case) & trekking), "Expected no trekking gear in birthday cart", case)


# ---------------------------------------------------------------------------
# Section 10: Error handling and boundary cases
# ---------------------------------------------------------------------------


def test_10_1_unachievable_goal_is_graceful(client: httpx.Client) -> None:
    case = _post_build(client, "Buy a Ferrari under 100", 100)
    _check(case["status_code"] != 500, "Expected no server error", case)
    _check(case["elapsed"] < 10, "Expected graceful response within 10 seconds", case)
    envelope = case["json"] if isinstance(case["json"], dict) else {}
    data = envelope.get("data") or {}
    valid = envelope.get("success") is True or (
        envelope.get("success") is False
        and isinstance(data, dict)
        and (data.get("needs_clarification") is True or data.get("unsupported") is True)
    )
    _check(valid, "Expected partial success, clarification, or unsupported response", case)


def test_10_2_empty_goal_does_not_crash(client: httpx.Client) -> None:
    case = _post_build(client, "", 1000)
    _check(case["status_code"] in {200, 422}, "Expected status 200 or 422 for empty goal", case)


def test_10_3_missing_budget_uses_default(client: httpx.Client) -> None:
    case = _post_build(client, "Birthday party for 10 kids tomorrow")
    _check(case["status_code"] != 500, "Expected no server error without budget", case)
    _check(_success_or_clarification(case), "Expected success or clarification without budget", case)
    if case["json"].get("success") is True:
        _check(bool(_items(case)), "Expected cart items when missing-budget build succeeds", case)


def test_10_4_very_large_headcount_does_not_crash(client: httpx.Client) -> None:
    case = _post_build(client, "Birthday party for 500 kids tomorrow under 50000", 50000, headcount=500)
    _check(case["status_code"] != 500, "Expected no server error for 500-person party", case)
    _check(_success_or_clarification(case), "Expected success or clarification for large headcount", case)
    if case["json"].get("success") is True:
        _check(_data(case).get("total_cost", 50001) <= 50000, "Expected large cart within Rs50000", case)


def test_10_5_zero_budget_is_graceful(client: httpx.Client) -> None:
    case = _post_build(client, "Birthday party for 5 kids tomorrow", 0, headcount=5)
    _check(case["status_code"] != 500, "Expected no server error for zero budget", case)


# ---------------------------------------------------------------------------
# Section 11: Specific product category checks (one shared response)
# ---------------------------------------------------------------------------


def test_11_1_plate_item_sanity(birthday_build: dict[str, Any]) -> None:
    item = _find_item(birthday_build, label_terms=("plate", "utensil"), categories=("plates", "disposable_plates"))
    _check(item.get("category") in {"plates", "disposable_plates"}, "Expected plates category", birthday_build)
    _check(40 <= item.get("price", 0) <= 500, "Expected plate price from Rs40 to Rs500", birthday_build)
    _check(item.get("pack_size", 0) >= 10, "Expected plate pack size >= 10", birthday_build)


def test_11_2_cups_item_sanity(birthday_build: dict[str, Any]) -> None:
    item = _find_item(birthday_build, label_terms=("cup", "drink"), categories=("cups", "disposable_cups"))
    _check(item.get("category") in {"cups", "disposable_cups"}, "Expected cups category", birthday_build)
    _check(40 <= item.get("price", 0) <= 400, "Expected cup price from Rs40 to Rs400", birthday_build)
    _check(item.get("pack_size", 0) >= 10, "Expected cup pack size >= 10", birthday_build)


def test_11_3_candles_item_sanity(birthday_build: dict[str, Any]) -> None:
    item = _find_item(birthday_build, label_terms=("candle",))
    _check(item.get("category") in {"candles", "cake_knife"}, "Expected candles/cake-knife category", birthday_build)
    _check(30 <= item.get("price", 0) <= 200, "Expected candle price from Rs30 to Rs200", birthday_build)
    _check(item.get("pack_size", 0) >= 1, "Expected candle pack size >= 1", birthday_build)


def test_11_4_balloon_item_sanity(birthday_build: dict[str, Any]) -> None:
    item = _find_item(birthday_build, label_terms=("balloon",), categories=("balloon_set", "balloons"))
    _check(item.get("category") in {"balloon_set", "balloons"}, "Expected actual balloon category", birthday_build)
    _check(100 <= item.get("price", 0) <= 600, "Expected balloon price from Rs100 to Rs600", birthday_build)
    _check(item.get("pack_size", 0) >= 20, "Expected balloon pack size >= 20", birthday_build)


def test_11_5_napkin_item_sanity(birthday_build: dict[str, Any]) -> None:
    item = _find_item(birthday_build, label_terms=("napkin", "tissue"))
    _check(item.get("category") in {"napkins", "tissue_pack"}, "Expected napkin/tissue category", birthday_build)
    _check(30 <= item.get("price", 0) <= 300, "Expected napkin price from Rs30 to Rs300", birthday_build)


# ---------------------------------------------------------------------------
# Section 12: Performance benchmarks
# ---------------------------------------------------------------------------


def test_12_1_first_birthday_response_under_15_seconds(birthday_build: dict[str, Any]) -> None:
    _check(birthday_build["elapsed"] < 15, "Expected first birthday response within 15 seconds", birthday_build)


def test_12_2_health_endpoint_always_200(client: httpx.Client) -> None:
    response = client.get("/health")
    payload = {"status_code": response.status_code, "json": _response_payload(response)}
    _check(response.status_code == 200, "Expected sacred health endpoint status 200", payload)


def test_12_3_coverage_survives_large_catalog(birthday_build: dict[str, Any]) -> None:
    covered = _data(birthday_build).get("coverage_score", {}).get("covered", 0)
    _check(covered >= 7, "Expected at least 7/8 coverage with the full catalog", birthday_build)
