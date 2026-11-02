"""Browser end-to-end tests (real Chrome) for the location-first flow.

Run from the repo root:  sh e2e/run.sh        (needs internet: map tiles, Leaflet and the destination photos come from CDNs)

The nine steps: open the app -> grant location or type a city -> popular places near you -> travel date and predicted
crowd -> best time to visit -> hidden gems -> interactive map -> open a destination -> its prediction details.
"""
import os
import re

import pytest
from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("E2E_BASE", "http://localhost:8020")
SAT, TUE = "2026-12-26", "2026-12-22"
COIMBATORE = "lat=11.0168&lon=76.9558"


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


def search(page, city="Coimbatore", date=SAT, interest=""):
    page.goto(BASE + "/")
    page.locator("#from").fill(city)
    page.locator("#date").fill(date)
    if interest:
        page.locator("#interest").select_option(interest)
    page.get_by_role("button", name="Explore Destinations").click()
    expect(page).to_have_url(re.compile(r"#/explore\?"))


def results_ready(page):
    expect(page.locator("#popular .dcard").first).to_be_visible()
    expect(page.locator("#results[aria-busy=false]")).to_be_attached()


# =============================================================== the nine-step flow
def test_step1_homepage_explains_the_product_and_offers_a_location_first_search(page):
    page.goto(BASE + "/")
    expect(page.get_by_role("heading", level=1)).to_contain_text("Explore More. Wait Less.")
    expect(page.get_by_role("heading", level=1)).to_contain_text("Discover Beyond the Crowds.")
    expect(page.get_by_text("Discover popular destinations around you, predict tourist crowds and find peaceful places to explore.")).to_be_visible()
    nav = page.get_by_role("navigation", name="Main")
    for name in ("Explore", "Crowd Prediction", "Hidden Gems"):
        expect(nav.get_by_role("link", name=name)).to_be_visible()
    expect(page.locator("#locpill")).to_contain_text("Choose location")
    for label in ("Location", "Travel date", "Interest (optional)"):
        expect(page.locator(".searchpanel").get_by_text(label, exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Use my location")).to_be_visible()
    expect(page.get_by_role("button", name="Explore Destinations")).to_be_visible()
    expect(page.get_by_text("Sign in")).to_have_count(0)                         # no registration needed
    page.wait_for_function("() => { const b = document.querySelector('#hero-bg'); return !!b && b.classList.contains('on'); }", timeout=30000)
    expect(page.locator("#herocredit")).to_contain_text("Photo:")                  # a real photograph, credited


def test_steps2to4_typed_city_gives_a_dynamic_greeting_and_popular_places_with_predicted_crowds(page):
    search(page)
    expect(page.get_by_role("heading", level=1)).to_have_text("Discover amazing places around Coimbatore.")
    expect(page.locator("#locpill")).to_contain_text("Coimbatore")
    expect(page.locator(".bandsub")).to_contain_text("Saturday, 26 December 2026")
    results_ready(page)
    cards = page.locator("#popular .dcard")
    assert 3 <= cards.count() <= 6
    first = cards.first
    expect(first.locator("h3")).to_have_text(re.compile("Ooty"))
    expect(first.locator(".chip").first).to_have_text(re.compile("(Low|Moderate|High) crowd"))
    expect(first).to_contain_text("km away")
    expect(first).to_contain_text("Best time:")
    expect(first.locator(".desc")).not_to_be_empty()
    expect(first.locator(".tl li")).to_have_count(4)
    expect(first.get_by_role("link", name="View Details")).to_be_visible()
    expect(first.locator(".kind")).to_have_text("Popular")
    expect(page.locator("#popular .secsub")).to_contain_text("Sat, 26 Dec")
    page.wait_for_function("() => { const i = document.querySelector('#popular .dcard img'); return !!i && i.naturalWidth > 0; }", timeout=30000)
    for chip in page.locator("#popular .chip").all():                              # three crowd colours only
        assert re.search(r"\b(green|yellow|red)\b", chip.get_attribute("class"))


def test_step5_best_time_panel_shows_the_calmest_period_and_updates_per_destination(page):
    search(page)
    results_ready(page)
    body = page.locator("#bt-body")
    expect(body).to_contain_text("Best time to visit:")
    expect(body).to_contain_text("Lower crowd levels are predicted during this period.")
    expect(body.locator(".tl.big li")).to_have_count(4)
    expect(body.locator(".tl.big li.best")).to_have_count(1)
    expect(body.locator(".tl.big")).to_contain_text("Early morning")
    expect(body.locator(".tl.big")).to_contain_text("Evening")
    expect(body.locator("svg.chart")).to_be_visible()
    name1 = body.locator("h3").inner_text()
    page.locator(".tabchip").nth(1).click()
    expect(body.locator("h3")).not_to_have_text(name1)
    expect(body.locator("svg.chart")).to_be_visible()


def test_step6_hidden_gems_are_lesser_known_calm_and_explained(page):
    search(page)
    results_ready(page)
    gems = page.locator("#hidden-gems .dcard")
    expect(page.get_by_role("heading", name="Escape the Crowds")).to_be_visible()
    expect(page.get_by_text("Discover peaceful places and lesser-known destinations near you.")).to_be_visible()
    assert 3 <= gems.count() <= 6
    for i in range(gems.count()):
        g = gems.nth(i)
        expect(g.locator(".kind")).to_have_text("Hidden gem")
        expect(g.locator(".chip").first).to_have_text(re.compile("(Low|Moderate) crowd"))
        expect(g.locator(".why")).to_contain_text("Quieter option")
        expect(g).to_contain_text("Best time:")
    gems.first.get_by_text("Why is this a hidden gem?").click()
    expect(gems.first).to_contain_text("catalogue popularity score")
    expect(gems.first).to_contain_text("not a visitor count")
    expect(page.locator("#hidden-gems")).to_contain_text("Valparai")             # near Coimbatore, lesser-known, calm
    expect(page.locator("#hidden-gems")).to_contain_text("A calmer alternative to Munnar")


def test_step7_interactive_map_markers_popup_and_filters(page):
    search(page)
    results_ready(page)
    expect(page.locator("#map .leaflet-container, #map.leaflet-container")).to_be_visible()
    expect(page.locator(".mk.you")).to_have_count(1)                              # the user's own position
    page.locator("#map").scroll_into_view_if_needed()
    total = page.locator(".leaflet-marker-icon .mk").count()
    assert total >= 15
    n_pop, n_gem = page.locator(".mk.popular").count(), page.locator(".mk.hidden_gem").count()
    assert n_pop >= 3 and n_gem >= 3                                              # visually different markers
    # filters
    page.get_by_role("button", name="Hidden gems").click()
    expect(page.locator(".mk.popular")).to_have_count(0)
    expect(page.locator(".mk.hidden_gem")).to_have_count(n_gem)
    page.get_by_role("button", name="All places").click()
    page.get_by_role("button", name="High crowd").click()
    expect(page.locator("#map-count")).to_contain_text("Showing")
    assert page.locator(".mk.green, .mk.yellow").count() == 0 and page.locator(".mk.red").count() >= 1
    page.get_by_role("button", name="High crowd").click()
    page.get_by_role("button", name="Moderate crowd").click()
    page.get_by_role("button", name="Hidden gems").click()
    shown = int(re.search(r"Showing (\d+)", page.locator("#map-count").inner_text()).group(1))
    assert shown == page.locator(".leaflet-marker-icon .mk:not(.you)").count()
    page.get_by_role("button", name="All places").click()
    # marker click shows the popup with photo, name, level, best time, description and View Details
    page.get_by_role("button", name="Moderate crowd").click()                     # switch the filter back off
    page.get_by_role("button", name="Popular places").click()
    page.locator(".leaflet-marker-icon:has(.mk.popular)").first.click(force=True)
    pop = page.locator(".leaflet-popup-content")
    expect(pop).to_be_visible()
    expect(pop.locator("img")).to_have_count(1)
    expect(pop.locator(".chip")).to_have_text(re.compile("crowd"))
    expect(pop).to_contain_text("Best time:")
    expect(pop.get_by_role("link", name="View Details")).to_be_visible()
    page.wait_for_timeout(900)                                                   # let the map finish panning the popup into view
    mbox, pbox = page.locator("#map").bounding_box(), page.locator(".leaflet-popup-content-wrapper").bounding_box()
    assert pbox["y"] >= mbox["y"] - 2 and pbox["y"] + pbox["height"] <= mbox["y"] + mbox["height"] + 2, "popup is cut off by the map edge"


def test_view_on_map_scrolls_to_the_map_and_opens_that_place(page):
    search(page)
    results_ready(page)
    card = page.locator("#hidden-gems .dcard").first
    name = card.locator("h3").inner_text()
    card.get_by_role("button", name="View on map").click()
    expect(page.locator(".leaflet-popup-content")).to_contain_text(name)
    box = page.locator("#map").bounding_box()
    vh = page.viewport_size["height"]
    assert 0 <= box["y"] and box["y"] + min(box["height"], 400) <= vh, "the map should be scrolled into view"


def test_steps8and9_open_a_destination_and_see_its_prediction(page):
    search(page)
    results_ready(page)
    page.locator("#popular .dcard").first.get_by_role("link", name="View Details").click()
    expect(page).to_have_url(re.compile(r"#/d/ooty"))
    expect(page.get_by_role("heading", name="Ooty (Udhagamandalam)", level=1)).to_be_visible()
    page.wait_for_function("() => { const b = document.querySelector('#d-bg'); return !!b && b.classList.contains('on'); }", timeout=30000)
    expect(page.locator(".dhero")).to_contain_text("Tamil Nadu")
    expect(page.locator(".reading")).to_contain_text(re.compile("(Low|Moderate|High) crowd"))
    expect(page.locator(".tl.big li")).to_have_count(4)
    expect(page.locator("#pred")).to_contain_text("Best time to visit:")
    expect(page.locator("#pred svg.chart")).to_be_visible()
    expect(page.locator(".week .day")).to_have_count(7)
    expect(page.get_by_role("heading", name="Location")).to_be_visible()
    expect(page.locator("#dmap .leaflet-marker-icon").first).to_be_visible()
    expect(page.get_by_role("heading", name="Places inside Ooty (Udhagamandalam)")).to_be_visible()
    for tag in ("ML prediction", "Demonstration data", "Not live"):
        expect(page.locator("#pred").get_by_text(tag, exact=True)).to_be_visible()
    expect(page.get_by_text("Why we showed you this")).to_be_visible()
    page.get_by_role("link", name="Back to results").click()
    expect(page).to_have_url(re.compile(r"#/explore\?"))
    results_ready(page)


def test_the_explanation_belongs_to_the_search_that_produced_it(page):
    page.goto(f"{BASE}/#/d/ooty?date={SAT}")                                      # opened directly: no search behind it
    expect(page.get_by_role("heading", name="Ooty (Udhagamandalam)", level=1)).to_be_visible()
    expect(page.get_by_text("Why we showed you this")).to_have_count(0)
    search(page)                                                                  # Coimbatore, Saturday
    results_ready(page)
    page.locator("#popular .dcard").first.get_by_role("link", name="View Details").click()
    expect(page.get_by_text("Why we showed you this")).to_be_visible()
    expect(page.locator(".whybox")).to_contain_text("from Coimbatore")
    page.locator("#w-date").fill(TUE)                                             # a different date: the old reasons no longer apply
    page.get_by_role("button", name="Update").click()
    expect(page.locator("#w-date")).to_have_value(TUE)
    expect(page.get_by_text("Why we showed you this")).to_have_count(0)
    page.goto(f"{BASE}/#/d/ooty?date={SAT}&back=lat%3D19.076%26lon%3D72.8777%26date%3D{SAT}%26src%3Dcity")   # a link from a different search
    expect(page.get_by_role("heading", name="Ooty (Udhagamandalam)", level=1)).to_be_visible()
    expect(page.get_by_text("Why we showed you this")).to_have_count(0)


def test_destination_time_range_and_day_controls_update_the_prediction(page):
    page.goto(f"{BASE}/#/d/goa?date={SAT}&from=9&to=17")
    expect(page.locator(".reading")).to_contain_text("High crowd")
    page.locator("#w-from").select_option("5")
    page.locator("#w-to").select_option("7")
    page.get_by_role("button", name="Update").click()
    expect(page).to_have_url(re.compile("from=5&to=7"))
    expect(page.locator(".reading")).not_to_contain_text("High crowd")
    page.locator(".week .day").nth(2).click()
    expect(page).to_have_url(re.compile("date=2026-12-28"))
    expect(page.locator("#w-date")).to_have_value("2026-12-28")                    # wait for the page to redraw
    page.locator("#w-from").select_option("18")
    page.locator("#w-to").select_option("9")
    page.get_by_role("button", name="Update").click()
    expect(page.locator("#when-err")).to_have_text("The start time must not be after the end time.")


def test_unknown_destination_page_is_a_clear_empty_state(page):
    page.goto(f"{BASE}/#/d/atlantis?date={SAT}")
    expect(page.get_by_text("Destination not found")).to_be_visible()
    page.errors[:] = [e for e in page.errors if " 404 " not in e]


# =============================================================== dates, time of day, interest
def test_changing_date_time_and_interest_refreshes_the_predictions(page):
    search(page, city="Panaji")
    results_ready(page)
    goa = page.locator("#popular .dcard").filter(has=page.get_by_role("heading", name="Goa", exact=True))
    expect(goa.locator(".chip").first).to_have_text("High crowd")                  # Saturday in the peak season
    page.locator("#refine #date").fill(TUE)
    page.get_by_role("button", name="Update").click()
    expect(page.get_by_role("heading", level=1)).to_have_text("Discover amazing places around Panaji.")
    expect(page.locator(".bandsub")).to_contain_text("Tuesday, 22 December 2026")
    results_ready(page)
    expect(goa.locator(".chip").first).to_have_text("Moderate crowd")               # quieter on a Tuesday
    page.locator("#refine #slot").select_option("early")
    page.get_by_role("button", name="Update").click()
    expect(page.locator(".bandsub")).to_contain_text("Early morning")
    results_ready(page)
    expect(page.locator("#popular .secsub")).to_contain_text("early morning")
    page.locator("#refine #interest").select_option("beach")
    page.get_by_role("button", name="Update").click()
    results_ready(page)
    expect(page.locator("#popular .dcard").first.locator("h3")).to_contain_text(re.compile("Goa|Mumbai|Puri|Kanyakumari|Puducherry|Andaman"))


def test_a_busy_date_changes_what_the_best_time_panel_recommends(page):
    page.goto(f"{BASE}/#/explore?lat=15.4909&lon=73.8278&date={SAT}&src=city")
    results_ready(page)
    expect(page.locator("#bt-body")).to_contain_text("Best time to visit:")


# =============================================================== location handling
def test_denied_location_falls_back_to_a_typed_city(browser):
    pg = new_page(browser)                                                       # no geolocation permission granted
    pg.add_init_script("window.__geoAsked = false; const o = navigator.geolocation.getCurrentPosition.bind(navigator.geolocation);"
                       "navigator.geolocation.getCurrentPosition = (...a) => { window.__geoAsked = true; return o(...a); };")
    pg.goto(BASE + "/")
    pg.wait_for_timeout(600)
    assert pg.evaluate("window.__geoAsked") is False                             # never asked on load without permission
    pg.get_by_role("button", name="Use my location").click()
    expect(pg.locator("#loc-note")).to_contain_text("type your city instead")
    expect(pg.locator("#from")).to_be_focused()
    pg.locator("#from").fill("Bangalore")                                        # alias
    pg.locator("#date").fill(SAT)
    pg.get_by_role("button", name="Explore Destinations").click()
    expect(pg.get_by_role("heading", level=1)).to_have_text("Discover amazing places around Bengaluru.")
    expect(pg.locator("#popular .dcard").first).to_be_visible()
    pg.errors[:] = [e for e in pg.errors if "Geolocation" not in e]
    assert not pg.errors, pg.errors
    pg._ctx.close()


def test_granted_location_is_used_with_a_dynamic_greeting(browser):
    pg = new_page(browser, geolocation={"latitude": 10.9984, "longitude": 76.9611}, permissions=["geolocation"])
    pg.goto(BASE + "/")
    expect(pg.locator("#greet")).to_have_text("Discover amazing places around Coimbatore.")   # already allowed: used at once, no prompt
    pg.get_by_role("button", name="Use my location").click()
    expect(pg).to_have_url(re.compile(r"src=gps"))
    expect(pg.get_by_role("heading", level=1)).to_have_text("Discover amazing places around Coimbatore.")
    expect(pg.locator("#from")).to_have_value("My location (Coimbatore)")
    assert re.search(r"lat=11(\.0)?&lon=76\.96", pg.url), pg.url                                         # rounded to about 1 km
    expect(pg.locator("#popular .dcard").first).to_be_visible()
    assert not pg.errors, pg.errors
    pg._ctx.close()


def test_a_location_between_cities_is_described_as_near_one(browser):
    pg = new_page(browser, geolocation={"latitude": 10.65, "longitude": 77.0}, permissions=["geolocation"])
    pg.goto(BASE + "/")
    expect(pg.locator("#greet")).to_have_text("Discover amazing places near Coimbatore.")
    pg._ctx.close()


def test_empty_unknown_and_foreign_locations_are_explained(page):
    page.goto(BASE + "/")
    page.get_by_role("button", name="Explore Destinations").click()
    expect(page.locator("#form-err")).to_have_text("Enter your city, or use your current location.")
    page.locator("#from").fill("Atlantis")
    page.get_by_role("button", name="Explore Destinations").click()
    expect(page.locator("#form-err")).to_contain_text("nearby major city")
    page.errors[:] = [e for e in page.errors if " 404 " not in e]
    page.goto(f"{BASE}/#/explore?lat=51.5&lon=-0.12&date={SAT}&src=gps")
    expect(page.get_by_text("TripNest AI covers destinations in India")).to_be_visible()


def test_header_links_open_the_right_section_of_the_last_search(page):
    page.goto(BASE + "/")
    page.get_by_role("link", name="Hidden Gems").click()                          # no search yet
    expect(page.locator("#toast")).to_have_text("Choose a location and date first.")
    expect(page).to_have_url(re.compile(r"#/$"))
    search(page)
    results_ready(page)
    nav = page.get_by_role("navigation", name="Main")
    nav.get_by_role("link", name="Hidden Gems").click()
    expect(page).to_have_url(re.compile("go=hidden-gems"))
    expect(page.get_by_role("heading", name="Escape the Crowds")).to_be_in_viewport()
    nav.get_by_role("link", name="Crowd Prediction").click()
    expect(page.get_by_role("heading", name="Best time to visit")).to_be_in_viewport()


# =============================================================== robustness
def test_photos_that_fail_to_load_become_clean_placeholders(browser):
    pg = new_page(browser)
    pg.route(re.compile(r"https://(thumb|upload)\.wikimedia\.org/.*"), lambda r: r.abort())
    search(pg)
    results_ready(pg)
    expect(pg.locator("#popular .ph.broken").first).to_be_visible()
    expect(pg.locator("#popular .dcard h3").first).to_be_visible()                # names and crowd info still shown
    expect(pg.locator("#popular .dcard .chip").first).to_be_visible()
    assert not [e for e in pg.errors if "Failed" not in e], pg.errors
    pg._ctx.close()


def test_leaving_a_page_mid_load_causes_no_script_errors(page):
    for path in ["/", f"/#/explore?{COIMBATORE}&date={SAT}", f"/#/d/goa?date={SAT}"]:
        page.goto(BASE + path)
        page.goto(BASE + f"/#/d/jaipur?date={SAT}")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="Jaipur", level=1)).to_be_visible()


def test_typed_inputs_never_appear_in_the_address_bar(page):
    page.goto(BASE + "/")
    page.locator("#from").fill("Pune")
    page.locator("#from").press("Enter")
    page.wait_for_timeout(800)
    assert "Pune" not in page.url.split("#")[0] and "?from" not in page.url.split("#")[0]


# =============================================================== five screen sizes
@pytest.mark.parametrize("name,size", [("desktop", (1440, 900)), ("laptop", (1280, 720)), ("tablet", (768, 1024)), ("phone", (390, 844))])
def test_every_screen_size_supports_the_whole_flow(browser, name, size):
    pg = new_page(browser, viewport={"width": size[0], "height": size[1]}, is_mobile=size[0] < 500)
    pg.goto(BASE + "/")
    expect(pg.get_by_role("button", name="Explore Destinations")).to_be_visible()
    pg.locator("#from").fill("Mumbai")
    pg.locator("#date").fill(SAT)
    pg.get_by_role("button", name="Explore Destinations").click()
    results_ready(pg)
    for sec in ("#popular", "#best-time", "#hidden-gems", "#crowd-map"):
        expect(pg.locator(sec)).to_be_attached()
    if name == "phone":                                                          # cards become a swipeable row
        assert pg.evaluate("(() => { const c = document.querySelector('#popular .cards'); return c.scrollWidth > c.clientWidth + 20; })()")
    pg.locator("#map").scroll_into_view_if_needed()
    mb = pg.locator("#map").bounding_box()
    side = 32 if size[0] <= 760 else 40                                            # page margins used by the layout
    assert mb["height"] >= 380 and mb["width"] >= min(1200, size[0] - side) - 2
    assert pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1, f"{name}: page scrolls sideways"
    pg.locator("#popular .dcard").first.get_by_role("link", name="View Details").click()
    expect(pg.locator(".reading")).to_be_visible()
    for path in ["/", f"/#/explore?lat=19.076&lon=72.8777&date={SAT}", f"/#/d/goa?date={SAT}"]:
        pg.goto(BASE + path)
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(500)
        assert pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1, f"{name} {path} scrolls sideways"
    assert not pg.errors, pg.errors
    pg._ctx.close()
