// Router, app shell and sign-in screens.
import { $, $$, api, esc, toast, state, curvePath, reveal } from "./core.js";
import { landingShell, mountLanding } from "./landing.js";
import * as P from "./pages.js";
import { admin } from "./admin.js";
import { discover } from "./discover.js";
import { ICONS } from "./icons.js";

const NAV = [
  ["#/discover", "Discover", "discover"], ["#/home", "Home", "home"], ["#/explore", "Explore list", "explore"],
  ["#/compare", "Compare crowds", "compare"], ["#/recommend", "Recommendations", "recommend"], ["#/plan", "Trip planner", "plan"],
  ["#/trips", "My trips", "trips"], ["#/community", "Community", "community"], ["#/about", "How our data works", "about"],
];

const ROUTES = [
  [/^\/discover$/, (el, p) => discover(el, p), "Discover"],
  [/^\/home$/, (el, p) => P.home(el, p), "Home"],
  [/^\/explore$/, (el, p) => P.explore(el, p), "Explore"],
  [/^\/d\/([a-z0-9-]+)$/, (el, p, m) => P.destination(el, p, m[1]), "Destination"],
  [/^\/map$/, (el, p) => P.mapView(el, p), "Map"],
  [/^\/compare$/, (el, p) => P.compare(el, p), "Compare crowds"],
  [/^\/recommend$/, (el, p) => P.recommend(el, p), "Recommendations"],
  [/^\/plan$/, (el, p) => P.planner(el, p), "Trip planner"],
  [/^\/trips$/, (el, p) => P.trips(el, p), "My trips"],
  [/^\/trips\/(\d+)$/, (el, p, m) => P.trip(el, p, m[1]), "Trip"],
  [/^\/community(?:\/([a-z0-9]+))?$/, (el, p, m) => P.community(el, p, m[1]), "Community"],
  [/^\/profile$/, (el, p) => P.profile(el, p), "Profile"],
  [/^\/about$/, (el, p) => P.about(el, p), "How our data works"],
  [/^\/admin$/, (el, p) => admin(el, p), "Admin"],
];

const mark = `<svg viewBox="0 0 32 32" width="40" height="40" aria-hidden="true"><rect width="32" height="32" rx="16" fill="#141414"/><path d="M4 24 C9 24 11 9 16 9 S23 22 28 22 L28 26 L4 26Z" fill="#f2a516"/></svg>`;

function shell() {
  const u = state.user;
  const item = ([h, l, ic]) => `<a href="${h}" aria-label="${esc(l)}">${ICONS[ic]}<span class="tip">${esc(l)}</span></a>`;
  return `<div class="shell" id="shell">
    <header class="mobilebar"><a class="wordmark" href="#/" style="padding:0">${mark}TripNest AI</a>
      <button class="btn quiet small" id="menu" aria-expanded="false" aria-controls="rail">Menu</button></header>
    <aside class="rail" id="rail" aria-label="Sections">
      <a class="logo" href="#/" aria-label="TripNest AI home page" style="background:none">${mark}</a>
      <nav>${NAV.map(item).join("")}${u && u.role === "admin" ? item(["#/admin", "Admin console", "admin"]) : ""}</nav>
      <div class="bottom">${u ? `<a class="me" href="#/profile" aria-label="Your profile (${esc(u.name)})">${esc(u.name.trim().charAt(0).toUpperCase())}<span class="tip">Profile</span></a>
        <button class="ic" id="logout" aria-label="Sign out">${ICONS.logout}<span class="tip">Sign out</span></button>`
        : `<a href="#/login" aria-label="Sign in">${ICONS.login}<span class="tip">Sign in</span></a>`}</div>
    </aside>
    <main class="sheet" id="main" tabindex="-1"></main></div>`;
}

function authScreen(mode, params) {
  const reg = mode === "register";
  return `<div class="auth"><div class="art"><a class="wordmark" href="#/" style="color:var(--ink);padding:0">${mark}TripNest AI</a>
      <svg class="curve" viewBox="0 0 1000 600" preserveAspectRatio="none" aria-hidden="true"><path id="auth-curve" fill="#f2a516" d="M0,600 L0,420 C300,420 420,80 560,80 S800,460 1000,470 L1000,600Z"/></svg>
      <p>${reg ? "Save trips, favourite places and plans that dodge the rush." : "Welcome back. Your saved trips are waiting."}</p></div>
    <div class="formside"><form id="auth-form" method="post" action="#" novalidate>
      <h1>${reg ? "Create your account" : "Sign in"}</h1>
      ${reg ? `<label class="field">Name<input name="name" required maxlength="80" autocomplete="name"></label>` : ""}
      <label class="field">Email<input name="email" type="email" required autocomplete="email"></label>
      <label class="field">Password<input name="password" type="password" required minlength="${reg ? 8 : 1}" maxlength="72" autocomplete="${reg ? "new-password" : "current-password"}" ${reg ? 'aria-describedby="pw-hint"' : ""}>
        ${reg ? '<span class="hint" id="pw-hint">At least 8 characters, with letters and numbers.</span>' : ""}</label>
      <p class="form-error" id="auth-err" role="alert"></p>
      <button class="btn" type="submit">${reg ? "Create account" : "Sign in"}</button>
      <p class="note">${reg ? 'Already have an account? <a href="#/login">Sign in</a>' : 'New to TripNest? <a href="#/register">Create an account</a>'} · <a href="#/">Back to home</a></p>
    </form></div></div>`;
}

async function mountAuth(mode, params) {
  const f = $("#auth-form");
  // Attach the handler before any await: a native submit must never run (it would put fields in the URL).
  api(`/api/attractions/agra-taj-mahal/forecast`).then((t) => {
    if (t.hourly.length > 2) $("#auth-curve")?.setAttribute("d", curvePath(t.hourly, 1000, 600));
  }).catch(() => { /* decorative only */ });
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = $("#auth-err");
    err.textContent = "";
    if (!f.reportValidity()) return;
    const btn = f.querySelector("button");
    btn.disabled = true;
    try {
      const body = { email: f.email.value.trim(), password: f.password.value };
      if (mode === "register") body.name = f.name.value.trim();
      const r = await api(`/api/auth/${mode === "register" ? "register" : "login"}`, { method: "POST", body });
      state.user = r.user;
      toast(mode === "register" ? "Account created" : `Signed in as ${r.user.name}`);
      location.hash = params.get("next") || (r.user.role === "admin" ? "#/admin" : "#/discover");
    } catch (ex) {
      err.textContent = ex.message;
      btn.disabled = false;
    }
  });
}

let renderSeq = 0;

async function render() {
  const raw = location.hash.slice(1) || "/";
  const [path, query] = raw.split("?");
  const params = new URLSearchParams(query || "");
  const root = $("#root");
  window.scrollTo(0, 0);

  if (path === "/" || path === "") {
    document.title = "TripNest AI — Go at the quiet hour";
    root.innerHTML = landingShell();
    return mountLanding();
  }
  if (path === "/login" || path === "/register") {
    if (state.user) { location.hash = "#/discover"; return; }
    document.title = (path === "/login" ? "Sign in" : "Create account") + " — TripNest AI";
    root.innerHTML = authScreen(path.slice(1), params);
    return mountAuth(path.slice(1), params);
  }
  if (!$("#shell")) root.innerHTML = shell(), bindShell();
  const main = $("#main");
  const route = ROUTES.find(([re]) => re.test(path));
  $$(".rail nav a").forEach((a) => {
    if (path.startsWith(a.getAttribute("href").slice(1))) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  $("#shell").classList.remove("open");
  if (!route) {
    document.title = "Not found — TripNest AI";
    renderSeq++;
    main.innerHTML = `<div class="page"><div class="empty"><strong>We couldn't find that page</strong>Check the address or go to <a href="#/explore">Explore</a>.</div></div>`;
    return;
  }
  document.title = `${route[2]} — TripNest AI`;
  // Each render gets its own container: a slower previous view can only write into its own, now detached, node.
  const my = ++renderSeq;
  const view = document.createElement("div");
  main.replaceChildren(view);
  try { await route[1](view, params, path.match(route[0])); } catch (e) {
    if (my === renderSeq) view.innerHTML = `<div class="page"><div class="error-box" role="alert">${esc(e.message)}</div></div>`;
  }
  if (my === renderSeq) reveal(view);
}

function bindShell() {
  $$(".rail a").forEach((a) => a.addEventListener("click", () => $("#shell").classList.remove("open")));
  $("#menu").addEventListener("click", () => {
    const open = $("#shell").classList.toggle("open");
    $("#menu").setAttribute("aria-expanded", open);
  });
  $("#logout")?.addEventListener("click", async () => {
    try { await api("/api/auth/logout", { method: "POST" }); } catch { /* ignore */ }
    state.user = null;
    toast("Signed out");
    $("#root").innerHTML = "";
    location.hash = "#/";
  });
}

// Defence in depth: every form in this app is handled by script; block native submission everywhere
// so a slow-loading handler can never send form fields as URL query parameters.
document.addEventListener("submit", (e) => e.preventDefault(), true);

async function boot() {
  try { state.user = (await api("/api/auth/session")).user; } catch { state.user = null; }
  let lastUser = state.user?.id;
  window.addEventListener("hashchange", () => {
    if ((state.user?.id) !== lastUser) { lastUser = state.user?.id; $("#root").innerHTML = ""; }
    render();
  });
  render();
}
boot();
