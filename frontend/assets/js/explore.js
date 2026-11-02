// Explore: popular places near you, best time to visit, hidden gems ("Escape the crowds") and the interactive crowd map.
import { $, $$, out, api, esc, loading, errorBox, forecastChart } from "./core.js";
import { ICON, chip, SLOT_OPTIONS, dayLabel, longDay, todayISO, maxDateISO, mem, exploreUrl, photo, credit,
  timelineMini, timelineBig, bestLine, markerIcon, youIcon, newMap, popupHTML } from "./ui.js";
import { interestOptions, bindLocationField, interestLabel } from "./search.js";

export async function explore(el, params) {
  const q = { lat: params.get("lat"), lon: params.get("lon"), date: params.get("date"), interest: params.get("interest") || "",
              slot: params.get("slot") || "all", src: params.get("src") || "city" };
  if (!q.lat || !q.lon || !q.date) {
    el.innerHTML = `<div class="wrap pad"><div class="card emptybox"><h1>Start with a location</h1><p>Choose where you are and when you want to travel, and we'll show places around you.</p><p><a class="btn primary" href="#/">Choose a location</a></p></div></div>`;
    return;
  }
  const slotLabel = (SLOT_OPTIONS.find((s) => s[0] === q.slot) || SLOT_OPTIONS[0])[1];
  const backParam = encodeURIComponent(params.toString());
  const href = (slug) => `#/d/${slug}?date=${q.date}${q.slot !== "all" ? "&slot=" + q.slot : ""}&back=${backParam}`;

  el.innerHTML = `
  <section class="band" aria-labelledby="band-h"><div class="hero-bg" id="band-bg" aria-hidden="true"></div><div class="hero-scrim" aria-hidden="true"></div>
    <div class="wrap bandinner"><p class="crumbs"><a href="#/">Change search</a></p>
      <h1 id="band-h">Finding places around you…</h1><p class="bandsub">${esc(longDay(q.date))}</p></div></section>
  <div class="wrap"><form class="refine card" id="refine" novalidate aria-label="Change location, date or time">
    <div class="sfield wide"><label for="from">${ICON.pin}<span>Location</span></label>
      <div class="inrow"><input id="from" list="city-list" autocomplete="off" maxlength="80" aria-describedby="loc-note"><button type="button" class="geo" id="geo" title="Use my current location">${ICON.target}<span>Use my location</span></button></div>
      <datalist id="city-list"></datalist></div>
    <div class="sfield"><label for="date">${ICON.calendar}<span>Travel date</span></label><input type="date" id="date" min="${todayISO()}" max="${maxDateISO()}" value="${esc(q.date)}" required></div>
    <div class="sfield"><label for="interest">${ICON.star}<span>Interest</span></label><select id="interest"><option value="">Any interest</option></select></div>
    <div class="sfield"><label for="slot">${ICON.clock}<span>Time of day</span></label><select id="slot">${SLOT_OPTIONS.map(([v, l]) => `<option value="${v}" ${v === q.slot ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></div>
    <button class="btn primary big" type="submit">Update</button>
    <p class="note panelnote" id="loc-note" role="status"></p><p class="form-error" id="form-err" role="alert"></p></form></div>
  <div class="wrap sections" id="results" aria-busy="true">${loading("Predicting crowds for places around you")}</div>`;

  // ---- refine form (location, date, interest, time of day all refresh the results from the backend)
  const S = { geo: null };
  const loc = bindLocationField(el, S);
  interestOptions(out("#interest", el), q.interest);
  $("#refine", el).addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = out("#form-err", el); err.textContent = "";
    const date = $("#date", el).value;
    if (date < todayISO() || date > maxDateISO()) { err.textContent = "Choose a date from today to about 18 months ahead."; return; }
    try {
      const o = await loc.resolve();
      const n = { lat: o.lat, lon: o.lon, date, interest: $("#interest", el).value, slot: $("#slot", el).value, src: o.src, name: o.name };
      mem.set("last", n);
      location.hash = exploreUrl(n);
    } catch (ex) { err.textContent = ex.message; $("#from", el).focus(); }
  });

  let data;
  try { data = await api(`/api/explore?lat=${q.lat}&lon=${q.lon}&date=${q.date}${q.interest ? "&interest=" + encodeURIComponent(q.interest) : ""}&slot=${q.slot}`); }
  catch (e) { out("#results", el).innerHTML = errorBox(e) + `<p style="margin-top:12px"><a class="btn ghost" href="#/">Back to search</a></p>`; out("#band-h", el).textContent = "We couldn't load places"; return; }
  if (!document.body.contains(el)) return;

  const o = data.origin;
  const place = o.label.startsWith("near ") ? o.label : `around ${o.label}`;
  const cityName = o.label.replace(/^near /, "");
  mem.set("last", { ...q, name: cityName });
  out("#band-h", el).textContent = o.covered ? `Discover amazing places ${place}.` : "TripNest AI covers India";
  out("#band-bg", el).classList.remove("on");
  const bandImg = (data.popular[0] || data.hidden_gems[0] || {}).image;
  if (bandImg) { const im = new Image(); im.onload = () => { const b = out("#band-bg", el); b.style.backgroundImage = `url("${bandImg.url}")`; b.classList.add("on"); }; im.src = bandImg.url; }
  out("#from", el).value = q.src === "gps" ? `My location (${o.label})` : cityName;
  if (q.src === "gps") { S.geo = { lat: +q.lat, lon: +q.lon, name: cityName }; S.geoInfo = o; }
  out("#loc-note", el).textContent = q.src === "gps" ? "Using your current location, rounded to about 1 km." : "";
  const bandsub = el.querySelector(".bandsub");
  bandsub.textContent = `Predicted crowds for ${longDay(q.date)}${q.slot !== "all" ? " · " + slotLabel : ""}`;

  const results = out("#results", el);
  results.setAttribute("aria-busy", "false");
  if (!o.covered) {
    results.innerHTML = `<div class="card emptybox"><h2>${esc(data.message)}</h2><p>Type an Indian city above, or use your location from within India.</p></div>`;
    return;
  }

  const all = [...data.popular, ...data.hidden_gems];
  const credits = new Map(all.filter((i) => i.image).map((i) => [i.image.url, i.image]));
  all.forEach((i) => mem.set("why_" + i.slug, { back: params.toString(), date: q.date, group: i.group, reasons: i.reasons, classification_reason: i.classification_reason, alternative_to: i.alternative_to || null }));

  const card = (it) => `<article class="dcard ${it.group}" data-slug="${esc(it.slug)}">
    <a class="dimg" href="${esc(href(it.slug))}" tabindex="-1" aria-hidden="true">${photo(it.image, it.name, "r43")}
      ${chip(it.crowd.level, "overlay")}<span class="kind ${it.group}">${it.group === "popular" ? ICON.star + "Popular" : ICON.gem + "Hidden gem"}</span></a>
    <div class="dbody"><h3><a href="${esc(href(it.slug))}">${esc(it.name)}</a></h3>
      <p class="loc">${ICON.pin}<span>${esc(it.state)} · ${it.distance_km.toLocaleString("en-IN")} km away</span></p>
      <p class="desc">${esc(it.description)}</p>
      ${timelineMini(it.timeline)}
      <p class="bt">${ICON.clock}<span>Best time: <b>${esc(it.best_label)}</b></span></p>
      ${it.group === "hidden_gem" ? `<div class="why"><p>${esc(it.reasons[0])}.</p><p>${esc(it.reasons[1])}${it.reasons[1].endsWith(".") ? "" : "."}</p></div>
        <details class="small"><summary>Why is this a hidden gem?</summary><p>${esc(it.classification_reason)}</p></details>` : ""}
      <div class="dact"><a class="btn primary small" href="${esc(href(it.slug))}">View Details</a><button type="button" class="btn ghost small" data-onmap="${esc(it.slug)}">${ICON.map}View on map</button></div></div></article>`;

  results.innerHTML = `
  <section id="popular" aria-labelledby="pop-h"><div class="sechead"><div><h2 id="pop-h">Popular places near you</h2>
      <p class="secsub">Predicted crowd for ${esc(dayLabel(q.date))}${q.slot !== "all" ? ", " + esc(slotLabel.toLowerCase()) : ", busiest hour"}. Nearest first${q.interest ? `, ${esc(interestLabel(q.interest))} first` : ""}.</p></div></div>
    ${data.popular_note ? `<p class="notice">${ICON.info}${esc(data.popular_note)}</p>` : ""}
    <div class="cards">${data.popular.map(card).join("") || '<p class="note">No popular places found.</p>'}</div></section>

  <section id="best-time" aria-labelledby="bt-h"><div class="sechead"><div><h2 id="bt-h">Best time to visit</h2>
      <p class="secsub">See how the predicted crowd changes through the day, and when it is calmest.</p></div></div>
    <div class="card btpanel"><div class="chips" role="tablist" aria-label="Choose a destination">${all.map((i, n) => `<button role="tab" type="button" class="tabchip" data-bt="${esc(i.slug)}" aria-selected="${n === 0}">${i.group === "hidden_gem" ? ICON.gem : ""}${esc(i.name.split(" (")[0])}</button>`).join("")}</div>
      <div id="bt-body" aria-live="polite"></div></div></section>

  <section id="hidden-gems" class="gemsec" aria-labelledby="gem-h"><div class="sechead"><div><h2 id="gem-h">${ICON.gem} Escape the Crowds</h2>
      <p class="secsub">Discover peaceful places and lesser-known destinations near you.</p></div></div>
    ${data.gems_note ? `<p class="notice">${ICON.info}${esc(data.gems_note)}</p>` : ""}
    <div class="cards">${data.hidden_gems.map(card).join("") || '<p class="note">No lesser-known places found nearby for this date.</p>'}</div></section>

  <section id="crowd-map" aria-labelledby="map-h"><div class="sechead"><div><h2 id="map-h">Crowd map</h2>
      <p class="secsub">Predicted crowds on ${esc(dayLabel(q.date))}. Select a marker for details.</p></div></div>
    <div class="card filters" role="group" aria-label="Map filters"><div class="chips">
      ${[["all", "All places"], ["popular", "Popular places"], ["hidden_gem", "Hidden gems"]].map(([k, l], n) => `<button type="button" class="fchip" data-type="${k}" aria-pressed="${n === 0}">${esc(l)}</button>`).join("")}
      <span class="sep" aria-hidden="true"></span>
      ${[["green", "Low crowd"], ["yellow", "Moderate crowd"], ["red", "High crowd"]].map(([k, l]) => `<button type="button" class="fchip ${k}" data-level="${k}" aria-pressed="false"><i></i>${esc(l)}</button>`).join("")}</div>
      <p class="note" id="map-count" role="status"></p></div>
    <div class="mapwrap"><div id="map" role="region" aria-label="Map of popular places and hidden gems with predicted crowds"></div>
      <div class="legend"><span><i class="dot green"></i>Low</span><span><i class="dot yellow"></i>Moderate</span><span><i class="dot red"></i>High</span>
        <span><i class="shape circ"></i>Popular</span><span><i class="shape dia"></i>Hidden gem</span><span><i class="shape sm"></i>Other place</span><span><i class="shape you"></i>You</span></div></div></section>

  <section class="card about" aria-labelledby="about-h"><h2 id="about-h">About these predictions</h2>
    <p><span class="tag">ML prediction</span> <span class="tag demo">Demonstration data</span> <span class="tag">Not live</span></p>
    <p>${esc(data.provenance.note)}</p><p class="note">${esc(data.provenance.data_freshness)}</p>
    <p class="note">${esc(data.classification.note)} Popular means a catalogue popularity score of ${data.classification.popular_min} or more; lesser-known means ${data.classification.gem_max} or less.</p>
    <details><summary>Limitations</summary><ul class="bul">${data.provenance.limitations.map((l) => `<li>${esc(l)}</li>`).join("")}</ul></details>
    <details><summary>Photo credits</summary><ul class="bul">${[...credits.values()].map((im) => `<li>${esc(im.title || "")}: ${credit(im)}</li>`).join("")}</ul></details></section>`;

  // ---- best time to visit panel
  const preds = new Map();
  const byslug = Object.fromEntries(all.map((i) => [i.slug, i]));
  async function showBest(slug) {
    $$(".tabchip", el).forEach((b) => b.setAttribute("aria-selected", b.dataset.bt === slug));
    const it = byslug[slug], body = out("#bt-body", el);
    body.innerHTML = `<div class="btgrid"><div class="btinfo"><div class="btname">${photo(it.image, it.name, "thumb")}<div><h3>${esc(it.name)}</h3><p class="note">${esc(it.state)}</p>${chip(it.crowd.level)}</div></div>
      ${bestLine(it.best_window)}<p style="margin-top:12px"><a class="btn primary small" href="${esc(href(slug))}">View Details</a></p></div>
      <div class="btright">${timelineBig(it.timeline)}<div class="chartbox" id="chartbox">${loading("Loading hourly prediction")}</div></div></div>`;
    try {
      const p = preds.get(slug) || (await api(`/api/destinations/${slug}/prediction?date=${q.date}&from=5&to=19`));
      preds.set(slug, p);
      const box = out("#chartbox", el);
      if (!box.isConnected || !$(`.tabchip[data-bt="${CSS.escape(slug)}"][aria-selected="true"]`, el)) return;
      const bw = p.best_window;
      box.innerHTML = `<p class="note">Predicted crowd by hour (share of assumed capacity). Colours show the level; the paler band is the likely range.</p>
        ${forecastChart(p.hourly.filter((h) => h.hour <= 19), { label: `${it.name} predicted crowd by hour on ${q.date}`, selected: bw.available ? bw.start_hour : null })}
        <div class="legend"><span><i class="dot green"></i>Low</span><span><i class="dot yellow"></i>Moderate</span><span><i class="dot red"></i>High</span></div>`;
    } catch (e) { out("#chartbox", el).innerHTML = errorBox(e); }
  }
  $$(".tabchip", el).forEach((b) => b.addEventListener("click", () => showBest(b.dataset.bt)));
  if (all.length) showBest(all[0].slug);

  // ---- interactive map with filters
  const F = { type: "all", levels: new Set() };
  const map = await newMap(out("#map", el));
  const markers = new Map();
  if (map) {
    const layer = L.layerGroup().addTo(map);
    L.marker([+q.lat, +q.lon], { icon: youIcon(), zIndexOffset: 1000, keyboard: false }).bindTooltip(`You are here (${o.label})`, { direction: "top" }).addTo(map);
    data.map.forEach((p) => {
      const m = L.marker([p.lat, p.lon], { icon: markerIcon(p.group, p.color), title: `${p.name}: ${p.level}`, riseOnHover: true });
      m.bindPopup(popupHTML(p, href(p.slug)), { className: "tnpop", maxWidth: 300, minWidth: 250, autoPanPaddingTopLeft: [20, 30], autoPanPaddingBottomRight: [20, 20] });
      markers.set(p.slug, { m, p });
    });
    const apply = () => {
      layer.clearLayers();
      let n = 0;
      markers.forEach(({ m, p }) => {
        const okType = F.type === "all" || p.group === F.type;
        const okLevel = !F.levels.size || F.levels.has(p.color);
        if (okType && okLevel) { layer.addLayer(m); n++; }
      });
      out("#map-count", el).textContent = n ? `Showing ${n} of ${data.map.length} places` : "No places match these filters. Clear a filter to see more.";
    };
    $$(".fchip[data-type]", el).forEach((b) => b.addEventListener("click", () => {
      F.type = b.dataset.type;
      $$(".fchip[data-type]", el).forEach((x) => x.setAttribute("aria-pressed", x === b));
      apply();
    }));
    $$(".fchip[data-level]", el).forEach((b) => b.addEventListener("click", () => {
      const on = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", on);
      on ? F.levels.add(b.dataset.level) : F.levels.delete(b.dataset.level);
      apply();
    }));
    apply();
    const pts = [[+q.lat, +q.lon], ...data.popular.concat(data.hidden_gems).map((i) => [i.lat, i.lon])];
    map.fitBounds(pts, { padding: [40, 40], maxZoom: 9 });
    $$("[data-onmap]", el).forEach((b) => b.addEventListener("click", () => {
      const rec = markers.get(b.dataset.onmap);
      if (!rec) return;
      F.type = "all"; F.levels.clear();
      $$(".fchip[data-type]", el).forEach((x) => x.setAttribute("aria-pressed", x.dataset.type === "all"));
      $$(".fchip[data-level]", el).forEach((x) => x.setAttribute("aria-pressed", "false"));
      apply();
      out("#map", el).scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
      let opened = false;
      const open = () => { if (!opened) { opened = true; rec.m.openPopup(); } };
      map.once("moveend", () => setTimeout(open, 60));           // open after the move, so Leaflet can pan the popup into view
      map.flyTo([rec.p.lat, rec.p.lon], 10, { duration: 0.8 });
      setTimeout(open, 2500);                                    // fallback if the map was already there and never moved
    }));
  } else {
    out("#map", el).innerHTML = '<div class="emptybox"><p>The map couldn\'t load. The cards above show the same places.</p></div>';
  }

  const go = params.get("go");
  if (go) requestAnimationFrame(() => out("#" + go, el).scrollIntoView({ block: "start" }));
}
