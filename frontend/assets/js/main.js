// TripNest AI: router and page frame. Routes: #/ (landing), #/explore, #/d/<destination>.
import { $, $$, esc, toast } from "./core.js";
import { ICON, mem, exploreUrl } from "./ui.js";
import { landing } from "./landing.js";
import { explore } from "./explore.js";
import { destination } from "./destination.js";

const ROUTES = [
  [/^\/?$/, (el) => landing(el), "Explore more, wait less"],
  [/^\/explore$/, (el, p) => explore(el, p), "Places around you"],
  [/^\/d\/([a-z0-9-]+)$/, (el, p, m) => destination(el, p, m[1]), "Destination crowd prediction"],
];

const header = () => `<header class="top"><div class="wrap topin">
  <a class="logo" href="#/" aria-label="TripNest AI home">${ICON.plane}<span>TripNest AI</span></a>
  <nav aria-label="Main" class="nav"><a href="#/explore" data-nav="explore">Explore</a><a href="#/explore?go=best-time" data-nav="best-time">Crowd Prediction</a><a href="#/explore?go=hidden-gems" data-nav="hidden-gems">Hidden Gems</a></nav>
  <a class="locpill" id="locpill" href="#/" title="Change location">${ICON.pin}<span id="locname">Choose location</span></a></div></header>`;
const footer = () => `<footer class="foot"><div class="wrap"><p><b>TripNest AI</b>. Discover Smarter. Travel Better. Explore Beyond the Crowds.</p>
  <p class="note">Crowd figures are ML predictions trained on demonstration data, not live counts. Hours, fees and distances are indicative. Map © OpenStreetMap contributors. Photos from Wikimedia Commons, credited on each page.</p></div></footer>`;

// The header links open the last search at the right section; without a search they point to the search form.
function navTarget(section) {
  const last = mem.get("last");
  if (!last || !last.lat) { toast("Choose a location and date first."); return "#/"; }
  return exploreUrl(last, section ? { go: section } : {});
}
let seq = 0;

async function render() {
  const raw = location.hash.slice(1) || "/";
  const [path, query] = raw.split("?");
  const params = new URLSearchParams(query || "");
  const route = ROUTES.find(([re]) => re.test(path));
  const root = $("#root");
  if (!$("#frame")) { root.innerHTML = `<div id="frame">${header()}<main id="main" tabindex="-1"></main>${footer()}</div>`; bindHeader(); }
  const last = mem.get("last");
  $("#locname").textContent = last && last.name ? last.name : "Choose location";
  $$(".nav a").forEach((a) => a.removeAttribute("aria-current"));
  if (path === "/explore") $(`.nav a[data-nav="${params.get("go") || "explore"}"]`)?.setAttribute("aria-current", "page");
  const main = $("#main"), my = ++seq, view = document.createElement("div");
  main.replaceChildren(view);
  window.scrollTo(0, 0);
  if (!route) {
    document.title = "Page not found — TripNest AI";
    view.innerHTML = `<div class="wrap pad"><div class="card emptybox"><h1>We couldn't find that page</h1><p><a class="btn primary" href="#/">Go to the TripNest AI home page</a></p></div></div>`;
    return;
  }
  document.title = `${route[2]} — TripNest AI`;
  try { await route[1](view, params, path.match(route[0])); }
  catch (e) { if (my === seq) view.innerHTML = `<div class="wrap pad"><div class="error-box" role="alert">${esc(e.message)}</div></div>`; }
}

function bindHeader() {
  $(".skip")?.addEventListener("click", (e) => { e.preventDefault(); $("#main").focus(); });
  $$(".nav a").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    const target = navTarget(a.dataset.nav === "explore" ? "" : a.dataset.nav);
    if (target === location.hash) { render(); return; }
    location.hash = target;
  }));
}

document.addEventListener("submit", (e) => e.preventDefault(), true);   // forms are handled by script; never put fields in the address bar
window.addEventListener("hashchange", render);
render();
