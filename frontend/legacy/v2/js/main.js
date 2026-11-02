// TripNest AI: three pages. #/ (home), #/results, #/d/<destination>.
import { $, esc } from "./core.js";
import { home } from "./home.js";
import { results } from "./results.js";
import { destination } from "./destination.js";

const ROUTES = [
  [/^\/?$/, (el) => home(el), "Find quiet destinations"],
  [/^\/results$/, (el, p) => results(el, p), "Recommended destinations"],
  [/^\/d\/([a-z0-9-]+)$/, (el, p, m) => destination(el, p, m[1]), "Destination crowd prediction"],
];
const mark = `<svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true"><rect width="32" height="32" rx="16" fill="#141414"/><path d="M4 24 C9 24 11 9 16 9 S23 22 28 22 L28 26 L4 26Z" fill="#f2a516"/></svg>`;

let seq = 0;
async function render() {
  const raw = location.hash.slice(1) || "/";
  const [path, query] = raw.split("?");
  const route = ROUTES.find(([re]) => re.test(path));
  const root = $("#root");
  if (!$("#frame")) root.innerHTML = `<div class="frame" id="frame"><header class="topbar"><a class="wordmark" href="#/">${mark}<span>TripNest AI</span></a>
    <nav aria-label="Main"><a href="#/">Find destinations</a></nav></header><main id="main" tabindex="-1"></main></div>`;
  const main = $("#main");
  const my = ++seq;
  const view = document.createElement("div");
  main.replaceChildren(view);
  window.scrollTo(0, 0);
  if (!route) {
    document.title = "Page not found — TripNest AI";
    view.innerHTML = `<div class="d-card" style="margin:24px"><div class="empty"><strong>We couldn't find that page</strong>Go back to the <a href="#/">TripNest AI home page</a>.</div></div>`;
    return;
  }
  document.title = `${route[2]} — TripNest AI`;
  try { await route[1](view, new URLSearchParams(query || ""), path.match(route[0])); }
  catch (e) { if (my === seq) view.innerHTML = `<div class="d-card" style="margin:24px"><div class="error-box" role="alert">${esc(e.message)}</div></div>`; }
}

// Every form is handled by script; never let a native submit put fields in the address bar.
document.addEventListener("submit", (e) => e.preventDefault(), true);
window.addEventListener("hashchange", render);
render();
