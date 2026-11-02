// Destination details: prediction for a date and time range, trend, best time and visitor information.
import { $, $$, out, api, esc, toast, hr, MONTHS, inr, levelPill, forecastChart, loading, errorBox, empty } from "./core.js";
import { crowdMap, mapShell, fillPhotos, creditLine, typeTags, interestLabel, dayLabel, longDay, todayISO, maxDateISO } from "./shared.js";

const HOURS = Array.from({ length: 19 }, (_, i) => i + 5);
const opt = (sel) => HOURS.map((h) => `<option value="${h}" ${h === sel ? "selected" : ""}>${esc(hr(h))}</option>`).join("");

export async function destination(el, params, slug) {
  const P = { date: params.get("date") || todayISO(), from: +(params.get("from") || 9), to: +(params.get("to") || 17), back: params.get("back") || "" };
  el.innerHTML = `<div class="discover"><div class="d-panel" id="panel">${loading("Predicting crowds")}</div>${mapShell()}</div>`;
  const map = crowdMap($("#d-map", el));
  const panel = out("#panel", el);
  let p;
  try { p = await api(`/api/destinations/${encodeURIComponent(slug)}/prediction?date=${P.date}&from=${P.from}&to=${P.to}`); }
  catch (e) {
    panel.innerHTML = e.status === 404
      ? `<div class="d-card">${empty("Destination not found", "It may have been removed.", '<a href="#/">Back to search</a>')}</div>` : `<div class="d-card">${errorBox(e)}</div>`;
    return;
  }
  const d = p.destination, s = p.selected, prov = p.provenance, q = p.best_time;
  const rangeText = `${hr(P.from)} to ${hr(P.to)}`;
  document.title = `${d.name} crowd prediction — TripNest AI`;

  const go = (patch) => {
    const n = new URLSearchParams({ date: P.date, from: P.from, to: P.to, ...(P.back ? { back: P.back } : {}), ...patch });
    location.hash = `#/d/${d.slug}?${n}`;
  };

  panel.innerHTML = `
    <section class="d-card">
      <p class="crumbs"><a href="${P.back ? "#/results?" + esc(P.back) : "#/"}">${P.back ? "Back to results" : "Back to search"}</a></p>
      <div class="hero-photo" data-photo="${esc(d.slug)}" aria-hidden="true"></div>
      <h1>${esc(d.name)}</h1>
      <p class="note">${esc(d.state)} · ${d.categories.slice(0, 4).map((c) => esc(interestLabel(c))).join(", ")}</p>
      <p style="margin-top:10px">${esc(d.description)}</p>
      <p class="credit" id="credit"></p>
    </section>

    <section class="d-card" aria-labelledby="pred-h">
      <h2 id="pred-h">Predicted crowd</h2>
      <form class="refine three" id="when"><label class="field">Date<input type="date" name="date" min="${todayISO()}" max="${maxDateISO()}" value="${esc(P.date)}"></label>
        <label class="field">From<select name="from">${opt(P.from)}</select></label><label class="field">To<select name="to">${opt(P.to)}</select></label>
        <button class="btn quiet" type="submit">Update</button></form>
      <p class="form-error" id="when-err" role="alert"></p>
      <div class="bigread lv-${esc(s.level.replace(/\s+/g, "-"))}" aria-live="polite">
        <div><span class="note">${esc(longDay(p.date))}, ${esc(rangeText)}</span><b>${s.level === "Closed" ? "Closed in this time range" : esc(s.level) + " crowds"}</b></div>
        ${s.level === "Closed" ? "" : `<p>Busiest around <strong>${esc(s.peak_label)}</strong>: about <strong>${s.visitors.toLocaleString("en-IN")}</strong> people across the destination
          (likely ${s.low.toLocaleString("en-IN")} to ${s.high.toLocaleString("en-IN")}), or ${Math.round(s.util * 100)}% of assumed capacity.</p>`}
      </div>
      ${p.calendar.holiday ? `<p class="note" style="margin-top:8px">${esc(p.calendar.name)}: holiday crowds are included in this prediction.</p>` : ""}
      ${p.in_season ? "" : `<p class="note" style="margin-top:8px">${esc(MONTHS[new Date(p.date).getMonth()])} is outside the usual best season.</p>`}
      <div class="tagrow">${typeTags()}</div>
      <div style="margin-top:12px">${forecastChart(p.hourly, { label: `${d.name} predicted crowd on ${p.date}`, selected: null })}</div>
      <div class="legend"><span><i style="background:#c9cdc6"></i>Low</span><span><i style="background:#ffc23d"></i>Moderate</span><span><i style="background:#ff8233"></i>High</span><span><i style="background:#e0261a"></i>At capacity</span><span><i style="background:#ffe39a"></i>Likely range (${Math.round(prov.uncertainty.confidence * 100)}%)</span></div>
      <p class="note" style="margin-top:6px">Levels: Low under 40% of assumed capacity, Moderate 40–70%, High 70–90%, At capacity above 90%.</p>
    </section>

    ${q ? `<section class="d-card" aria-labelledby="best-h"><h2 id="best-h">Best time to visit</h2>
      <p class="bestline"><b>${esc(q.label)}</b> ${levelPill(q.level)} <span class="note">the quietest daytime hour on ${esc(dayLabel(p.date))}, about ${q.visitors.toLocaleString("en-IN")} people</span></p>
      <h3 class="sub">The next 7 days</h3>
      <div class="week">${p.week.map((w) => `<button class="day lv-${esc(w.peak_level.replace(/\s+/g, "-"))}" data-date="${esc(w.date)}" aria-label="${esc(dayLabel(w.date))}: ${esc(w.peak_level)} crowds, quietest ${esc(w.quietest_label || "")}" aria-pressed="${w.date === p.date}">
        <span>${esc(w.weekday)}</span><b>${esc(w.date.slice(8))}</b><i>${esc(w.peak_level)}</i><small>${esc(w.quietest_label || "")}</small></button>`).join("")}</div>
      <p class="note" style="margin-top:6px">Each day shows its busiest daytime level and its quietest hour. Select a day to see its prediction.</p></section>` : ""}

    <section class="d-card" aria-labelledby="att-h"><h2 id="att-h">Places inside ${esc(d.name)}</h2><p class="note" style="margin:4px 0 10px">Predicted for ${esc(rangeText)}</p>
      <div class="rows">${p.attractions.map((a) => `<div class="row"><div><strong>${esc(a.name)}</strong>
        <div class="meta">${esc(a.category)} · open ${esc(hr(a.open_hour))} – ${esc(hr(a.close_hour === 24 ? 24 : a.close_hour))}${a.sensitive ? " · fragile site, stricter limits" : ""} · best ${esc(a.best_hour_label)}</div></div>
        <div>${levelPill(a.level)}</div></div>`).join("")}</div></section>

    <section class="d-card" aria-labelledby="info-h"><h2 id="info-h">Visitor information</h2>
      <dl class="facts"><dt>Getting there</dt><dd>${esc(d.how_to_reach)}</dd>
        <dt>Best months</dt><dd>${esc(d.best_months.map((m) => MONTHS[m - 1]).join(", "))}</dd>
        <dt>Suggested stay</dt><dd>${d.min_days}+ day${d.min_days > 1 ? "s" : ""}</dd>
        <dt>Typical cost</dt><dd>About ${esc(inr(d.daily_cost))} per person per day (indicative)</dd>
        <dt>Facilities</dt><dd>${esc(d.facilities.join(", "))}</dd></dl>
      <p class="note">${esc(d.data_source)}. Hours and fees are indicative; check locally before you travel.</p></section>

    <section class="d-card" aria-labelledby="lim-h"><h2 id="lim-h">About this prediction</h2>
      <p>This is an <strong>ML prediction from demonstration data</strong>, not a live count. Made ${esc(new Date(prov.generated_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }))}.</p>
      <p class="note" style="margin-top:6px">${esc(prov.data_freshness)}</p>
      <p class="note" style="margin-top:6px">Uncertainty: ${esc(prov.uncertainty.method)}.</p>
      <details style="margin-top:8px"><summary>Limitations</summary><ul class="why">${prov.limitations.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></details></section>`;

  // controls
  $("#when", el).addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.target, err = out("#when-err", el);
    if (+f.from.value > +f.to.value) { err.textContent = "The start time must not be after the end time."; return; }
    if (!f.date.value) { err.textContent = "Choose a date."; return; }
    err.textContent = "";
    go({ date: f.date.value, from: f.from.value, to: f.to.value });
  });
  $$(".week .day", el).forEach((b) => b.addEventListener("click", () => go({ date: b.dataset.date })));

  // photos
  fillPhotos(el, "destinations", [d.slug]).then((ph) => (out("#credit", el).innerHTML = creditLine(ph)));

  // map: attractions coloured by their predicted level in the chosen range
  api(`/api/destinations/${d.slug}`).then((full) => {
    const byslug = Object.fromEntries(full.attractions.map((a) => [a.slug, a]));
    const points = p.attractions.map((a) => ({ lat: byslug[a.slug].lat, lon: byslug[a.slug].lon, level: a.level, name: a.name, radius: 9 }));
    out("#map-when", el).textContent = `${d.name}: predicted crowds, ${dayLabel(p.date)}, ${rangeText}`;
    map.setPoints(points);
    const fit = () => map.ready ? map.fit(points.map((x) => [x.lat, x.lon]), { maxZoom: 13 }) : setTimeout(fit, 150);
    fit();
  }).catch((e) => toast(e.message, true));
}
