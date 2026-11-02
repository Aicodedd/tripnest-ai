"""Browser end-to-end tests (real Chrome) for the two core features.

Run from the repo root:  sh e2e/run.sh
Journeys: (1) location + date -> recommendations, (2) destination -> crowd prediction, (3) compare destinations,
(4) manual location when browser location is unavailable, (5) different screen sizes.
"""
import os
import re

import pytest
from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("E2E_BASE", "http://localhost:8020")
DATE = "2026-12-26"  # a Saturday in the beach season


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        yield b
        b.close()


def new_page(browser, **ctx):
    c = browser.new_context(viewport=ctx.pop("viewport", {"width": 1366, "height": 900}), **ctx)
    pg = c.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(f"{e} | {(e.stack or '').splitlines()[1:3]}"))
    pg.on("response", lambda r: pg.errors.append(f"HTTP {r.status} {r.url}") if r.status >= 400 and "/api/" in r.url else None)
    pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
    pg._ctx = c
    return pg


@pytest.fixture()
def page(browser):
    pg = new_page(browser)
    yield pg
    assert not pg.errors, f"browser errors: {pg.errors}"
    pg._ctx.close()


def search(page, city="Chennai", date=DATE, interest="beach"):
    page.goto(BASE + "/")
    page.get_by_label("Starting location").fill(city)
    page.locator("#date").fill(date)
    if interest:
        page.get_by_label("Interest (optional)").select_option(interest)
    page.get_by_role("button", name="Find Destinations").click()


# ---------------------------------------------------------------- 1
def test_journey1_location_and_date_give_recommendations(page):
    search(page)
    expect(page).to_have_url(re.compile(r"#/results\?.*date=2026-12-26"))
    expect(page.get_by_role("heading", name="Destinations for Sat, 26 Dec")).to_be_visible()
    cards = page.locator(".rcard")
    expect(cards.first).to_be_visible()
    assert cards.count() >= 3
    first = cards.first
    expect(first.locator("h2")).to_have_text("Mahabalipuram")          # nearest good beach on a busy Saturday
    expect(first.locator(".pill").first).to_have_text(re.compile("Low|Moderate|High|At Capacity"))
    expect(first).to_contain_text("Best time")
    expect(first).to_contain_text("km (straight-line distance)")
    expect(first.locator(".why li").first).to_contain_text("Predicted")
    expect(first.get_by_role("link", name="View details")).to_be_visible()
    first.get_by_text("Why this score").click()
    expect(first.locator(".wrow")).to_have_count(4)
    expect(page.locator("#why")).to_contain_text("Popularity is not used")
    expect(page.get_by_text("Demonstration data").first).to_be_visible()
    expect(page.locator("canvas.leaflet-heatmap-layer")).to_have_count(1)
    expect(page.get_by_text("Sign in")).to_have_count(0)               # no accounts needed


def test_recommendations_react_to_interest_and_date(page):
    search(page, interest="wildlife")
    expect(page.locator(".rcard").first).to_be_visible()
    wild = page.locator(".rcard h2").all_inner_texts()
    search(page, interest="beach")
    expect(page.locator(".rcard h2").first).to_have_text("Mahabalipuram")   # the list has changed
    beach = page.locator(".rcard h2").all_inner_texts()
    assert wild and beach and wild[0] != beach[0]
    page.locator("#refine input[name=date]").fill("2026-12-22")
    page.get_by_role("button", name="Update").click()
    expect(page.get_by_role("heading", name="Destinations for Tue, 22 Dec")).to_be_visible()


# ---------------------------------------------------------------- 2
def test_journey2_destination_shows_its_crowd_prediction(page):
    search(page)
    page.locator(".rcard").first.get_by_role("link", name="View details").click()
    expect(page.get_by_role("heading", name="Mahabalipuram", level=1)).to_be_visible()
    expect(page.locator(".bigread")).to_contain_text(re.compile("(Low|Moderate|High|At Capacity) crowds"))
    expect(page.locator("#pred-h")).to_be_visible()
    expect(page.locator("svg.chart").first).to_be_visible()
    expect(page.locator("#best-h")).to_be_visible()
    expect(page.locator(".week .day")).to_have_count(7)
    expect(page.locator("#info-h")).to_be_visible()
    for t in ("ML prediction", "Demonstration data", "Not live"):
        expect(page.get_by_text(t, exact=True).first).to_be_visible()
    page.get_by_text("Limitations").click()
    expect(page.locator("#lim-h").locator("xpath=..")).to_contain_text("No live crowd counts")
    expect(page.get_by_role("link", name="Back to results")).to_be_visible()


def test_prediction_changes_with_time_range_and_day(page):
    page.goto(f"{BASE}/#/d/goa?date={DATE}&from=9&to=17")
    expect(page.locator(".bigread")).to_contain_text("At Capacity")
    page.locator("#when select[name=from]").select_option("5")
    page.locator("#when select[name=to]").select_option("8")
    page.get_by_role("button", name="Update").click()
    expect(page).to_have_url(re.compile("from=5&to=8"))
    expect(page.locator(".bigread")).not_to_contain_text("At Capacity")
    page.locator(".week .day").nth(2).click()                           # a quieter weekday
    expect(page).to_have_url(re.compile("date=2026-12-28"))


def test_invalid_time_range_is_explained(page):
    page.goto(f"{BASE}/#/d/goa?date={DATE}")
    page.locator("#when select[name=from]").select_option("18")
    page.locator("#when select[name=to]").select_option("9")
    page.get_by_role("button", name="Update").click()
    expect(page.locator("#when-err")).to_have_text("The start time must not be after the end time.")


def test_check_one_destination_from_the_homepage(page):
    page.goto(BASE + "/")
    page.locator("#date").fill(DATE)
    page.get_by_label("Destination", exact=True).fill("Jaipur")
    page.get_by_role("button", name="Check crowd prediction").click()
    expect(page.get_by_role("heading", name="Jaipur", level=1)).to_be_visible()
    expect(page).to_have_url(re.compile(f"date={DATE}"))
    page.goto(BASE + "/")
    page.get_by_label("Destination", exact=True).fill("Nowhereville")
    page.get_by_role("button", name="Check crowd prediction").click()
    expect(page.locator("#check-err")).to_have_text("Choose a destination from the list.")


def test_unknown_destination_page_is_a_clear_empty_state(page):
    page.goto(f"{BASE}/#/d/atlantis?date={DATE}")
    expect(page.get_by_text("Destination not found")).to_be_visible()
    page.errors[:] = [e for e in page.errors if " 404 " not in e]       # the 404 is the behaviour under test


# ---------------------------------------------------------------- 3
def test_journey3_compare_several_destinations(page):
    search(page, interest="")
    boxes = page.locator("input[data-cmp]")
    boxes.nth(0).check()
    expect(page.get_by_text("Tick Compare on one more destination")).to_be_visible()
    boxes.nth(1).check()
    boxes.nth(2).check()
    expect(page.get_by_role("heading", name="Compare 3 destinations")).to_be_visible()
    expect(page.locator("#cmp-body svg.chart")).to_be_visible()
    expect(page.locator("#cmp-body tbody tr")).to_have_count(3)
    expect(page.locator("#cmp-body")).to_contain_text(re.compile("Low|Moderate|High|At Capacity"))
    boxes.nth(3).check()
    boxes.nth(4).click()                                                # a fifth is refused
    expect(page.locator("#toast")).to_have_text("You can compare up to 4 destinations.")
    expect(boxes.nth(4)).not_to_be_checked()


# ---------------------------------------------------------------- 4
def test_journey4_manual_location_when_browser_location_is_denied(browser):
    pg = new_page(browser)                                               # no geolocation permission granted
    pg.goto(BASE + "/")
    pg.get_by_role("button", name="use my current location").click()
    expect(pg.locator("#loc-note")).to_contain_text("type your starting city instead")
    expect(pg.locator("#from")).to_be_focused()
    pg.locator("#from").fill("Bangalore")                                # an alias is understood
    pg.locator("#date").fill(DATE)
    pg.get_by_role("button", name="Find Destinations").click()
    expect(pg).to_have_url(re.compile("from=Bengaluru"))
    expect(pg.locator(".rcard").first).to_be_visible()
    pg.errors[:] = [e for e in pg.errors if "Geolocation" not in e]
    assert not pg.errors, pg.errors
    pg._ctx.close()


def test_unknown_or_empty_location_is_explained(page):
    page.goto(BASE + "/")
    page.get_by_role("button", name="Find Destinations").click()
    expect(page.locator("#form-err")).to_have_text("Enter your starting city, or use your current location.")
    page.get_by_label("Starting location").fill("Atlantis")
    page.get_by_role("button", name="Find Destinations").click()
    expect(page.locator("#form-err")).to_contain_text("nearby major city")
    page.errors[:] = [e for e in page.errors if " 404 " not in e]


def test_current_location_is_used_only_after_the_visitor_asks(browser):
    pg = new_page(browser, geolocation={"latitude": 13.0827, "longitude": 80.2707}, permissions=["geolocation"])
    asked = []
    pg.add_init_script("const o = navigator.geolocation.getCurrentPosition.bind(navigator.geolocation);"
                       "navigator.geolocation.getCurrentPosition = (...a) => { window.__geoAsked = true; return o(...a); };")
    pg.goto(BASE + "/")
    assert pg.evaluate("!!window.__geoAsked") is False                   # never asked on page load
    pg.get_by_role("button", name="use my current location").click()
    expect(pg.locator("#from")).to_have_value("My current location")
    pg.locator("#date").fill(DATE)
    pg.get_by_role("button", name="Find Destinations").click()
    expect(pg).to_have_url(re.compile(r"lat=13\.08&lon=80\.27&from=Your\+location"))
    expect(pg.locator(".rcard").first).to_be_visible()
    assert not asked and not pg.errors, pg.errors
    pg._ctx.close()


def test_search_works_without_any_start_location_api(page):
    page.goto(f"{BASE}/#/results?date={DATE}")                           # distance is simply not used
    expect(page.locator(".rcard").first).to_be_visible()
    expect(page.locator("#r-sub")).to_contain_text("distance is not used")


# ---------------------------------------------------------------- 5
@pytest.mark.parametrize("name,size", [("desktop", (1440, 900)), ("laptop", (1280, 720)), ("tablet", (768, 1024)), ("phone", (390, 844))])
def test_journey5_usable_on_every_screen_size(browser, name, size):
    pg = new_page(browser, viewport={"width": size[0], "height": size[1]}, is_mobile=size[0] < 500)
    pg.goto(BASE + "/")
    expect(pg.get_by_role("button", name="Find Destinations")).to_be_visible()
    pg.get_by_label("Starting location").fill("Mumbai")
    pg.locator("#date").fill(DATE)
    pg.get_by_role("button", name="Find Destinations").click()
    expect(pg.locator(".rcard").first).to_be_visible()
    pg.locator(".rcard").first.get_by_role("link", name="View details").click()
    expect(pg.locator(".bigread")).to_be_visible()
    for path in ["/", f"/#/results?lat=19.076&lon=72.8777&from=Mumbai&date={DATE}", f"/#/d/goa?date={DATE}"]:
        pg.goto(BASE + path)
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(500)
        assert pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1, f"{name} {path} scrolls sideways"
        assert pg.locator("#d-map").count() == 1 and pg.locator("#d-map").is_visible()
    assert not pg.errors, pg.errors
    pg._ctx.close()


def test_leaving_a_page_mid_load_causes_no_script_errors(page):
    for path in ["/", f"/#/results?date={DATE}", f"/#/d/goa?date={DATE}"]:
        page.goto(BASE + path)
        page.goto(BASE + "/#/d/jaipur?date=" + DATE)
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="Jaipur", level=1)).to_be_visible()


def test_credentials_or_inputs_never_appear_in_the_url(page):
    page.goto(BASE + "/")
    page.get_by_label("Starting location").fill("Pune")
    page.get_by_label("Starting location").press("Enter")
    page.wait_for_timeout(800)
    assert "?from" not in page.url.split("#")[0] and "Pune" not in page.url.split("#")[0]
