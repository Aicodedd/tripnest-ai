// Traveller screens. Each view receives (el, params) and renders into el.
import {
  $, $$, out, api, esc, toast, hr, hrRange, pct, inr, MONTHS, fmtDate, fmtWhen, levelPill, cap, state, isoLocal, todayISO,
  nextWeekday, provenanceBox, loading, errorBox, empty, forecastChart, lineChart, barRow, makeMap, dot, whenLeafletReady,
} from "./core.js";

const GROUPS = [["solo", "Solo"], ["couple", "Couple"], ["family", "Family with children"], ["elders", "With elderly travellers"], ["friends", "Friends"]];
const BUDGETS = [["low", "Low (up to ₹2,000/day)"], ["mid", "Mid (up to ₹3,500/day)"], ["high", "High (up to ₹7,000/day)"]];
const INTERESTS = ["heritage", "spiritual", "beach", "nature", "wildlife", "waterfall", "lake", "viewpoint", "adventure", "market", "food", "museum", "trek", "garden", "photography", "quiet"];

export async function loadLookups() {
  if (!state.states) state.states = (await api("/api/states")).items;
  if (!state.categories) state.categories = (await api("/api/categories")).items;
}
const requireLogin = (el, what) => {
  el.innerHTML = `<div class="page">${empty("Sign in to " + what, "Your saved data is private to your account.",
    `<p style="margin-top:12px"><a class="btn" href="#/login?next=${encodeURIComponent(location.hash)}">Sign in</a> <a class="btn quiet" href="#/register">Create account</a></p>`)}</div>`;
};
const chipGroup = (name, values, selected = []) => `<div class="chips" role="group" aria-label="${esc(name)}">${values.map((v) =>
  `<button type="button" class="chip" data-v="${esc(v)}" aria-pressed="${selected.includes(v)}">${esc(cap(v))}</button>`).join("")}</div>`;
const chipValues = (root) => $$(".chip[aria-pressed=true]", root).map((b) => b.dataset.v);
const bindChips = (root) => $$(".chip", root).forEach((b) => b.addEventListener("click", () =>
  b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") !== "true")));
const options = (pairs, sel) => pairs.map(([v, l]) => `<option value="${esc(v)}" ${v === sel ? "selected" : ""}>${esc(l)}</option>`).join("");
const destCard = (d) => `<a class="dcard" href="#/d/${esc(d.slug)}">
  <span class="note">${esc(d.state.name)}</span><h3>${esc(d.name)}</h3><p>${esc(d.description)}</p>
  <div class="foot"><span class="tag">${esc(cap(d.budget))} budget</span><span class="tag">${esc(d.attraction_count)} places</span>
  <span class="tag">Best ${esc(d.best_months.slice(0, 3).map((m) => MONTHS[m - 1]).join(", "))}${d.best_months.length > 3 ? "…" : ""}</span></div></a>`;

// ------------------------------------------------------------------ home
export async function home(el) {
  el.innerHTML = loading("Loading your TripNest");
  try {
    const sat = isoLocal(nextWeekday(6, 12)).slice(0, 10);
    const [hl, favs, trips] = await Promise.all([
      api(`/api/crowd/highlights?date=${sat}&limit=6`),
      state.user ? api("/api/me/favourites") : Promise.resolve({ items: [] }),
      state.user ? api("/api/itineraries") : Promise.resolve({ items: [] }),
    ]);
    await loadLookups();
    const first = hl.items[0];
    const name = state.user ? state.user.name.split(" ")[0] : "traveller";
    const fact = first ? `${first.attraction}: quietest at ${hr(first.quietest.hour)} Saturday.` : "";
    el.innerHTML = `<div class="page">
      <h1 class="greeting">Hello, ${esc(name)}. ${esc(fact)}</h1>
      <p class="greeting-sub">${esc(new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" }))}. Crowd figures are forecasts from a model trained on demonstration data.</p>
      <div class="grid12">
        <div class="tile s3"><span>States and union territories</span><b>${state.states.length}</b><span>All covered</span></div>
        <div class="tile s3"><span>Destinations</span><b>${state.states.reduce((a, s) => a + s.destinations, 0)}</b><span><a href="#/explore">Browse all</a></span></div>
        <div class="tile s3"><span>Your saved trips</span><b>${trips.items.length}</b><span><a href="#/plan">Plan a new trip</a></span></div>
        <div class="tile s3"><span>Your favourites</span><b>${favs.items.length}</b><span>${state.user ? '<a href="#/profile">Manage</a>' : '<a href="#/login">Sign in to save</a>'}</span></div>
        <section class="panel s8"><header><h2>Saturday at the busiest places</h2><a href="#/compare">Compare crowds</a></header>
          <div class="rows">${hl.items.map((x) => `<a class="row" href="#/d/${esc(x.destination.slug)}">
            <div><strong>${esc(x.attraction)}</strong><div class="meta">${esc(x.destination.name)}, ${esc(x.state)}</div></div>
            <div class="meta">Busiest ${esc(hr(x.peak.hour))} ${levelPill(x.peak.level)} · quietest ${esc(hr(x.quietest.hour))} ${levelPill(x.quietest.level)}</div></a>`).join("")}</div>
          ${provenanceBox(hl.provenance)}</section>
        <section class="panel s4"><header><h2>Your trips</h2><a href="#/trips">View all</a></header>
          ${trips.items.length ? `<div class="rows">${trips.items.slice(0, 4).map((t) => `<a class="row" href="#/trips/${t.id}"><div><strong>${esc(t.title)}</strong><div class="meta">${esc(fmtDate(t.start_date))} · ${t.days} day${t.days > 1 ? "s" : ""}</div></div></a>`).join("")}</div>`
            : empty("No trips yet", state.user ? "Build a crowd-aware day plan and save it here." : "Sign in to save plans.", '<p style="margin-top:10px"><a class="btn small" href="#/plan">Plan a trip</a></p>')}
          <header style="margin-top:20px"><h2>Favourites</h2></header>
          ${favs.items.length ? `<div class="rows">${favs.items.map((f) => `<a class="row" href="#/d/${esc(f.slug)}"><strong>${esc(f.name)}</strong><span class="meta">${esc(f.state)}</span></a>`).join("")}</div>`
            : `<p class="note">Tap “Save to favourites” on any destination.</p>`}
        </section>
      </div></div>`;
  } catch (e) { el.innerHTML = errorBox(e); }
}

// ------------------------------------------------------------------ explore
export async function explore(el, params) {
  await loadLookups();
  const p = { q: params.get("q") || "", state: params.get("state") || "", category: params.get("category") || "",
              budget: params.get("budget") || "", month: params.get("month") || "", page: +(params.get("page") || 1) };
  el.innerHTML = `<div class="page">
    <div class="page-head"><div><h1>Explore India</h1><p>Search ${state.states.length} states and union territories. Every destination has hour-by-hour crowd forecasts.</p></div></div>
    <form class="form-grid panel" id="filters" role="search">
      <label class="field">Search<input name="q" value="${esc(p.q)}" placeholder="Taj Mahal, Kerala, waterfall" maxlength="60"></label>
      <label class="field">State or UT<select name="state"><option value="">All</option>${options(state.states.map((s) => [s.code, s.name]), p.state)}</select></label>
      <label class="field">Category<select name="category"><option value="">Any</option>${options(state.categories.map((c) => [c.name, cap(c.name)]), p.category)}</select></label>
      <label class="field">Budget<select name="budget"><option value="">Any</option>${options(BUDGETS, p.budget)}</select></label>
      <label class="field">Travel month<select name="month"><option value="">Any</option>${options(MONTHS.map((m, i) => [String(i + 1), m]), p.month)}</select></label>
      <div><button class="btn" type="submit">Show destinations</button></div>
    </form>
    <div id="results" style="margin-top:24px">${loading("Finding destinations")}</div></div>`;
  $("#filters", el).addEventListener("submit", (e) => {
    e.preventDefault();
    const f = new FormData(e.target), qs = new URLSearchParams();
    for (const [k, v] of f) if (v) qs.set(k, v);
    location.hash = "#/explore" + (qs.toString() ? "?" + qs : "");
  });
  const qs = new URLSearchParams({ limit: 24, page: p.page });
  ["q", "state", "category", "budget", "month"].forEach((k) => p[k] && qs.set(k, p[k]));
  try {
    const r = await api("/api/destinations?" + qs);
    const res = $("#results", el);
    if (!r.items.length) {
      res.innerHTML = empty("No destinations match", "Try a broader search or clear a filter.", '<p style="margin-top:10px"><a class="btn small quiet" href="#/explore">Clear filters</a></p>');
      return;
    }
    const pages = Math.ceil(r.total / r.limit);
    const link = (n) => { const q2 = new URLSearchParams(params); q2.set("page", n); return "#/explore?" + q2; };
    res.innerHTML = `<p class="note" style="margin-bottom:12px">${r.total} destination${r.total === 1 ? "" : "s"}</p>
      <div class="cards">${r.items.map(destCard).join("")}</div>
      ${pages > 1 ? `<nav aria-label="Pages" style="display:flex;gap:8px;margin-top:20px">${p.page > 1 ? `<a class="btn small quiet" href="${link(p.page - 1)}">Previous</a>` : ""}<span class="note" style="align-self:center">Page ${p.page} of ${pages}</span>${p.page < pages ? `<a class="btn small quiet" href="${link(p.page + 1)}">Next</a>` : ""}</nav>` : ""}`;
  } catch (e) { out("#results", el).innerHTML = errorBox(e); }
}

// ------------------------------------------------------------------ destination detail
export async function destination(el, params, slug) {
  el.innerHTML = loading("Loading destination");
  let d;
  try { d = await api(`/api/destinations/${encodeURIComponent(slug)}`); } catch (e) {
    el.innerHTML = e.status === 404 ? empty("Destination not found", "It may have been removed.", '<a href="#/explore">Back to explore</a>') : errorBox(e);
    return;
  }
  const favs = state.user ? (await api("/api/me/favourites")).items.map((f) => f.slug) : [];
  let isFav = favs.includes(d.slug);
  let at = params.get("at") || isoLocal(new Date());
  let selected = d.attractions[0]?.slug;
  el.innerHTML = `<div class="page">
    <p class="crumbs"><a href="#/explore">Explore</a> / <a href="#/explore?state=${esc(d.state.code)}">${esc(d.state.name)}</a></p>
    <div class="page-head"><div><h1>${esc(d.name)}</h1><p>${esc(d.description)}</p></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn quiet" id="fav">${isFav ? "Saved to favourites" : "Save to favourites"}</button>
      <a class="btn" href="#/plan?d=${esc(d.slug)}">Plan a trip here</a></div></div>
    <div class="grid12">
      <section class="panel s8" aria-labelledby="now-h"><header><h2 id="now-h">Crowds at each place</h2>
        <div class="chips" role="group" aria-label="When">
          <button class="chip" data-at="now">Now</button><button class="chip" data-at="tomorrow">Tomorrow 10 AM</button>
          <button class="chip" data-at="sat">Saturday 4 PM</button>
          <label class="sr-only" for="at-input">Date and time</label><input class="input" style="width:auto;min-height:36px" type="datetime-local" id="at-input" value="${esc(at)}"></div></header>
        <div id="crowd">${loading()}</div></section>
      <section class="panel s4" aria-labelledby="w-h"><header><h2 id="w-h">Weather</h2></header><div id="weather">${loading()}</div></section>
      <section class="panel s12" aria-labelledby="f-h"><header><h2 id="f-h">Hourly forecast</h2>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><label class="sr-only" for="attr-sel">Attraction</label><select class="input" style="width:auto" id="attr-sel">${d.attractions.map((a) => `<option value="${esc(a.slug)}">${esc(a.name)}</option>`).join("")}</select>
        <label class="sr-only" for="f-date">Date</label><input class="input" style="width:auto" type="date" id="f-date" value="${esc(at.slice(0, 10))}"></div></header>
        <div id="forecast">${loading()}</div></section>
      <section class="panel s6" aria-labelledby="h-h"><header><h2 id="h-h">Usual pattern</h2><span class="sub">Last 8 weeks and the past year</span></header><div id="history">${loading()}</div></section>
      <section class="panel s6" aria-labelledby="m-h"><header><h2 id="m-h">Map</h2></header><div class="map" id="dmap"></div></section>
      <section class="panel s7" aria-labelledby="r-h"><header><h2 id="r-h">Reviews</h2><span class="sub">${d.rating.count} reviews${d.rating.average ? ` · ${d.rating.average} / 5` : ""}</span></header><div id="reviews">${loading()}</div></section>
      <section class="panel s5" aria-labelledby="i-h"><header><h2 id="i-h">Travel information</h2></header>
        <p><strong>Getting there.</strong> ${esc(d.how_to_reach)}</p>
        <p style="margin-top:10px"><strong>Best months.</strong> ${esc(d.best_months.map((m) => MONTHS[m - 1]).join(", "))}. Plan for ${d.min_days}+ day${d.min_days > 1 ? "s" : ""}; about ${esc(inr(d.daily_cost))} per person per day (indicative).</p>
        <p style="margin-top:10px"><strong>Facilities.</strong> ${esc(d.facilities.join(", "))}.</p>
        <h3 style="font-size:1rem;font-weight:600;margin:20px 0 8px">Local stays and businesses</h3>
        <div class="rows">${d.listings.map((l) => `<div class="row"><div><strong>${esc(l.name)}</strong><div class="meta">${esc(cap(l.kind))} · ${esc(l.description)}</div></div>
          ${l.source === "demo" ? '<span class="tag demo">Demo listing</span>' : l.verified ? '<span class="tag live">Verified</span>' : '<span class="tag">Unverified</span>'}</div>`).join("") || '<p class="note">No listings yet.</p>'}</div>
        <p class="note" style="margin-top:10px">${esc(d.provenance.catalogue.note)} Updated ${esc(fmtWhen(d.updated_at))}.</p></section>
    </div></div>`;

  $("#fav", el).addEventListener("click", async () => {
    if (!state.user) { location.hash = "#/login?next=" + encodeURIComponent(location.hash); return; }
    try {
      await api(`/api/me/favourites/${d.slug}`, { method: isFav ? "DELETE" : "POST" });
      isFav = !isFav;
      out("#fav", el).textContent = isFav ? "Saved to favourites" : "Save to favourites";
      toast(isFav ? "Saved to favourites" : "Removed from favourites");
    } catch (e) { toast(e.message, true); }
  });

  const loadCrowd = async () => {
    out("#crowd", el).innerHTML = loading();
    try {
      const c = await api(`/api/destinations/${d.slug}/crowd?at=${encodeURIComponent(at)}`);
      out("#crowd", el).innerHTML = `<p class="note" style="margin-bottom:10px">Forecast for ${esc(fmtWhen(c.at))}. Overall ${levelPill(c.overall.level)}</p>
        <div class="rows">${c.attractions.map((a) => `<div class="row"><div><strong>${esc(a.name)}</strong>
          <div class="meta">${a.open ? `~${a.visitors.toLocaleString("en-IN")} people (${pct(a.util)} of assumed capacity)${a.trend ? ` · ${a.trend}` : ""}${a.reports ? ` · ${a.reports} traveller report${a.reports > 1 ? "s" : ""}` : ""}` : `Opens ${esc(hrRange(a.hours[0], a.hours[1]))}`}${a.sensitive ? " · fragile site, stricter limits" : ""}</div></div>
          <div style="display:flex;gap:8px;align-items:center">${levelPill(a.level)}${a.open ? `<button class="btn small quiet" data-report="${esc(a.slug)}" data-name="${esc(a.name)}">Report crowd</button>` : ""}</div></div>`).join("")}</div>
        ${provenanceBox(c.provenance)}`;
      $$("[data-report]", $("#crowd", el)).forEach((b) => b.addEventListener("click", () => reportDialog(b.dataset.report, b.dataset.name)));
    } catch (e) { out("#crowd", el).innerHTML = errorBox(e); }
  };
  const reportDialog = (aslug, name) => {
    if (!state.user) { location.hash = "#/login?next=" + encodeURIComponent(location.hash); return; }
    const box = document.createElement("form");
    box.className = "panel";
    box.style.marginTop = "12px";
    box.innerHTML = `<p><strong>How crowded is ${esc(name)} right now?</strong></p>
      ${chipGroup("Crowd level", ["low", "moderate", "high", "packed"])}
      <label class="field" style="margin-top:10px">Note (optional)<input name="note" maxlength="300"></label>
      <p style="margin-top:10px;display:flex;gap:8px"><button class="btn small" type="submit">Send report</button><button class="btn small quiet" type="button" data-cancel>Cancel</button></p>`;
    $("#crowd", el).prepend(box);
    $$(".chip", box).forEach((b) => b.addEventListener("click", () => $$(".chip", box).forEach((x) => x.setAttribute("aria-pressed", x === b))));
    box.querySelector("[data-cancel]").addEventListener("click", () => box.remove());
    box.addEventListener("submit", async (e) => {
      e.preventDefault();
      const level = chipValues(box)[0];
      if (!level) { toast("Choose a crowd level", true); return; }
      try {
        await api(`/api/attractions/${aslug}/reports`, { method: "POST", body: { level, note: box.note.value || null, at } });
        toast("Report sent. Thank you!");
        loadCrowd();
      } catch (err) { toast(err.message, true); }
    });
  };
  const loadForecast = async () => {
    out("#forecast", el).innerHTML = loading();
    const date = $("#f-date", el).value || todayISO();
    try {
      const f = await api(`/api/attractions/${selected}/forecast?date=${date}`);
      const a = f.attraction;
      out("#forecast", el).innerHTML = `<div class="grid12"><div class="s8">${forecastChart(f.hourly, { label: `${a.name} on ${date}` })}
          <div class="legend"><span><i style="background:#3d0012"></i>Forecast</span><span><i style="background:#f3c5db"></i>Likely range (80%)</span><span>Dashed lines: Moderate 40%, High 70%, At capacity 90% of assumed capacity${a.sensitive ? " (stricter 25/50/70% for this fragile site)" : ""}</span></div></div>
        <div class="s4"><p><strong>${esc(a.name)}</strong></p><p class="note">${esc(hrRange(a.open_hour, a.close_hour))} · ${a.fee ? esc(inr(a.fee)) + " entry (indicative)" : "Free entry (indicative)"} · about ${a.visit_min} min</p>
          ${f.peak ? `<p style="margin-top:12px">Busiest at <strong>${esc(hr(f.peak.hour))}</strong> ${levelPill(f.peak.level)}, about ${f.peak.visitors.toLocaleString("en-IN")} people. Chance of reaching capacity then: ${pct(f.peak.p_exceed)}.</p>` : ""}
          ${f.calendar.holiday ? `<p class="note" style="margin-top:8px">${esc(f.calendar.name)}: holiday crowds expected.</p>` : ""}
          ${f.in_season ? "" : '<p class="note" style="margin-top:8px">Outside the usual best season, so quieter.</p>'}
          <h3 style="font-size:1rem;font-weight:600;margin:16px 0 8px">Quietest times this week</h3>
          <div class="rows">${f.best_times.map((b) => `<div class="row"><span>${esc(fmtDate(b.date))}, ${esc(hr(b.hour))}</span>${levelPill(b.level)}</div>`).join("")}</div></div></div>
        <p class="note" style="margin-top:8px">${esc(f.capacity.note)} ${esc(f.uncertainty)}</p>`;
    } catch (e) { out("#forecast", el).innerHTML = errorBox(e); }
  };
  const loadHistory = async () => {
    try {
      const h = await api(`/api/attractions/${selected}/history`);
      out("#history", el).innerHTML = `<p class="note">Busiest hour by weekday (share of assumed capacity)</p>${barRow(h.by_weekday.map((w) => w.peak_util), h.by_weekday.map((w) => w.weekday))}
        <p class="note" style="margin-top:12px">Average daily peak by month</p>${barRow(h.by_month.map((m) => m.avg_peak_util), h.by_month.map((m) => MONTHS[m.month - 1]))}
        <p class="note" style="margin-top:8px">${esc(h.provenance.note)}</p>`;
    } catch (e) { out("#history", el).innerHTML = errorBox(e); }
  };
  $$("[data-at]", el).forEach((b) => b.addEventListener("click", () => {
    const k = b.dataset.at, now = new Date();
    if (k === "now") at = isoLocal(now);
    if (k === "tomorrow") { const t = new Date(now); t.setDate(t.getDate() + 1); t.setHours(10, 0, 0, 0); at = isoLocal(t); }
    if (k === "sat") at = isoLocal(nextWeekday(6, 16));
    $("#at-input", el).value = at;
    loadCrowd();
  }));
  $("#at-input", el).addEventListener("change", (e) => { if (e.target.value) { at = e.target.value; loadCrowd(); } });
  $("#attr-sel", el).addEventListener("change", (e) => { selected = e.target.value; loadForecast(); loadHistory(); });
  $("#f-date", el).addEventListener("change", loadForecast);
  loadCrowd(); loadForecast(); loadHistory();

  api(`/api/destinations/${d.slug}/weather`).then((w) => {
    if (!w.available) { out("#weather", el).innerHTML = empty("Weather unavailable", w.reason); return; }
    out("#weather", el).innerHTML = `<p style="font-size:2.4rem;letter-spacing:-0.03em">${Math.round(w.current.temp_c)}°C</p>
      <p>${esc(w.current.condition)} <span class="tag live">Live</span></p>
      <div class="rows" style="margin-top:12px">${w.daily.slice(0, 5).map((x) => `<div class="row"><span>${esc(fmtDate(x.date))}</span><span class="meta">${esc(x.condition)} · ${Math.round(x.min_c)}–${Math.round(x.max_c)}°C · rain ${x.rain_chance ?? "–"}%</span></div>`).join("")}</div>
      <ul style="margin:12px 0 0;padding-left:18px">${w.suggestions.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>
      <p class="note" style="margin-top:8px">${esc(w.source)}, fetched ${esc(fmtWhen(w.fetched_at))}.</p>`;
  }).catch((e) => (out("#weather", el).innerHTML = errorBox(e)));

  whenLeafletReady(() => {
    const map = makeMap($("#dmap", el), { center: [d.lat, d.lon], zoom: 11 });
    if (!map) return;
    const pts = d.attractions.map((a) => [a.lat, a.lon]);
    d.attractions.forEach((a) => dot(map, a.lat, a.lon, { popup: `<strong>${esc(a.name)}</strong><br>${esc(cap(a.category))} · ${esc(hrRange(a.open_hour, a.close_hour))}` }));
    if (pts.length > 1) map.fitBounds(pts, { padding: [30, 30] });
  });

  loadReviews(d, el);
}

async function loadReviews(d, el) {
  const box = $("#reviews", el);
  try {
    const r = await api(`/api/destinations/${d.slug}/reviews`);
    const s = r.summary;
    box.innerHTML = `
      <p>${s.sentiment.positive} positive · ${s.sentiment.neutral} neutral · ${s.sentiment.negative} negative${s.demo_count ? ` <span class="tag demo">${s.demo_count} demo reviews</span>` : ""}</p>
      ${s.complaints.length ? `<p class="note" style="margin-top:6px">Most mentioned problems: ${s.complaints.map((c) => `${esc(c.label)} (${c.count})`).join(", ")}</p>` : ""}
      ${state.user ? `<form id="rv-form" class="form-grid" style="margin:16px 0">
          <label class="field">Rating<select name="rating">${[5, 4, 3, 2, 1].map((n) => `<option value="${n}">${n} / 5</option>`).join("")}</select></label>
          <label class="field" style="grid-column:1/-1">Your review<textarea name="text" minlength="10" maxlength="1500" required placeholder="What was it like? Mention crowds, cleanliness, parking, staff…" aria-describedby="rv-hint"></textarea><span class="hint" id="rv-hint">10 to 1,500 characters.</span></label>
          <div><button class="btn" type="submit">Post review</button></div></form>`
        : `<p style="margin:14px 0"><a href="#/login?next=${encodeURIComponent(location.hash)}">Sign in</a> to write a review.</p>`}
      <div class="rows">${r.items.map((x) => `<div class="row" style="display:block">
        <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><strong>${esc(x.author)}</strong>
          <span>${x.source === "demo" ? '<span class="tag demo">Demo</span> ' : ""}<span class="pill ${x.sentiment === "positive" ? "lv-Low" : x.sentiment === "negative" ? "lv-High" : "lv-Closed"}">${esc(cap(x.sentiment))}</span> ${x.rating}/5</span></div>
        <p style="margin-top:6px">${esc(x.text)}</p>
        <p class="meta" style="margin-top:4px">${esc(fmtDate(x.created_at.slice(0, 10)))}${x.aspects.length ? " · " + x.aspects.map((a) => `${esc(a.label)}: ${esc(a.sentiment)}`).join(", ") : ""}
        ${state.user && x.source === "user" ? ` · <button class="linkish" data-flag="${x.id}">Report</button>` : ""}</p></div>`).join("")}</div>
      <p class="note" style="margin-top:8px">${esc(r.method)}</p>`;
    const f = $("#rv-form", el);
    if (f) f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = f.querySelector("button");
      btn.disabled = true;
      try {
        const res = await api(`/api/destinations/${d.slug}/reviews`, { method: "POST", body: { rating: +f.rating.value, text: f.text.value } });
        toast(`Review posted (read as ${res.sentiment})`);
        loadReviews(d, el);
      } catch (err) { toast(err.message, true); btn.disabled = false; }
    });
    $$("[data-flag]", box).forEach((b) => b.addEventListener("click", () => flagContent("review", +b.dataset.flag)));
  } catch (e) { box.innerHTML = errorBox(e); }
}

export async function flagContent(type, id) {
  const reason = prompt("Why should a moderator look at this? (3–300 characters)");
  if (!reason) return;
  try {
    await api("/api/content-reports", { method: "POST", body: { target_type: type, target_id: id, reason } });
    toast("Reported. A moderator will review it.");
  } catch (e) { toast(e.message, true); }
}

// ------------------------------------------------------------------ map
export async function mapView(el) {
  el.innerHTML = `<div class="page"><div class="page-head"><div><h1>Map of destinations</h1><p>Every catalogued destination across India. Select a dot for details.</p></div></div>
    <div class="map tall" id="bigmap"></div><p class="note" style="margin-top:8px">Positions are approximate. Map © OpenStreetMap contributors.</p></div>`;
  try {
    const r = await api("/api/destinations?limit=60");
    const r2 = r.total > 60 ? await api("/api/destinations?limit=60&page=2") : { items: [] };
    whenLeafletReady(() => {
      const map = makeMap($("#bigmap", el));
      if (!map) return;
      [...r.items, ...r2.items].forEach((d) => dot(map, d.lat, d.lon, { radius: 7, popup: `<strong>${esc(d.name)}</strong><br>${esc(d.state.name)}<br><a href="#/d/${esc(d.slug)}">Open forecasts</a>` }));
    });
  } catch (e) { el.innerHTML = errorBox(e); }
}

// ------------------------------------------------------------------ compare
export async function compare(el, params) {
  const all = [...(await api("/api/destinations?limit=60")).items, ...(await api("/api/destinations?limit=60&page=2")).items];
  const chosen = (params.get("slugs") || "goa,puducherry,mahabalipuram").split(",").filter(Boolean);
  const date = params.get("date") || isoLocal(nextWeekday(6, 12)).slice(0, 10);
  el.innerHTML = `<div class="page"><div class="page-head"><div><h1>Compare crowds</h1><p>Pick up to five destinations and a day to see whose crowds peak when.</p></div></div>
    <form class="panel form-grid" id="cmp">
      ${[0, 1, 2, 3, 4].map((i) => `<label class="field">Destination ${i + 1}<select name="s${i}"><option value="">None</option>${options(all.map((d) => [d.slug, d.name]), chosen[i] || "")}</select></label>`).join("")}
      <label class="field">Day<input type="date" name="date" value="${esc(date)}"></label><div><button class="btn">Compare</button></div></form>
    <section class="panel" style="margin-top:16px"><header><h2>Share of assumed capacity, by hour</h2></header><div id="cmp-out">${loading()}</div></section></div>`;
  $("#cmp", el).addEventListener("submit", (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const slugs = [0, 1, 2, 3, 4].map((i) => f.get("s" + i)).filter(Boolean);
    if (!slugs.length) { toast("Choose at least one destination", true); return; }
    location.hash = `#/compare?slugs=${[...new Set(slugs)].join(",")}&date=${f.get("date")}`;
  });
  try {
    const r = await api(`/api/crowd/compare?slugs=${encodeURIComponent(chosen.join(","))}&date=${date}`);
    out("#cmp-out", el).innerHTML = lineChart(r.items.map((x) => ({ name: x.name, points: x.hourly }))) +
      `<div class="rows" style="margin-top:16px">${r.items.map((x) => `<a class="row" href="#/d/${esc(x.slug)}"><strong>${esc(x.name)}</strong>
        <span class="meta">${x.peak ? `Busiest ${esc(hr(x.peak.hour))} ${levelPill(x.peak.level)}` : "Closed"}${x.quietest ? ` · quietest daytime ${esc(hr(x.quietest.hour))} ${levelPill(x.quietest.level)}` : ""}</span></a>`).join("")}</div>${provenanceBox(r.provenance)}`;
  } catch (e) { out("#cmp-out", el).innerHTML = errorBox(e); }
}

// ------------------------------------------------------------------ recommendations
export async function recommend(el) {
  const u = state.user || {};
  el.innerHTML = `<div class="page"><div class="page-head"><div><h1>Where should I go?</h1><p>Tell us what you like. We rank destinations by interest, predicted crowds, budget, season, distance and who is travelling, and explain every pick.</p></div></div>
    <form class="panel" id="rec" style="display:grid;gap:16px">
      <div><p class="field" style="font-weight:500;margin-bottom:8px">Interests</p>${chipGroup("Interests", INTERESTS, u.interests || [])}</div>
      <div class="form-grid">
        <label class="field">Travel date<input type="date" name="travel_date" value="${esc(isoLocal(nextWeekday(6, 12)).slice(0, 10))}" required></label>
        <label class="field">Days<input type="number" name="days" min="1" max="30" value="3" required></label>
        <label class="field">Budget<select name="budget">${options(BUDGETS, u.budget || "mid")}</select></label>
        <label class="field">Travelling as<select name="group_type">${options(GROUPS, u.group_type || "couple")}</select></label>
        <label class="field">Starting from<select name="origin"><option value="">Anywhere in India</option>${u.home_lat ? `<option value="home" selected>Home (${esc(u.home_city || "saved")})</option>` : ""}<option value="geo">My current location</option></select></label>
        <label class="field">Maximum distance<select name="max_distance_km"><option value="">No limit</option>${[300, 600, 1000, 1500].map((k) => `<option value="${k}">${k} km</option>`).join("")}</select></label>
        <div><button class="btn" type="submit">Recommend destinations</button></div></div></form>
    <div id="rec-out" style="margin-top:20px"></div></div>`;
  bindChips(el);
  $("#rec", el).addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, out = $("#rec-out", el);
    const body = { interests: chipValues(f), travel_date: f.travel_date.value, days: +f.days.value, budget: f.budget.value,
                   group_type: f.group_type.value, limit: 8 };
    if (f.max_distance_km.value) body.max_distance_km = +f.max_distance_km.value;
    if (f.origin.value === "home") body.origin = { lat: u.home_lat, lon: u.home_lon };
    if (f.origin.value === "geo") {
      try {
        const pos = await new Promise((ok, no) => navigator.geolocation.getCurrentPosition(ok, no, { timeout: 8000 }));
        body.origin = { lat: pos.coords.latitude, lon: pos.coords.longitude };
      } catch { toast("Couldn't get your location; showing results for anywhere in India.", true); }
    }
    if (body.max_distance_km && !body.origin) { toast("Choose a starting point to use a distance limit.", true); return; }
    out.innerHTML = loading("Scoring destinations");
    try {
      const r = await api("/api/recommendations", { method: "POST", body });
      if (!r.items.length) { out.innerHTML = empty("Nothing within that distance", "Raise the distance limit or change the starting point."); return; }
      out.innerHTML = `<div class="rows">${r.items.map((x, i) => `<div class="row" style="display:grid;grid-template-columns:1fr auto;gap:12px">
        <div><a href="#/d/${esc(x.slug)}"><strong style="font-size:1.2rem">${i + 1}. ${esc(x.name)}</strong></a> <span class="meta">${esc(x.state)}${x.distance_km != null ? ` · ${x.distance_km} km away` : ""}</span>
          <ul style="margin:8px 0 0;padding-left:18px">${x.reasons.map((s) => `<li>${esc(s)}</li>`).join("")}${x.cautions.map((s) => `<li class="note">${esc(s)}</li>`).join("")}</ul>
          <p class="note" style="margin-top:6px">Score ${Math.round(x.score * 100)} / 100 — ${Object.entries(x.breakdown).map(([k, v]) => `${esc(k)} ${Math.round(v * 100)}`).join(", ")}</p></div>
        <div style="text-align:right">${levelPill(x.crowd.level)}<p class="note">crowds that day</p><a class="btn small" style="margin-top:8px" href="#/plan?d=${esc(x.slug)}&date=${esc(r.travel_date)}">Plan it</a></div></div>`).join("")}</div>
        <p class="note" style="margin-top:10px">${esc(r.method)}</p>${provenanceBox(r.provenance)}`;
    } catch (err) { out.innerHTML = errorBox(err); }
  });
}

// ------------------------------------------------------------------ itinerary planner
export async function planner(el, params) {
  const all = [...(await api("/api/destinations?limit=60")).items, ...(await api("/api/destinations?limit=60&page=2")).items];
  const pre = params.get("d") || "";
  const u = state.user || {};
  el.innerHTML = `<div class="page"><div class="page-head"><div><h1>Plan a trip</h1><p>We build each day around opening hours and the quietest times, and tell you where our numbers are estimates.</p></div></div>
    <form class="panel" id="plan" style="display:grid;gap:16px">
      <div class="form-grid">
        ${[0, 1, 2].map((i) => `<label class="field">${i ? `Then (optional)` : "Destination"}<select name="d${i}" ${i ? "" : "required"}><option value="">${i ? "None" : "Choose"}</option>${options(all.map((d) => [d.slug, `${d.name}, ${d.state.name}`]), i ? "" : pre)}</select></label>`).join("")}
        <label class="field">Start date<input type="date" name="start_date" required value="${esc(params.get("date") || isoLocal(nextWeekday(6, 12)).slice(0, 10))}"></label>
        <label class="field">Days<input type="number" name="days" min="1" max="10" value="2" required aria-describedby="days-hint"><span class="hint" id="days-hint">1 to 10 days</span></label>
        <label class="field">Pace<select name="pace">${options([["relaxed", "Relaxed (3 stops)"], ["normal", "Normal (4 stops)"], ["packed", "Packed (5 stops)"]], "normal")}</select></label>
        <label class="field">Travelling as<select name="group_type">${options(GROUPS, u.group_type || "couple")}</select></label>
        <label class="field">Budget<select name="budget">${options(BUDGETS, u.budget || "mid")}</select></label></div>
      <div><p class="field" style="font-weight:500;margin-bottom:8px">Interests</p>${chipGroup("Interests", INTERESTS, u.interests || [])}</div>
      <div><button class="btn" type="submit">Build my plan</button></div></form>
    <div id="plan-out" style="margin-top:20px"></div></div>`;
  bindChips(el);
  $("#plan", el).addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const body = { destinations: [...new Set([f.d0.value, f.d1.value, f.d2.value].filter(Boolean))], start_date: f.start_date.value,
                   days: +f.days.value, pace: f.pace.value, group_type: f.group_type.value, budget: f.budget.value, interests: chipValues(f) };
    const out = $("#plan-out", el);
    out.innerHTML = loading("Building your plan");
    try {
      const r = await api("/api/itineraries/generate", { method: "POST", body });
      out.innerHTML = planHTML(r.plan, { editable: false }) + `<section class="panel" style="margin-top:16px"><header><h2>Save this plan</h2></header>
        ${state.user ? `<form id="save" class="form-grid"><label class="field">Trip name<input name="title" required maxlength="120" value="${esc(body.destinations.map((s) => all.find((d) => d.slug === s)?.name).join(" & "))} trip"></label><div><button class="btn">Save trip</button></div></form>`
          : `<p><a href="#/login?next=${encodeURIComponent("#/plan")}">Sign in</a> to save and edit plans.</p>`}</section>`;
      drawPlanMap(r.plan, el);
      const s = $("#save", el);
      if (s) s.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        try {
          const it = await api("/api/itineraries", { method: "POST", body: { ...body, title: s.title.value } });
          toast("Trip saved");
          location.hash = `#/trips/${it.id}`;
        } catch (err) { toast(err.message, true); }
      });
    } catch (err) { out.innerHTML = errorBox(err); }
  });
  if (pre) $("#plan", el).requestSubmit();
}

function planHTML(plan, { editable }) {
  return `${plan.warnings.length ? `<div class="provenance" style="background:#ffe8dc"><strong style="color:#8a3200">Heads-up</strong>${plan.warnings.map((w) => `<span>${esc(w)}</span>`).join("")}</div>` : ""}
    <div class="grid12" style="margin-top:16px"><div class="s7 plan-days">${plan.days.map((d, di) => `<article class="day" data-day="${di}">
      <header><h3>Day ${d.day}: ${esc(d.destination.name)}</h3><span class="note">${esc(fmtDate(d.date))}</span></header>
      ${d.travel_note ? `<p class="note">${esc(d.travel_note)}</p>` : ""}
      ${d.stops.length ? "" : '<p class="note">Free time: no further catalogued places fit this day.</p>'}
      ${d.stops.map((s, si) => `<div class="stop" data-slug="${esc(s.slug)}"><time>${esc(s.start)}–${esc(s.end)}</time>
        <div><strong>${esc(s.name)}</strong> ${levelPill(s.predicted.level)}<div class="note">${esc(cap(s.category))} · ${s.fee ? esc(inr(s.fee)) : "Free"} · open ${esc(hrRange(s.open_hour, s.close_hour))}</div>
          ${s.tip ? `<div class="note">${esc(s.tip)}</div>` : ""}${s.warning ? `<div class="form-error">${esc(s.warning)}</div>` : ""}</div>
        ${editable ? `<div class="tools"><button class="btn small quiet" data-act="up" aria-label="Move ${esc(s.name)} earlier" ${si === 0 ? "disabled" : ""}>↑</button><button class="btn small quiet" data-act="down" aria-label="Move ${esc(s.name)} later" ${si === d.stops.length - 1 ? "disabled" : ""}>↓</button><button class="btn small danger" data-act="del" aria-label="Remove ${esc(s.name)}">Remove</button></div>` : "<div></div>"}
        <p class="travel">${esc(s.travel_note)}</p></div>`).join("")}
      ${d.breaks.map((b) => `<p class="break">${esc(b.label)} around ${esc(b.start)}</p>`).join("")}</article>`).join("")}</div>
      <div class="s5"><div class="map" id="planmap" style="position:sticky;top:16px"></div>
        <p style="margin-top:12px"><strong>Estimated cost:</strong> ${esc(inr(plan.estimated_cost_inr))} per person</p><p class="note">${esc(plan.cost_note)}</p>
        <p class="note" style="margin-top:8px">${esc(plan.disclaimer)}${plan.weather_used ? " Live rain forecasts were used to favour covered places." : ""}</p></div></div>`;
}

function drawPlanMap(plan, el) {
  whenLeafletReady(() => {
    const box = $("#planmap", el);
    if (!box) return;
    const map = makeMap(box);
    if (!map) return;
    const pts = [];
    plan.days.forEach((d) => {
      const line = d.stops.map((s) => [s.lat, s.lon]);
      d.stops.forEach((s) => { dot(map, s.lat, s.lon, { level: s.predicted.level, popup: `Day ${d.day}, ${esc(s.start)}: ${esc(s.name)}` }); pts.push([s.lat, s.lon]); });
      if (line.length > 1) L.polyline(line, { color: "#3d0012", weight: 3, opacity: 0.7, dashArray: "6 6" }).addTo(map);
    });
    if (pts.length) map.fitBounds(pts, { padding: [30, 30], maxZoom: 13 });
  });
}

// ------------------------------------------------------------------ saved trips
export async function trips(el) {
  if (!state.user) return requireLogin(el, "see your trips");
  try {
    const r = await api("/api/itineraries");
    el.innerHTML = `<div class="page"><div class="page-head"><div><h1>My trips</h1><p>Your saved plans. Open one to reorder stops, add notes or rebuild it.</p></div><a class="btn" href="#/plan">Plan a new trip</a></div>
      ${r.items.length ? `<div class="rows">${r.items.map((t) => `<a class="row" href="#/trips/${t.id}"><div><strong>${esc(t.title)}</strong><div class="meta">${esc(fmtDate(t.start_date))} · ${t.days} day${t.days > 1 ? "s" : ""} · ${esc([...new Set(t.destinations)].join(", "))}</div></div><span class="meta">Updated ${esc(fmtWhen(t.updated_at))}</span></a>`).join("")}</div>`
        : empty("No saved trips yet", "Build a plan and press Save trip.", '<p style="margin-top:10px"><a class="btn small" href="#/plan">Plan a trip</a></p>')}</div>`;
  } catch (e) { el.innerHTML = errorBox(e); }
}

export async function trip(el, params, id) {
  if (!state.user) return requireLogin(el, "see this trip");
  let it;
  try { it = await api(`/api/itineraries/${id}`); } catch (e) { el.innerHTML = e.status === 404 ? empty("Trip not found", "It may have been deleted.", '<a href="#/trips">Back to my trips</a>') : errorBox(e); return; }
  const render = () => {
    el.innerHTML = `<div class="page"><p class="crumbs"><a href="#/trips">My trips</a></p>
      <div class="page-head"><div><h1>${esc(it.title)}</h1><p>${esc(fmtDate(it.start_date))} · ${it.days} day${it.days > 1 ? "s" : ""} · ${esc(cap(it.params.pace))} pace${it.plan.edited ? " · edited by you" : ""}</p></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn quiet" id="regen">Rebuild plan</button><button class="btn danger" id="del">Delete trip</button></div></div>
      <form class="panel form-grid" id="meta"><label class="field">Trip name<input name="title" maxlength="120" required value="${esc(it.title)}"></label>
        <label class="field" style="grid-column:1/-1">Notes<textarea name="notes" maxlength="2000" placeholder="Tickets to book, things to pack…">${esc(it.notes)}</textarea></label>
        <div><button class="btn">Save changes</button></div></form>
      ${planHTML(it.plan, { editable: true })}</div>`;
    drawPlanMap(it.plan, el);
    $("#meta", el).addEventListener("submit", async (e) => {
      e.preventDefault();
      try { it = await api(`/api/itineraries/${it.id}`, { method: "PUT", body: { title: e.target.title.value, notes: e.target.notes.value } }); toast("Changes saved"); render(); }
      catch (err) { toast(err.message, true); }
    });
    $("#regen", el).addEventListener("click", async () => {
      if (!confirm("Rebuild this plan? Your manual stop changes will be replaced.")) return;
      try { it = await api(`/api/itineraries/${it.id}/regenerate`, { method: "POST", body: {} }); toast("Plan rebuilt"); render(); }
      catch (err) { toast(err.message, true); }
    });
    $("#del", el).addEventListener("click", async () => {
      if (!confirm("Delete this trip permanently?")) return;
      try { await api(`/api/itineraries/${it.id}`, { method: "DELETE" }); toast("Trip deleted"); location.hash = "#/trips"; }
      catch (err) { toast(err.message, true); }
    });
    $$(".stop [data-act]", el).forEach((b) => b.addEventListener("click", async () => {
      const days = it.plan.days.map((d) => d.stops.map((s) => s.slug));
      const di = +b.closest(".day").dataset.day, slug = b.closest(".stop").dataset.slug, list = days[di], i = list.indexOf(slug);
      if (b.dataset.act === "up" && i > 0) [list[i - 1], list[i]] = [list[i], list[i - 1]];
      if (b.dataset.act === "down" && i < list.length - 1) [list[i + 1], list[i]] = [list[i], list[i + 1]];
      if (b.dataset.act === "del") list.splice(i, 1);
      try { it = await api(`/api/itineraries/${it.id}`, { method: "PUT", body: { days: days.map((s) => ({ stops: s })) } }); toast("Times updated"); render(); }
      catch (err) { toast(err.message, true); }
    }));
  };
  render();
}

// ------------------------------------------------------------------ community
export async function community(el, params, sub) {
  if (sub === "guidelines") {
    const g = await api("/api/community/guidelines");
    el.innerHTML = `<div class="page"><p class="crumbs"><a href="#/community">Community</a></p><div class="page-head"><div><h1>Community guidelines</h1><p>So everyone can trust what they read here.</p></div></div>
      <ol class="panel" style="padding-left:40px;display:grid;gap:10px">${g.items.map((x) => `<li>${esc(x)}</li>`).join("")}</ol>
      <p class="note" style="margin-top:12px">Use “Report” on any post, comment or review that breaks these rules. Moderators can hide it.</p></div>`;
    return;
  }
  if (sub) return post(el, sub);
  await loadLookups();
  try {
    const r = await api("/api/posts");
    const all = (await api("/api/destinations?limit=60&sort=name")).items.concat((await api("/api/destinations?limit=60&page=2&sort=name")).items);
    el.innerHTML = `<div class="page"><div class="page-head"><div><h1>Travel community</h1><p>First-hand tips from travellers: when it was quiet, what to skip, what surprised you.</p></div><a class="btn quiet" href="#/community/guidelines">Guidelines</a></div>
      <div class="grid12"><div class="s8" style="display:grid;gap:12px">${r.items.length ? r.items.map((p) => `<article class="post"><h3><a href="#/community/${p.id}">${esc(p.title)}</a></h3>
          <p class="note">${esc(p.author)}${p.destination ? ` · <a href="#/d/${esc(p.destination.slug)}">${esc(p.destination.name)}</a>` : ""} · ${esc(fmtWhen(p.created_at))} · ${p.comment_count} comment${p.comment_count === 1 ? "" : "s"}</p>
          <p class="body" style="margin-top:8px">${esc(p.body.length > 280 ? p.body.slice(0, 280) + "…" : p.body)}</p></article>`).join("")
        : empty("No posts yet", "Be the first to share a tip.")}</div>
      <section class="panel s4" aria-labelledby="np"><header><h2 id="np">Share an experience</h2></header>
        ${state.user ? `<form id="newpost" style="display:grid;gap:12px"><label class="field">Title<input name="title" required minlength="3" maxlength="140"></label>
          <label class="field">Destination (optional)<select name="destination"><option value="">None</option>${options(all.map((d) => [d.slug, d.name]))}</select></label>
          <label class="field">Your experience<textarea name="body" required minlength="3" maxlength="5000"></textarea></label>
          <p class="note">By posting you agree to the <a href="#/community/guidelines">guidelines</a>.</p><div><button class="btn">Publish post</button></div></form>`
          : `<p><a href="#/login?next=%23%2Fcommunity">Sign in</a> to post.</p>`}</section></div></div>`;
    const f = $("#newpost", el);
    if (f) f.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const p = await api("/api/posts", { method: "POST", body: { title: f.title.value, body: f.body.value, destination: f.destination.value || null } });
        toast("Post published");
        location.hash = `#/community/${p.id}`;
      } catch (err) { toast(err.message, true); }
    });
  } catch (e) { el.innerHTML = errorBox(e); }
}

async function post(el, id) {
  let p;
  try { p = await api(`/api/posts/${id}`); } catch (e) { el.innerHTML = e.status === 404 ? empty("Post not available", "It may have been removed by its author or a moderator.", '<a href="#/community">Back to community</a>') : errorBox(e); return; }
  el.innerHTML = `<div class="page"><p class="crumbs"><a href="#/community">Community</a></p>
    <article class="post"><h1 style="font-size:2rem;margin-bottom:8px">${esc(p.title)}</h1><p class="note">${esc(p.author)}${p.destination ? ` · <a href="#/d/${esc(p.destination.slug)}">${esc(p.destination.name)}</a>` : ""} · ${esc(fmtWhen(p.created_at))}</p>
      <p class="body" style="margin-top:14px">${esc(p.body)}</p>
      ${state.user ? `<p style="margin-top:14px;display:flex;gap:12px"><button class="linkish" id="flag">Report post</button>${state.user.name === p.author || state.user.role === "admin" ? '<button class="linkish" id="delpost">Delete post</button>' : ""}</p>` : ""}</article>
    <section class="panel" style="margin-top:16px"><header><h2>Comments (${p.comments.length})</h2></header>
      <div class="rows">${p.comments.map((c) => `<div class="row" style="display:block"><strong>${esc(c.author)}</strong> <span class="meta">${esc(fmtWhen(c.created_at))}</span><p class="body" style="margin-top:4px">${esc(c.body)}</p>
        ${state.user ? `<button class="linkish note" data-flagc="${c.id}">Report</button>` : ""}</div>`).join("") || '<p class="note">No comments yet.</p>'}</div>
      ${state.user ? `<form id="cform" style="display:grid;gap:10px;margin-top:14px"><label class="field">Add a comment<textarea name="body" required maxlength="1500"></textarea></label><div><button class="btn">Post comment</button></div></form>` : `<p style="margin-top:12px"><a href="#/login">Sign in</a> to comment.</p>`}</section></div>`;
  const cf = $("#cform", el);
  if (cf) cf.addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await api(`/api/posts/${id}/comments`, { method: "POST", body: { body: cf.body.value } }); toast("Comment posted"); post(el, id); }
    catch (err) { toast(err.message, true); }
  });
  $("#flag", el)?.addEventListener("click", () => flagContent("post", +id));
  $("#delpost", el)?.addEventListener("click", async () => {
    if (!confirm("Delete this post?")) return;
    try { await api(`/api/posts/${id}`, { method: "DELETE" }); toast("Post deleted"); location.hash = "#/community"; } catch (err) { toast(err.message, true); }
  });
  $$("[data-flagc]", el).forEach((b) => b.addEventListener("click", () => flagContent("comment", +b.dataset.flagc)));
}

// ------------------------------------------------------------------ profile
export async function profile(el) {
  if (!state.user) return requireLogin(el, "edit your profile");
  const [me, favs] = await Promise.all([api("/api/me/profile"), api("/api/me/favourites")]);
  el.innerHTML = `<div class="page"><div class="page-head"><div><h1>Your profile</h1><p>Your preferences pre-fill recommendations and plans.</p></div></div>
    <div class="grid12"><form class="panel s8" id="pf" style="display:grid;gap:16px">
      <div class="form-grid"><label class="field">Name<input name="name" required maxlength="80" value="${esc(me.name)}"></label>
        <label class="field">Email<input value="${esc(me.email)}" disabled></label>
        <label class="field">Home city<input name="home_city" maxlength="80" value="${esc(me.home_city || "")}"></label>
        <label class="field">Budget<select name="budget"><option value="">Not set</option>${options(BUDGETS, me.budget)}</select></label>
        <label class="field">Usually travelling as<select name="group_type"><option value="">Not set</option>${options(GROUPS, me.group_type)}</select></label>
        <div><button type="button" class="btn quiet" id="loc">Use my location as home</button><p class="note" id="loc-note">${me.home_lat ? `Saved: ${me.home_lat.toFixed(2)}, ${me.home_lon.toFixed(2)}` : "Used to measure distances."}</p></div></div>
      <div><p class="field" style="font-weight:500;margin-bottom:8px">Interests</p>${chipGroup("Interests", INTERESTS, me.interests)}</div>
      <div><button class="btn">Save profile</button></div></form>
    <section class="panel s4"><header><h2>Favourites</h2></header>${favs.items.length ? `<div class="rows">${favs.items.map((f) => `<div class="row"><a href="#/d/${esc(f.slug)}"><strong>${esc(f.name)}</strong></a><button class="btn small quiet" data-unfav="${esc(f.slug)}">Remove</button></div>`).join("")}</div>` : '<p class="note">No favourites yet.</p>'}</section></div></div>`;
  bindChips(el);
  let coords = me.home_lat ? { home_lat: me.home_lat, home_lon: me.home_lon } : {};
  $("#loc", el).addEventListener("click", () => navigator.geolocation.getCurrentPosition((p) => {
    coords = { home_lat: +p.coords.latitude.toFixed(4), home_lon: +p.coords.longitude.toFixed(4) };
    out("#loc-note", el).textContent = `Will save ${coords.home_lat}, ${coords.home_lon}`;
  }, () => toast("Location permission was not granted.", true)));
  $("#pf", el).addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    try {
      state.user = await api("/api/me/profile", { method: "PUT", body: { name: f.name.value, home_city: f.home_city.value || null,
        budget: f.budget.value || null, group_type: f.group_type.value || null, interests: chipValues(f), ...coords } });
      toast("Profile saved");
    } catch (err) { toast(err.message, true); }
  });
  $$("[data-unfav]", el).forEach((b) => b.addEventListener("click", async () => {
    try { await api(`/api/me/favourites/${b.dataset.unfav}`, { method: "DELETE" }); toast("Removed from favourites"); profile(el); } catch (err) { toast(err.message, true); }
  }));
}

// ------------------------------------------------------------------ about the data
export async function about(el) {
  const m = await api("/api/model");
  el.innerHTML = `<div class="page"><div class="page-head"><div><h1>How our data works</h1><p>What is live, what is modelled and what is demonstration data.</p></div></div>
    <div class="grid12">
      <section class="panel s6"><header><h2>Where each number comes from</h2></header>
        <table class="data"><thead><tr><th>Information</th><th>Source</th><th>Kind</th></tr></thead><tbody>
        <tr><td>Destinations, attractions, hours, fees</td><td>TripNest catalogue from public knowledge</td><td><span class="tag">Indicative</span></td></tr>
        <tr><td>Carrying capacity</td><td>Assumptions made for the prototype</td><td><span class="tag demo">Assumed</span></td></tr>
        <tr><td>Hourly visitor history</td><td>Simulated from capacity, season, weekday, holidays and rain</td><td><span class="tag demo">Demonstration</span></td></tr>
        <tr><td>Crowd forecasts and levels</td><td>Gradient-boosted model trained on that history</td><td><span class="tag demo">Model, demo-trained</span></td></tr>
        <tr><td>Traveller crowd reports</td><td>Signed-in users, last 90 minutes</td><td><span class="tag live">Live</span></td></tr>
        <tr><td>Weather</td><td>Open-Meteo forecast API</td><td><span class="tag live">Live</span></td></tr>
        <tr><td>Map</td><td>OpenStreetMap</td><td><span class="tag live">Live</span></td></tr>
        <tr><td>Seeded reviews and listings</td><td>Generated examples</td><td><span class="tag demo">Demo</span></td></tr></tbody></table></section>
      <section class="panel s6"><header><h2>Model card</h2></header>
        <p>${esc(m.backend)}. Target: ${esc(m.target)}.</p>
        <p style="margin-top:8px">Trained ${esc(fmtWhen(m.trained_at))} on ${m.history_days} days × ${m.attractions} attractions.</p>
        <table class="data" style="margin-top:12px"><thead><tr><th>Period</th><th>Dates</th><th>Rows</th></tr></thead><tbody>
          <tr><td>Train</td><td>${esc(m.split.train_start)} to ${esc(m.split.train_end)}</td><td>${m.rows.train.toLocaleString("en-IN")}</td></tr>
          <tr><td>Validation</td><td>${esc(m.split.val_start)} to ${esc(m.split.val_end)}</td><td>${m.rows.validation.toLocaleString("en-IN")}</td></tr>
          <tr><td>Test</td><td>${esc(m.split.test_start)} to ${esc(m.split.test_end)}</td><td>${m.rows.test.toLocaleString("en-IN")}</td></tr></tbody></table>
        <table class="data" style="margin-top:12px"><thead><tr><th>On the test fortnight</th><th>MAPE</th><th>MAE (people)</th><th>R²</th></tr></thead><tbody>
          <tr><td><strong>TripNest model</strong></td><td>${m.test_metrics.mape}%</td><td>${m.test_metrics.mae}</td><td>${m.test_metrics.r2}</td></tr>
          <tr><td>Same hour last week</td><td>${m.baselines.seasonal_naive.mape}%</td><td>${m.baselines.seasonal_naive.mae}</td><td>${m.baselines.seasonal_naive.r2}</td></tr>
          <tr><td>Weekday-hour average</td><td>${m.baselines.weekday_hour_mean.mape}%</td><td>${m.baselines.weekday_hour_mean.mae}</td><td>${m.baselines.weekday_hour_mean.r2}</td></tr></tbody></table>
        <p class="note" style="margin-top:10px">${esc(m.note)} Uncertainty: ${esc(m.uncertainty.method)}.</p>
        <p style="margin-top:10px">Strongest inputs: ${m.top_features.map((f) => esc(f.feature)).join(", ")}.</p></section>
      <section class="panel s12"><header><h2>Crowd levels</h2></header>
        <p>${levelPill("Low")} under 40% of assumed capacity · ${levelPill("Moderate")} 40–70% · ${levelPill("High")} 70–90% · ${levelPill("At Capacity")} 90% and above. Ecologically sensitive sites use stricter limits: 25%, 50% and 70%.</p>
        <p class="note" style="margin-top:8px">To use real data, load gate or sensor counts with the same columns (attraction, date, hour, count) and retrain with <code>python -m scripts.train_model</code>.</p></section></div></div>`;
}
