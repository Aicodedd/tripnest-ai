"""Browser end-to-end tests of the five mandatory user journeys (Playwright, real Chrome).

Run (from the repo root):  sh e2e/run.sh
The script starts an isolated server on port 8020 with a throwaway SQLite database.
"""
import os
import re
import time

import pytest
from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("E2E_BASE", "http://localhost:8020")
ADMIN_EMAIL = os.environ.get("E2E_ADMIN_EMAIL", "e2e-admin@example.com")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "E2e-Admin-Pass-1")
RUN = str(int(time.time()))


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        yield b
        b.close()


@pytest.fixture()
def page(browser):
    ctx = browser.new_context(viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(f"{e} | {(e.stack or "").splitlines()[1:3]}"))
    pg.on("response", lambda r: pg.errors.append(f"HTTP {r.status} {r.url}") if r.status >= 400 and "/api/" in r.url else None)
    pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" and "tile.openstreetmap" not in m.text
          and "open-meteo" not in m.text and "Failed to load resource" not in m.text else None)
    yield pg
    assert not pg.errors, f"browser errors: {pg.errors}"
    ctx.close()


def register(page, email, name="E2E Traveller", password="E2e-pass-123"):
    page.goto(f"{BASE}/#/register")
    page.get_by_label("Name").fill(name)
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Create account").click()
    expect(page).to_have_url(re.compile(r"#/discover"))


def login(page, email, password):
    page.goto(f"{BASE}/#/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()


# 1 ------------------------------------------------------------------
def test_journey1_register_login_and_manage_profile(page):
    email = f"asha{RUN}@example.com"
    register(page, email, name="Asha Iyer")
    page.goto(f"{BASE}/#/home")
    expect(page.get_by_role("heading", level=1)).to_contain_text("Hello, Asha.")
    page.get_by_role("link", name=re.compile("Your profile")).click()
    expect(page.get_by_role("heading", name="Your profile")).to_be_visible()
    page.get_by_label("Home city").fill("Chennai")
    page.get_by_label("Budget").select_option("low")
    page.get_by_role("button", name="Heritage").click()
    page.get_by_role("button", name="Save profile").click()
    expect(page.locator("#toast")).to_have_text("Profile saved")
    page.get_by_role("button", name="Sign out").click()
    expect(page.get_by_role("heading", name="Go at the quiet hour")).to_be_visible()
    login(page, email, "E2e-pass-123")
    expect(page).to_have_url(re.compile(r"#/discover"))
    page.goto(f"{BASE}/#/profile")
    expect(page.get_by_label("Home city")).to_have_value("Chennai")
    expect(page.get_by_role("button", name="Heritage")).to_have_attribute("aria-pressed", "true")


def test_credentials_never_appear_in_the_url(page):
    page.goto(f"{BASE}/#/login")
    page.get_by_label("Email").fill("leak@example.com")
    page.get_by_label("Password").fill("Secret-pass-1")
    page.get_by_label("Password").press("Enter")  # submit as fast as possible
    page.wait_for_timeout(800)
    assert "Secret-pass-1" not in page.url and "password" not in page.url
    page.errors[:] = [e for e in page.errors if " 401 " not in e]


def test_journey1b_wrong_password_shows_clear_error(page):
    login(page, "nobody@example.com", "Wrong-pass-1")
    expect(page.locator("#auth-err")).to_have_text("Invalid email or password")
    page.errors[:] = [e for e in page.errors if " 401 " not in e]  # the 401 is the behaviour under test


# 2 ------------------------------------------------------------------
def test_journey2_discover_destinations_and_crowds(page):
    page.goto(BASE + "/")
    expect(page.locator("#dial-level")).to_have_text(re.compile(r"Low|Moderate|High|At Capacity"))
    page.locator("#dial-hour").fill("6")
    expect(page.locator("#dial-advice")).to_contain_text("6 AM")
    page.goto(f"{BASE}/#/explore")
    page.get_by_label("Search", exact=True).fill("Hampi")
    page.get_by_role("button", name="Show destinations").click()
    expect(page.locator(".dcard")).to_have_count(1)
    page.locator(".dcard").first.click()
    expect(page.get_by_role("heading", name="Hampi", level=1)).to_be_visible()
    page.get_by_role("button", name="Saturday 4 PM").click()
    expect(page.locator("#crowd .row").first).to_be_visible()
    expect(page.locator("#crowd")).to_contain_text("Demonstration data")
    expect(page.locator("#forecast svg.chart")).to_be_visible()
    expect(page.locator("#forecast")).to_contain_text("Quietest times this week")
    # filters by state
    page.goto(f"{BASE}/#/explore?state=KL")
    expect(page.locator(".dcard").first).to_be_visible()
    for t in page.locator(".dcard .note").all_text_contents():
        assert t == "Kerala"
    # compare
    page.goto(f"{BASE}/#/compare?slugs=goa,puducherry&date=2026-11-14")
    expect(page.locator("#cmp-out svg.chart")).to_be_visible()


# 3 ------------------------------------------------------------------
def test_journey3_generate_save_and_edit_itinerary(page):
    register(page, f"planner{RUN}@example.com", name="Ravi Planner")
    page.goto(f"{BASE}/#/plan?d=jaipur")
    expect(page.locator(".day").first).to_be_visible()
    expect(page.locator(".day")).to_have_count(2)
    page.get_by_label("Trip name").fill("Jaipur weekend")
    page.get_by_role("button", name="Save trip").click()
    expect(page).to_have_url(re.compile(r"#/trips/\d+$"))
    expect(page.get_by_role("heading", name="Jaipur weekend")).to_be_visible()
    first = page.locator(".day").first.locator(".stop strong").first.inner_text()
    page.locator(".day").first.locator(".stop").first.get_by_role("button", name=re.compile("Move .* later")).click()
    expect(page.locator("#toast")).to_have_text("Times updated")
    expect(page.locator(".day").first.locator(".stop strong").nth(1)).to_have_text(first)
    page.get_by_label("Notes").fill("Book Amber Fort tickets online")
    page.get_by_role("button", name="Save changes").click()
    expect(page.locator("#toast")).to_have_text("Changes saved")
    page.reload()
    expect(page.get_by_label("Notes")).to_have_value("Book Amber Fort tickets online")
    page.goto(f"{BASE}/#/trips")
    expect(page.get_by_text("Jaipur weekend")).to_be_visible()


# 4 ------------------------------------------------------------------
def test_journey4_submit_review(page):
    register(page, f"reviewer{RUN}@example.com", name="Meera Reviewer")
    page.goto(f"{BASE}/#/d/hampi")
    page.get_by_label("Rating").select_option("4")
    page.get_by_label("Your review").fill("Beautiful at sunrise but the parking was a nightmare and toilets were dirty.")
    page.get_by_role("button", name="Post review").click()
    expect(page.locator("#toast")).to_contain_text("Review posted")
    expect(page.locator("#reviews")).to_contain_text("Meera Reviewer")
    expect(page.locator("#reviews")).to_contain_text("Parking")


# 5 ------------------------------------------------------------------
def test_journey5_admin_manages_content(page, browser):
    # a traveller posts and reports something
    ctx = browser.new_context()
    t = ctx.new_page()
    register(t, f"poster{RUN}@example.com", name="Spam Poster")
    t.goto(f"{BASE}/#/community")
    t.get_by_label("Title").fill(f"Cheap tickets {RUN}")
    t.get_by_label("Your experience").fill("Visit my site for cheap tickets")
    t.get_by_role("button", name="Publish post").click()
    expect(t).to_have_url(re.compile(r"#/community/\d+$"))
    post_url = t.url
    t.once("dialog", lambda d: d.accept("Spam advertising"))
    t.get_by_role("button", name="Report post").click()
    expect(t.locator("#toast")).to_contain_text("Reported")
    ctx.close()

    # travellers cannot open the console
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    expect(page).to_have_url(re.compile(r"#/admin$"))
    expect(page.get_by_role("heading", name="Admin console")).to_be_visible()
    expect(page.locator("#admin-body")).to_contain_text(re.compile("Forecast alerts"))
    page.get_by_role("tab", name=re.compile("Reported content")).click()
    row = page.locator(".row", has_text=f"Cheap tickets {RUN}")
    row.get_by_role("button", name="Hide content").click()
    expect(page.locator("#toast")).to_have_text("Content hidden")
    page.goto(post_url)
    expect(page.get_by_text("Post not available")).to_be_visible()
    page.errors[:] = [e for e in page.errors if not (" 404 " in e and "/api/posts/" in e)]  # hidden post must 404
    # destinations: toggle featured
    page.goto(f"{BASE}/#/admin?tab=destinations")
    btn = page.locator("tr", has_text="Kohima").get_by_role("button", name=re.compile("featured", re.I))
    before = btn.inner_text()
    btn.click()
    expect(page.locator("#toast")).to_have_text("Updated")
    expect(page.locator("tr", has_text="Kohima").get_by_role("button", name=re.compile("featured", re.I))).not_to_have_text(before)
    # system tab shows the model
    page.goto(f"{BASE}/#/admin?tab=system")
    expect(page.locator("#admin-body")).to_contain_text("Crowd model")


def test_traveller_is_refused_admin_console(page):
    register(page, f"curious{RUN}@example.com", name="Curious")
    page.goto(f"{BASE}/#/admin")
    expect(page.get_by_text("Administrators only")).to_be_visible()


def test_phone_layout_has_menu_and_no_horizontal_scroll(browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    p = ctx.new_page()
    for path in ["/", "/#/explore", "/#/d/goa", "/#/plan"]:
        p.goto(BASE + path)
        p.wait_for_load_state("networkidle")
        overflow = p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1, f"{path} scrolls sideways by {overflow}px"
    p.goto(BASE + "/#/explore")
    p.get_by_role("button", name="Menu").click()
    expect(p.get_by_role("link", name="Trip planner")).to_be_visible()
    ctx.close()


def test_leaving_a_page_mid_load_causes_no_script_errors(page):
    for path in ["/", "/#/d/goa", "/#/compare", "/#/explore"]:
        page.goto(BASE + path)
        page.goto(BASE + "/#/about")  # leave immediately, before the previous page's requests finish
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="How our data works")).to_be_visible()


def test_discover_shows_photos_crowd_details_reviews_and_coloured_heat(page):
    page.goto(f"{BASE}/#/discover?d=agra")
    expect(page.get_by_role("heading", name="Agra", level=1)).to_be_visible()
    expect(page.locator("[data-attr]")).to_have_count(4)
    page.get_by_role("tab", name="Saturday").click()
    page.locator("#d-hour").fill("11")
    expect(page.locator(".stat-pop")).to_contain_text("At Capacity")      # dark stat card on the map
    expect(page.locator("#cd-stats .stat.At-Capacity").first).to_be_visible()  # reddish stat tiles
    expect(page.locator("[data-lv='agra-taj-mahal']")).to_contain_text("At Capacity")
    expect(page.locator("canvas.leaflet-heatmap-layer")).to_have_count(1)  # crowd heat drawn on the map
    expect(page.locator("#rv-box")).to_contain_text("/ 5")
    page.locator("[data-attr='agra-mehtab-bagh']").click()
    expect(page.locator(".stat-pop")).to_contain_text("Mehtab Bagh")
    page.get_by_label("Search a place").fill("Munnar")
    page.get_by_role("button", name="Search", exact=True).click()
    expect(page.get_by_role("heading", name="Munnar", level=1)).to_be_visible()
    expect(page.get_by_role("link", name="Plan a trip to Munnar")).to_be_visible()


def test_quiet_places_get_no_heat_colour(page):
    data = page.request.get(f"{BASE}/api/crowd/map?at=2026-11-10T06:00").json()
    quiet = [p for p in data["points"] if p["level"] in ("Low", "Closed")]
    assert quiet and all(p["heat"] == 0 for p in quiet)
