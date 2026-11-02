// Destination details: photo, prediction for a date and time range, crowd trend, best time, map location.
import { $, $$, out, api, esc, hr, MONTHS, inr, loading, errorBox, forecastChart } from "./core.js";
import { ICON, chip, COLOR, dayLabel, longDay, todayISO, maxDateISO, mem, credit, timelineBig, bestLine, markerIcon, newMap } from "./ui.js";
import { interestLabel } from "./search.js";

const RANGE = { early: [5, 7], morning: [8, 11], afternoon: [12, 15], evening: [16, 19], all: [5, 19] };
const HOURS = Array.from({ length: 18 }, (_, i) => i + 5);
const opt = (sel) => HOURS.map((h) => `<option value="${h}" ${h === sel ? "selected" : ""}>${esc(hr(h))}</option>`).join("");

export async function destination(el, params, slug) {
  const slot = params.get("slot") || "all";
  const dflt = RANGE[slot] || RANGE.all;
  const P = { date: params.get("date") || todayISO(), from: +(params.get("from") || dflt[0]), to: +(params.get("to") || dflt[1]), back: params.get("back") || "" };
  el.innerHTML = `<div class="wrap pad">${loading("Predicting crowds")}</div>`;
  let p;
  try { p = await api(`/api/destinations/${encodeURIComponent(slug)}/prediction?date=${P.date}&from=${P.from}&to=${P.to}`); }
  catch (e) {
    el.innerHTML = `<div class="wrap pad">${e.status === 404 ? `<div class="card emptybox"><h1>Destination not found</h1><p>It may have been removed.</p><p><a class="btn primary" href="#/">Back to search</a></p></div>` : errorBox(e)}</div>`;
    return;
  }
  if (!document.body.contains(el)) return;
  const d = p.destination, s = p.selected, prov = p.provenance;
  const saved = mem.get("why_" + slug);
  const why = saved && P.back && saved.back === P.back && saved.date === P.date ? saved : null;   // only for the search and date that produced it
  document.title = `${d.name} crowd prediction — TripNest AI`;
  const go = (patch) => {
    const n = new URLSearchParams({ date: P.date, from: P.from, to: P.to, ...(P.back ? { back: P.back } : {}), ...patch });
    location.hash = `#/d/${d.slug}?${n}`;
  };
  const rangeText = `${hr(P.from)} to ${hr(P.to + 1)}`;
  const color = COLOR[s.level] || "grey";

  el.innerHTML = `
  <section class="dhero" aria-labelledby="d-h"><div class="hero-bg" id="d-bg" aria-hidden="true"></div><div class="hero-scrim" aria-hidden="true"></div>
    <div class="wrap bandinner"><p class="crumbs"><a href="${P.back ? "#/explore?" + esc(P.back) : "#/"}">${P.back ? "Back to results" : "Back to search"}</a></p>
      <h1 id="d-h">${esc(d.name)}</h1><p class="bandsub">${ICON.pin} ${esc(d.state)} · ${d.categories.slice(0, 4).map((c) => esc(interestLabel(c))).join(", ")}</p></div>
    <p class="herocredit">${d.image ? "Photo: " + credit(d.image) : ""}</p></section>
  <div class="wrap dgrid"><div class="dmain">
    <section class="card"><h2>About ${esc(d.name)}</h2><p>${esc(d.description)}</p>
      ${why ? `<div class="whybox"><b>${why.group === "hidden_gem" ? ICON.gem : ICON.star} Why we showed you this</b><ul class="bul">${why.reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>
        <p class="note">${esc(why.classification_reason)}</p></div>` : ""}</section>

    <section class="card" id="pred" aria-labelledby="pred-h"><h2 id="pred-h">Predicted crowd</h2>
      <form class="refine inline" id="when" novalidate><div class="sfield"><label for="w-date">${ICON.calendar}<span>Date</span></label><input id="w-date" type="date" min="${todayISO()}" max="${maxDateISO()}" value="${esc(P.date)}"></div>
        <div class="sfield"><label for="w-from">${ICON.clock}<span>From</span></label><select id="w-from">${opt(P.from)}</select></div>
        <div class="sfield"><label for="w-to">${ICON.clock}<span>To (hour starting)</span></label><select id="w-to">${opt(P.to)}</select></div>
        <button class="btn primary" type="submit">Update</button></form>
      <p class="form-error" id="when-err" role="alert"></p>
      <div class="reading ${color}" aria-live="polite"><div><span class="note">${esc(longDay(p.date))}, ${esc(rangeText)}</span>
        <b>${s.level === "Closed" ? "Closed in this time range" : esc({ green: "Low crowd", yellow: "Moderate crowd", red: "High crowd" }[color])}</b>
        ${s.level === "At Capacity" ? '<span class="note">Near or above the assumed capacity</span>' : ""}</div>
        ${s.level === "Closed" ? "" : `<p>Busiest around <strong>${esc(s.peak_label)}</strong>: about <strong>${s.visitors.toLocaleString("en-IN")}</strong> people across the destination
          (likely ${s.low.toLocaleString("en-IN")} to ${s.high.toLocaleString("en-IN")}), or ${Math.round(s.util * 100)}% of assumed capacity.</p>`}</div>
      ${p.calendar.holiday ? `<p class="note">${esc(p.calendar.name)}: holiday crowds are included in this prediction.</p>` : ""}
      ${p.in_season ? "" : `<p class="note">${esc(MONTHS[new Date(p.date).getMonth()])} is outside the usual best season.</p>`}
      <div class="tagrow"><span class="tag">ML prediction</span><span class="tag demo">Demonstration data</span><span class="tag">Not live</span></div>
      <h3 class="sub">Through the day</h3>${timelineBig(p.timeline)}
      <div class="bestbox">${bestLine(p.best_window)}</div>
      <div class="chartbox">${forecastChart(p.hourly.filter((h) => h.hour <= 19), { label: `${d.name} predicted crowd by hour on ${p.date}`, selected: p.best_window.available ? p.best_window.start_hour : null })}
        <div class="legend"><span><i class="dot green"></i>Low</span><span><i class="dot yellow"></i>Moderate</span><span><i class="dot red"></i>High</span><span><i class="dot band"></i>Likely range (${Math.round(prov.uncertainty.confidence * 100)}%)</span></div></div>
      <h3 class="sub">The next 7 days</h3>
      <div class="week">${p.week.map((w) => { const c = COLOR[w.peak_level] || "grey"; return `<button type="button" class="day ${c}" data-date="${esc(w.date)}" aria-pressed="${w.date === p.date}" aria-label="${esc(dayLabel(w.date))}: ${esc({ green: "low", yellow: "moderate", red: "high", grey: "closed" }[c])} crowd, quietest ${esc(w.quietest_label || "")}">
        <span>${esc(w.weekday)}</span><b>${esc(w.date.slice(8))}</b><i>${esc({ green: "Low", yellow: "Moderate", red: "High", grey: "Closed" }[c])}</i><small>${esc(w.quietest_label || "")}</small></button>`; }).join("")}</div>
      <p class="note">Each day shows its busiest daytime level and its quietest hour. Select a day to see its prediction.</p></section>

    <section class="card" aria-labelledby="in-h"><h2 id="in-h">Places inside ${esc(d.name)}</h2><p class="note" style="margin-bottom:10px">Predicted for ${esc(rangeText)}</p>
      <div class="rows">${p.attractions.map((a) => `<div class="row"><div><b>${esc(a.name)}</b><div class="note">${esc(a.category)} · open ${esc(hr(a.open_hour))} – ${esc(hr(a.close_hour))}${a.sensitive ? " · fragile site" : ""} · best ${esc(a.best_hour_label)}</div></div>${chip(a.level)}</div>`).join("")}</div></section>

    <section class="card" aria-labelledby="info-h"><h2 id="info-h">Visitor information</h2>
      <dl class="facts"><dt>Getting there</dt><dd>${esc(d.how_to_reach)}</dd><dt>Best months</dt><dd>${esc(d.best_months.map((m) => MONTHS[m - 1]).join(", "))}</dd>
        <dt>Suggested stay</dt><dd>${d.min_days}+ day${d.min_days > 1 ? "s" : ""}</dd><dt>Typical cost</dt><dd>About ${esc(inr(d.daily_cost))} per person per day (indicative)</dd></dl>
      <p class="note">${esc(d.data_source)}. Hours and costs are indicative; check locally before you travel.</p></section>

    <section class="card" aria-labelledby="lim-h"><h2 id="lim-h">About this prediction</h2>
      <p>Made ${esc(new Date(prov.generated_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }))}. ${esc(prov.data_freshness)}</p>
      <p class="note">Uncertainty: ${esc(prov.uncertainty.method)}.</p>
      <details><summary>Limitations</summary><ul class="bul">${prov.limitations.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></details></section>
  </div>
  <aside class="dside"><div class="card"><h2>Location</h2><div id="dmap" class="smallmap" role="region" aria-label="Map of ${esc(d.name)}"></div>
    <div class="legend"><span><i class="dot green"></i>Low</span><span><i class="dot yellow"></i>Moderate</span><span><i class="dot red"></i>High</span></div>
    <p class="note">Markers show each place's predicted crowd for ${esc(rangeText)} on ${esc(dayLabel(p.date))}.</p></div></aside></div>`;

  // hero photo
  if (d.image) { const im = new Image(); im.onload = () => { const b = out("#d-bg", el); b.style.backgroundImage = `url("${d.image.url}")`; b.classList.add("on"); }; im.src = d.image.url; }

  $("#when", el).addEventListener("submit", (e) => {
    e.preventDefault();
    const err = out("#when-err", el), f = $("#w-from", el).value, t = $("#w-to", el).value, dt = $("#w-date", el).value;
    if (!dt) { err.textContent = "Choose a date."; return; }
    if (+f > +t) { err.textContent = "The start time must not be after the end time."; return; }
    err.textContent = "";
    go({ date: dt, from: f, to: t });
  });
  $$(".week .day", el).forEach((b) => b.addEventListener("click", () => go({ date: b.dataset.date })));

  // map: the places inside, coloured by their predicted level
  api(`/api/destinations/${d.slug}`).then(async (full) => {
    const map = await newMap(out("#dmap", el));
    if (!map) { out("#dmap", el).innerHTML = '<p class="note">The map couldn\'t load.</p>'; return; }
    const by = Object.fromEntries(full.attractions.map((a) => [a.slug, a]));
    const pts = [];
    p.attractions.forEach((a) => {
      const g = by[a.slug]; if (!g) return;
      pts.push([g.lat, g.lon]);
      L.marker([g.lat, g.lon], { icon: markerIcon("popular", COLOR[a.level] || "grey"), title: `${a.name}: ${a.level}` })
        .bindPopup(`<div class="pop"><div class="pbody"><div class="ptop"><b>${esc(a.name)}</b>${chip(a.level)}</div><p class="note">${esc(a.category)} · best ${esc(a.best_hour_label)}</p></div></div>`, { className: "tnpop", minWidth: 220 }).addTo(map);
    });
    if (pts.length > 1) map.fitBounds(pts, { padding: [30, 30], maxZoom: 13 }); else if (pts.length) map.setView(pts[0], 12);
  }).catch(() => {});
}
