// Discover: details panel (photos, crowd, reviews) beside a crowd heat map.
// Map colour: no colour where it is quiet, yellow where it is medium, red where it is crowded.
import { $, $$, out, api, esc, toast, hr, pct, MONTHS, levelPill, isoLocal, nextWeekday, state, whenLeafletReady, fmtDate } from "./core.js";
import { ICONS } from "./icons.js";

// Calibrated for leaflet.heat's blur (a point's rendered peak is below its value):
// Moderate (0.35+) renders yellow, High (0.65+) orange, At Capacity (0.9+) red.
const HEAT_GRADIENT = { 0.12: "#fff3a6", 0.25: "#ffd84a", 0.38: "#ffb43d", 0.5: "#ff8233", 0.62: "#f24a22", 0.78: "#d81b12" };
const MODES = [["now", "Now"], ["tomorrow", "Tomorrow"], ["sat", "Saturday"]];

function modeDate(mode) {
  const d = new Date();
  if (mode === "tomorrow") d.setDate(d.getDate() + 1);
  if (mode === "sat") return nextWeekday(6, 12);
  return d;
}
const photoCache = {};
const getPhoto = (kind, slug) => (photoCache[kind + slug] ||= api(`/api/${kind}/${slug}/photo`).catch(() => ({ available: false })));

export async function discover(el, params) {
  const now = new Date();
  const S = {
    mode: "now", hour: Math.min(22, Math.max(6, now.getHours())), dest: null, attr: null, attrs: [], map: null, heat: null,
    dots: null, points: [], forecast: null,
  };
  if (S.hour >= 21 || S.hour < 6) { S.mode = "tomorrow"; S.hour = 10; }
  const at = () => { const d = modeDate(S.mode); d.setHours(S.hour, 0, 0, 0); return isoLocal(d); };

  el.innerHTML = `<div class="discover">
    <div class="d-panel" id="d-panel" aria-live="polite"></div>
    <div class="d-map"><div id="d-map" role="region" aria-label="Crowd map"></div>
      <div class="when" id="d-when"></div>
      <div class="legend-box" aria-label="Map key"><span><i style="background:#e8ebe6;border:1px solid #c9ccc6"></i>Quiet</span><span><i style="background:#ffc23d"></i>Medium</span><span><i style="background:#e0261a"></i>Crowded</span></div>
      <a class="help" href="#/about" aria-label="How our crowd data works">?</a></div></div>`;

  // ---------------------------------------------------------------- map
  whenLeafletReady(() => {
    const box = $("#d-map", el);
    if (!window.L || !box) return;
    S.map = L.map(box, { zoomControl: true, scrollWheelZoom: matchMedia("(min-width: 1101px)").matches }).setView([22.6, 80.5], 5);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, className: "soft-tiles",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(S.map);
    S.dots = L.layerGroup().addTo(S.map);
    S.map.on("zoomend", () => S.heat && S.heat.setOptions(heatOpts()));
    refreshMap();
  });
  const heatOpts = () => {
    const z = S.map ? S.map.getZoom() : 5;
    const radius = z >= 13 ? 90 : z >= 11 ? 60 : z >= 8 ? 38 : 22;
    return { radius, blur: radius * 0.8, max: 1, minOpacity: 0.35, gradient: HEAT_GRADIENT };
  };
  async function refreshMap() {
    out("#d-when", el).textContent = new Date(at()).toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short", hour: "numeric" });
    const seq = (S.mapSeq = (S.mapSeq || 0) + 1);
    let r;
    try { r = await api(`/api/crowd/map?at=${encodeURIComponent(at())}`); } catch (e) { toast(e.message, true); return; }
    if (seq !== S.mapSeq) return; // a newer time was chosen while this was loading
    S.points = r.points;
    if (!S.map) return;
    const hot = r.points.filter((p) => p.heat > 0).map((p) => [p.lat, p.lon, p.heat]);
    if (window.L && L.heatLayer) {
      if (S.heat) S.heat.setLatLngs(hot), S.heat.setOptions(heatOpts());
      else S.heat = L.heatLayer(hot, heatOpts()).addTo(S.map);
    }
    S.dots.clearLayers();
    r.points.forEach((p) => {
      const sel = S.attr === p.slug;
      const m = L.circleMarker([p.lat, p.lon], { radius: sel ? 8 : 5, color: "#fff", weight: 2, fillColor: "#141414", fillOpacity: 1 })
        .bindTooltip(`${esc(p.name)} · ${esc(p.level)}`, { direction: "top" }).addTo(S.dots);
      m.on("click", () => (p.destination === S.dest?.slug ? selectAttraction(p.slug) : selectDestination(p.destination, p.slug)));
    });
    updateBadges();
    if (S.attr) showPopup();
  }
  function updateBadges() {
    (S.attrs || []).forEach((x) => {
      const p = S.points.find((pt) => pt.slug === x.slug);
      const badge = panel()?.querySelector(`[data-lv="${CSS.escape(x.slug)}"]`);
      if (badge && p) badge.innerHTML = levelPill(p.level);
    });
  }

  // ---------------------------------------------------------------- panel pieces
  const panel = () => $("#d-panel", el);
  const tabs = () => `<div class="tabs" role="tablist" aria-label="When">${MODES.map(([k, l]) =>
    `<button role="tab" aria-selected="${S.mode === k}" data-mode="${k}">${esc(l)}</button>`).join("")}</div>`;
  const search = () => `<form class="d-search" id="d-search" role="search"><label class="sr-only" for="d-q">Search a place</label>
    <input class="input" id="d-q" placeholder="Search a place, state or attraction" maxlength="60" autocomplete="off"><button class="btn">Search</button></form>`;
  const slider = () => `<div class="slider"><div class="top"><span>Time of visit</span><span class="bubble" id="d-hour-label">${esc(hr(S.hour))}</span></div>
    <label class="sr-only" for="d-hour">Hour of visit</label><input type="range" id="d-hour" min="6" max="22" step="1" value="${S.hour}" aria-valuetext="${esc(hr(S.hour))}">
    <div class="ticks"><span>6 AM</span><span>10 AM</span><span>2 PM</span><span>6 PM</span><span>10 PM</span></div></div>`;

  function bindCommon() {
    $$("[data-mode]", panel()).forEach((b) => b.addEventListener("click", () => {
      S.mode = b.dataset.mode;
      $$("[data-mode]", panel()).forEach((x) => x.setAttribute("aria-selected", x === b));
      changed();
    }));
    const r = $("#d-hour", panel());
    if (r) r.addEventListener("input", () => {
      S.hour = +r.value;
      out("#d-hour-label", el).textContent = hr(S.hour);
      r.setAttribute("aria-valuetext", hr(S.hour));
      clearTimeout(S.t); S.t = setTimeout(changed, 180);
    });
    $("#d-search", panel()).addEventListener("submit", async (e) => {
      e.preventDefault();
      const q = $("#d-q", panel()).value.trim();
      if (!q) return;
      try {
        const res = await api(`/api/destinations?q=${encodeURIComponent(q)}&limit=5`);
        if (!res.items.length) { toast(`No destination matches “${q}”`, true); return; }
        const hit = res.items[0];
        selectDestination(hit.slug);
      } catch (err) { toast(err.message, true); }
    });
  }
  function changed() {
    refreshMap();
    if (S.dest) renderAttractionDetails(); else renderRecommendations();
  }

  // ---------------------------------------------------------------- default: recommended places
  async function renderRecommendations() {
    const u = state.user || {};
    const travel = isoLocal(modeDate(S.mode)).slice(0, 10);
    if (!$("#rec-cards", panel())) {
      panel().innerHTML = `<section class="d-card"><h1>Discover India</h1><p class="note" style="margin-top:6px">Crowd forecasts for ${state.states?.length || 36} states and union territories. Pick a place, or start from our suggestions.</p>
        <div style="margin-top:16px">${tabs()}</div>${search()}
        <p class="label">Recommended for ${esc(fmtDate(travel))}</p><div class="photos" id="rec-cards"></div><p class="credit" id="rec-credit"></p></section>
        ${slider()}
        <section class="d-card"><h2>Why these places</h2><div id="rec-why" class="note" style="margin-top:8px">Loading…</div></section>`;
      bindCommon();
    }
    out("#rec-cards", el).innerHTML = `<p class="note">Finding quieter places…</p>`;
    try {
      const r = await api("/api/recommendations", { method: "POST", body: {
        interests: u.interests || [], budget: u.budget || "mid", group_type: u.group_type || "couple", days: 3, travel_date: travel, limit: 6,
        ...(u.home_lat ? { origin: { lat: u.home_lat, lon: u.home_lon } } : {}) } });
      out("#rec-cards", el).innerHTML = r.items.map((d) => `<button class="pcard" data-dest="${esc(d.slug)}" aria-pressed="false">
          <div class="img noimg" data-photo="${esc(d.slug)}"><span class="lv">${levelPill(d.crowd.level)}</span>${esc(d.state)}</div>
          <div class="nm">${esc(d.name)}</div></button>`).join("");
      out("#rec-why", el).innerHTML = `<div class="rows">${r.items.slice(0, 4).map((d) => `<div class="row" style="display:block"><strong>${esc(d.name)}</strong>
        <p class="meta">${esc(d.reasons.slice(0, 2).join(". "))}.</p></div>`).join("")}</div>`;
      $$("[data-dest]", panel()).forEach((b) => b.addEventListener("click", () => selectDestination(b.dataset.dest)));
      loadPhotos("destinations", r.items.map((d) => d.slug), "#rec-credit");
    } catch (e) { out("#rec-cards", el).innerHTML = `<p class="form-error">${esc(e.message)}</p>`; }
  }

  async function loadPhotos(kind, slugs, creditSel) {
    const credits = [];
    await Promise.all(slugs.map(async (slug) => {
      const ph = await getPhoto(kind, slug);
      const box = panel()?.querySelector(`[data-photo="${CSS.escape(slug)}"]`);
      if (!box || !ph.available) return;
      box.classList.remove("noimg");
      box.style.backgroundImage = `url("${ph.url.replace(/"/g, "")}")`;
      box.setAttribute("role", "img");
      box.setAttribute("aria-label", `Photo: ${ph.title}`);
      box.childNodes.forEach((n) => { if (n.nodeType === 3) n.textContent = ""; });
      credits.push(ph);
    }));
    const c = panel()?.querySelector(creditSel);
    if (c && credits.length) c.innerHTML = "Photos via Wikimedia Commons: " + credits.map((p) =>
      `<a href="${esc(p.source_page || p.article)}" target="_blank" rel="noopener">${esc(p.credit)}</a> (${esc(p.licence)})`).join(", ");
  }

  // ---------------------------------------------------------------- a destination
  async function selectDestination(slug, attrSlug = null) {
    let d;
    try { d = await api(`/api/destinations/${encodeURIComponent(slug)}`); } catch (e) { toast(e.message, true); return; }
    S.dest = d;
    S.attrs = d.attractions;
    S.attr = attrSlug || [...d.attractions].sort((a, b) => b.capacity - a.capacity)[0]?.slug;
    history.replaceState(null, "", `#/discover?d=${d.slug}`);
    if (S.map) {
      const pts = d.attractions.map((a) => [a.lat, a.lon]);
      if (pts.length > 1) S.map.flyToBounds(pts, { padding: [70, 70], maxZoom: 13, duration: 0.8 });
      else S.map.flyTo([d.lat, d.lon], 12);
    }
    const states = state.states || (await api("/api/states")).items;
    state.states = states;
    const sameState = (await api(`/api/destinations?state=${d.state.code}&limit=60&sort=name`)).items;
    panel().innerHTML = `
      <section class="d-card"><h1>${esc(d.name)}</h1><p class="note" style="margin-top:4px">${esc(d.state.name)} · best ${esc(d.best_months.slice(0, 4).map((m) => MONTHS[m - 1]).join(", "))} · about ₹${d.daily_cost.toLocaleString("en-IN")}/day</p>
        <div style="margin-top:16px">${tabs()}</div>${search()}
        <p class="label">Places</p>
        <div class="photos" id="attr-cards">${d.attractions.map((a) => `<button class="pcard" data-attr="${esc(a.slug)}" aria-pressed="${a.slug === S.attr}">
          <div class="img noimg" data-photo="${esc(a.slug)}"><span class="lv" data-lv="${esc(a.slug)}"></span>${esc(a.category)}</div><div class="nm">${esc(a.name)}</div></button>`).join("")}</div>
        <p class="credit" id="attr-credit"></p></section>
      ${slider()}
      <section class="d-card" aria-labelledby="cd-h"><h2 id="cd-h">Crowd details</h2><p class="note" id="cd-sub"></p>
        <div class="stats3" style="margin-top:14px" id="cd-stats"></div>
        <p class="label">Quietest times this week</p><div class="chips" id="cd-best"></div>
        <p class="note" id="cd-weather" style="margin-top:12px"></p>
        <p class="credit">Forecasts come from a model trained on demonstration data, not live counts. <a href="#/about">How it works</a></p></section>
      <section class="d-card" aria-labelledby="rv-h"><h2 id="rv-h">Reviews</h2><div id="rv-box" class="note">Loading reviews…</div></section>
      <section class="d-card"><div class="two">
        <label class="field">State<select id="d-state">${states.map((s) => `<option value="${esc(s.code)}" ${s.code === d.state.code ? "selected" : ""}>${esc(s.name)}</option>`).join("")}</select></label>
        <label class="field">Destination<select id="d-dest">${sameState.map((x) => `<option value="${esc(x.slug)}" ${x.slug === d.slug ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></label></div></section>
      <a class="big-action" href="#/plan?d=${esc(d.slug)}">Plan a trip to ${esc(d.name)}</a>
      <p style="text-align:center;margin-bottom:8px"><a href="#/d/${esc(d.slug)}">All details, forecasts and map for ${esc(d.name)}</a> · <button class="linkish" id="d-back">Back to suggestions</button></p>`;
    bindCommon();
    $$("[data-attr]", panel()).forEach((b) => b.addEventListener("click", () => selectAttraction(b.dataset.attr)));
    $("#d-state", panel()).addEventListener("change", async (e) => {
      const r = await api(`/api/destinations?state=${e.target.value}&limit=60&sort=name`);
      if (r.items.length) selectDestination(r.items[0].slug);
    });
    $("#d-dest", panel()).addEventListener("change", (e) => selectDestination(e.target.value));
    $("#d-back", panel()).addEventListener("click", () => {
      S.dest = null; S.attr = null;
      history.replaceState(null, "", "#/discover");
      if (S.map) { S.map.closePopup(); S.map.flyTo([22.6, 80.5], 5, { duration: 0.8 }); }
      panel().innerHTML = "";
      renderRecommendations();
    });
    loadPhotos("attractions", d.attractions.map((a) => a.slug), "#attr-credit");
    loadReviews(d);
    api(`/api/destinations/${d.slug}/weather`).then((w) => {
      out("#cd-weather", el).textContent = w.available
        ? `Weather now: ${Math.round(w.current.temp_c)}°C, ${w.current.condition} (live, Open-Meteo). ${w.suggestions[0] || ""}`
        : `Weather unavailable: ${w.reason}`;
    }).catch(() => {});
    refreshMap();
    renderAttractionDetails();
  }

  function selectAttraction(slug) {
    S.attr = slug;
    $$("[data-attr]", panel()).forEach((b) => b.setAttribute("aria-pressed", b.dataset.attr === slug));
    const a = S.attrs.find((x) => x.slug === slug);
    if (a && S.map) S.map.flyTo([a.lat, a.lon], Math.max(S.map.getZoom(), 13), { duration: 0.6 });
    renderAttractionDetails();
    refreshMap();
  }

  async function renderAttractionDetails() {
    if (!S.dest || !S.attr) return;
    const a = S.attrs.find((x) => x.slug === S.attr);
    const date = at().slice(0, 10);
    const seq = (S.detailSeq = (S.detailSeq || 0) + 1);
    let f;
    try { f = await api(`/api/attractions/${S.attr}/forecast?date=${date}`); } catch (e) { toast(e.message, true); return; }
    if (seq !== S.detailSeq) return; // ignore a slower, older request (different time or place)
    S.forecast = f;
    const h = f.hourly.find((x) => x.hour === S.hour);
    const quiet = f.hourly.filter((x) => x.hour >= 7 && x.hour <= 20).reduce((m, x) => (x.util < m.util ? x : m), f.hourly[0] || { hour: 0, util: 0, level: "Low" });
    const level = h ? h.level : "Closed";
    out("#cd-sub", el).textContent = `${a.name}, ${new Date(at()).toLocaleString("en-IN", { weekday: "long", hour: "numeric" })}`;
    out("#cd-stats", el).innerHTML = `
      <div class="stat ${h ? h.level.replace(/\s+/g, "-") : ""}"><div class="ico">${ICONS.people}</div><div><span>People ${S.mode === "now" && S.hour === new Date().getHours() ? "now" : "then"}</span><br><b>${h ? "~" + h.visitors.toLocaleString("en-IN") : "Closed"}</b></div></div>
      <div class="stat ${h ? h.level.replace(/\s+/g, "-") : ""}"><div class="ico">${ICONS.gauge}</div><div><span>${esc(level)}</span><br><b>${h ? pct(h.util) : "–"}</b></div></div>
      <div class="stat"><div class="ico">${ICONS.clock}</div><div><span>Quietest that day</span><br><b>${f.hourly.length ? esc(hr(quiet.hour)) : "–"}</b></div></div>`;
    out("#cd-best", el).innerHTML = f.best_times.map((b) => `<span class="chip" style="display:inline-flex;align-items:center;gap:6px">${esc(fmtDate(b.date))} ${esc(hr(b.hour))} ${levelPill(b.level)}</span>`).join("");
    updateBadges();
    showPopup();
  }

  function showPopup() {
    if (!S.map || !S.attr || !S.forecast || S.forecast.attraction.slug !== S.attr) return;
    const a = S.attrs.find((x) => x.slug === S.attr);
    if (!a) return;
    const f = S.forecast, h = f.hourly.find((x) => x.hour === S.hour);
    const quiet = f.hourly.filter((x) => x.hour >= 7 && x.hour <= 20).reduce((m, x) => (x.util < m.util ? x : m), f.hourly[0] || { hour: 0 });
    S.pop ||= L.popup({ className: "stat-pop", closeButton: false, autoClose: false, closeOnClick: false, autoPan: true, autoPanPadding: [24, 24], offset: [0, -6], maxWidth: 420 });
    S.pop
      .setLatLng([a.lat, a.lon])
      .setContent(`<div class="pop3"><div><b>${h ? "~" + h.visitors.toLocaleString("en-IN") : "Closed"}</b><span>People at ${esc(hr(S.hour))}</span></div>
        <div><b>${h ? pct(h.util) : "–"}</b><span>${h ? esc(h.level) : "Not open then"}</span></div>
        <div><b>${f.hourly.length ? esc(hr(quiet.hour)) : "–"}</b><span>Quietest</span></div></div>
        <p class="pop-name">${esc(a.name)} · <a href="#/d/${esc(S.dest.slug)}">Details</a></p>`)
      .openOn(S.map);
  }

  async function loadReviews(d) {
    try {
      const r = await api(`/api/destinations/${d.slug}/reviews`);
      const s = r.summary;
      out("#rv-box", el).innerHTML = `<p style="color:var(--text);font-size:1.6rem">${s.average ?? "–"} <span class="note">/ 5 from ${s.count} reviews${s.demo_count ? ` (${s.demo_count} demo)` : ""}</span></p>
        <p>${s.sentiment.positive} positive · ${s.sentiment.neutral} neutral · ${s.sentiment.negative} negative</p>
        ${s.complaints.length ? `<p style="margin-top:4px">Common complaints: ${s.complaints.slice(0, 3).map((c) => esc(c.label)).join(", ")}</p>` : ""}
        ${r.items.slice(0, 2).map((x) => `<div class="review-mini"><strong style="color:var(--text)">${esc(x.author)}</strong> ${x.source === "demo" ? '<span class="tag demo">Demo</span>' : ""} · ${x.rating}/5<p style="color:var(--text)">${esc(x.text)}</p></div>`).join("")}
        <p style="margin-top:10px"><a href="#/d/${esc(d.slug)}">Read all and write a review</a></p>`;
    } catch (e) { out("#rv-box", el).textContent = e.message; }
  }

  // ---------------------------------------------------------------- start
  const start = params.get("d");
  if (start) selectDestination(start); else renderRecommendations();
}
