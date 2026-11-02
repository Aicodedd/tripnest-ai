// Results: recommended destinations with predicted crowds, explanations and comparison.
import { $, $$, out, api, esc, toast, hr, levelPill, lineChart, loading, errorBox, empty } from "./core.js";
import { crowdMap, mapShell, fillPhotos, creditLine, typeTags, interestLabel, dayLabel, todayISO, maxDateISO } from "./shared.js";

const KM = [["", "Any distance"], ["300", "Within 300 km"], ["600", "Within 600 km"], ["1000", "Within 1,000 km"], ["1500", "Within 1,500 km"]];
const FACTOR = { crowd: "Quiet on your date", interest: "Matches your interest", distance: "Near you", season: "Right season" };

export async function results(el, params) {
  const P = { lat: params.get("lat"), lon: params.get("lon"), from: params.get("from") || "", date: params.get("date"),
              interest: params.get("interest") || "", max_km: params.get("max_km") || "" };
  if (!P.date) { el.innerHTML = `<div class="d-card" style="margin:24px">${empty("Choose a date first", "Results need a travel date.", '<a href="#/">Start again</a>')}</div>`; return; }
  const chosen = new Set();
  const back = encodeURIComponent(params.toString());
  const detailHref = (slug) => `#/d/${slug}?date=${P.date}&back=${back}`;
  const S = { items: [] };

  el.innerHTML = `<div class="discover"><div class="d-panel" id="panel">
      <section class="d-card">
        <p class="crumbs"><a href="#/">Back to search</a></p>
        <h1 id="r-title">Destinations for ${esc(dayLabel(P.date))}</h1>
        <p class="note" id="r-sub">${P.from ? `Starting from ${esc(P.from)}` : "No starting location, so distance is not used"}${P.interest ? ` · interested in ${esc(interestLabel(P.interest))}` : ""}</p>
        <form class="refine" id="refine"><label class="field">Date<input type="date" name="date" min="${todayISO()}" max="${maxDateISO()}" value="${esc(P.date)}"></label>
          <label class="field">Distance<select name="max_km" ${P.lat ? "" : "disabled"}>${KM.map(([v, l]) => `<option value="${v}" ${v === P.max_km ? "selected" : ""}>${l}</option>`).join("")}</select></label>
          <button class="btn quiet" type="submit">Update</button></form>
        <div class="tagrow">${typeTags()}</div>
      </section>
      <div id="compare-slot"></div>
      <div id="list" class="rlist">${loading("Predicting crowds and ranking destinations")}</div>
      <section class="d-card" id="why" hidden></section>
      <p class="credit" id="credit"></p>
    </div>${mapShell(`Predicted crowds, ${dayLabel(P.date)}`)}</div>`;

  $("#refine", el).addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.target, q = new URLSearchParams(params);
    q.set("date", f.date.value);
    f.max_km.value ? q.set("max_km", f.max_km.value) : q.delete("max_km");
    location.hash = `#/results?${q}`;
  });

  const map = crowdMap($("#d-map", el), { onClick: (p) => selectCard(p.slug, false) });

  const qs = new URLSearchParams({ date: P.date, limit: 8 });
  if (P.lat) { qs.set("lat", P.lat); qs.set("lon", P.lon); }
  if (P.interest) qs.set("interest", P.interest);
  if (P.max_km) qs.set("max_km", P.max_km);
  let r;
  try { r = await api(`/api/recommendations?${qs}`); } catch (e) { out("#list", el).innerHTML = errorBox(e); return; }
  S.items = r.items;
  if (!r.items.length) {
    out("#list", el).innerHTML = empty("No destinations found", "Nothing matched. Try a larger distance or a different interest.", '<p style="margin-top:10px"><a class="btn small quiet" href="#/">Change search</a></p>');
    return;
  }
  const list = out("#list", el);
  list.innerHTML = r.items.map((d, i) => card(d, i)).join("");
  $$(".rcard", list).forEach((c) => c.addEventListener("click", (e) => { if (!e.target.closest("a,label,input,summary,details")) selectCard(c.dataset.slug, true); }));
  $$("input[data-cmp]", list).forEach((b) => b.addEventListener("change", () => toggleCompare(b)));

  const why = out("#why", el);
  why.hidden = false;
  why.innerHTML = `<h2>How we ranked these</h2><p class="note" style="margin:6px 0 12px">${esc(r.method)}</p>
    <div class="weights">${Object.entries(r.weights).filter(([, v]) => v > 0).map(([k, v]) => `<div class="wrow"><span>${esc(FACTOR[k])}</span><div class="wbar"><i style="width:${Math.round(v * 100)}%"></i></div><b>${Math.round(v * 100)}%</b></div>`).join("")}</div>
    ${Object.entries(r.weights).filter(([, v]) => v === 0).length ? `<p class="note" style="margin-top:8px">Not used this time: ${Object.entries(r.weights).filter(([, v]) => v === 0).map(([k]) => esc(FACTOR[k].toLowerCase())).join(", ")} (no ${"interest or start location"} given).</p>` : ""}
    <p class="note" style="margin-top:8px">${r.total_considered} destinations were scored. ${esc(r.provenance.data_freshness)}</p>`;

  const points = r.items.map((d) => ({ lat: d.lat, lon: d.lon, level: d.crowd.level, name: d.name, slug: d.slug, radius: 8,
    popup: `<div class="pop-name" style="margin:0"><strong style="color:#fff">${esc(d.name)}</strong><br>${esc(d.crowd.level)} · <a href="${esc(detailHref(d.slug))}">View details</a></div>` }));
  if (P.lat) points.push({ lat: +P.lat, lon: +P.lon, name: P.from || "You", ring: true, radius: 7, level: "" });
  map.setPoints(points);
  const fit = () => map.ready ? map.fit(points.map((p) => [p.lat, p.lon])) : setTimeout(fit, 150);
  fit();

  fillPhotos(list, "destinations", r.items.map((d) => d.slug)).then((ph) => (out("#credit", el).innerHTML = creditLine(ph)));

  function card(d, i) {
    const c = d.crowd, q = d.suggested_time;
    return `<article class="rcard" data-slug="${esc(d.slug)}" tabindex="-1">
      <div class="rimg" data-photo="${esc(d.slug)}" aria-hidden="true"><span class="rank">${i + 1}</span></div>
      <div class="rbody">
        <div class="rtop"><h2>${esc(d.name)}</h2>${levelPill(c.level)}</div>
        <p class="note">${esc(d.state)}${d.distance_km != null ? ` · ${d.distance_km.toLocaleString("en-IN")} km (${esc(d.distance_note)})` : ""}</p>
        <ul class="why">${d.reasons.slice(0, 3).map((x) => `<li>${esc(x)}</li>`).join("")}${d.cautions.slice(0, 1).map((x) => `<li class="caution">${esc(x)}</li>`).join("")}</ul>
        <p class="besttime"><strong>Best time ${esc(q.label)}</strong> ${levelPill(q.level)} <span class="note">Busiest ${esc(c.peak_label || "")}, about ${c.visitors.toLocaleString("en-IN")} people</span></p>
        <details><summary>Why this score (${Math.round(d.score * 100)}/100)</summary>
          <div class="weights">${Object.entries(d.breakdown).map(([k, v]) => `<div class="wrow"><span>${esc(FACTOR[k])}</span><div class="wbar"><i style="width:${Math.round(v * 100)}%"></i></div><b>${Math.round(v * 100)}</b></div>`).join("")}</div></details>
        <div class="ractions"><a class="btn small" href="${esc(detailHref(d.slug))}">View details</a>
          <label class="chip cmp"><input type="checkbox" data-cmp="${esc(d.slug)}"> Compare</label></div>
      </div></article>`;
  }

  function selectCard(slug, fly) {
    $$(".rcard", list).forEach((c) => c.classList.toggle("on", c.dataset.slug === slug));
    const d = S.items.find((x) => x.slug === slug);
    if (!d) return;
    if (fly) map.focus(d.lat, d.lon, 9);
    const pt = points.find((p) => p.slug === slug);
    if (pt?.marker) pt.marker.openPopup();
    if (!fly) $(`.rcard[data-slug="${CSS.escape(slug)}"]`, list)?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest" });
  }

  // ---- compare
  function toggleCompare(box) {
    if (box.checked && chosen.size >= 4) { box.checked = false; toast("You can compare up to 4 destinations.", true); return; }
    box.checked ? chosen.add(box.dataset.cmp) : chosen.delete(box.dataset.cmp);
    drawCompare();
  }
  async function drawCompare() {
    const slot = out("#compare-slot", el);
    if (chosen.size < 2) {
      slot.innerHTML = chosen.size === 1 ? `<section class="d-card slim"><p class="note">Tick Compare on one more destination to see them side by side.</p></section>` : "";
      return;
    }
    const slugs = [...chosen];
    slot.innerHTML = `<section class="d-card" aria-labelledby="cmp-h"><h2 id="cmp-h">Compare ${slugs.length} destinations</h2><div id="cmp-body">${loading()}</div></section>`;
    try {
      const c = await api(`/api/crowd/compare?slugs=${encodeURIComponent(slugs.join(","))}&date=${P.date}`);
      if ([...chosen].join() !== slugs.join()) return;
      const by = Object.fromEntries(S.items.map((d) => [d.slug, d]));
      out("#cmp-body", el).innerHTML = `<p class="note">Share of capacity by hour on ${esc(dayLabel(P.date))}. Lower is quieter.</p>${lineChart(c.items.map((x) => ({ name: x.name, points: x.hourly })))}
        <div class="table-wrap"><table class="data"><thead><tr><th>Destination</th><th>Busiest</th><th>Quietest</th><th>Distance</th><th>Score</th></tr></thead><tbody>
        ${c.items.map((x) => `<tr><td><a href="${esc(detailHref(x.slug))}">${esc(x.name)}</a></td>
          <td>${x.peak ? `${esc(hr(x.peak.hour))} ${levelPill(x.peak.level)}` : "Closed"}</td><td>${x.quietest ? `${esc(hr(x.quietest.hour))} ${levelPill(x.quietest.level)}` : "–"}</td>
          <td>${by[x.slug]?.distance_km != null ? by[x.slug].distance_km.toLocaleString("en-IN") + " km" : "–"}</td><td>${by[x.slug] ? Math.round(by[x.slug].score * 100) : "–"}</td></tr>`).join("")}</tbody></table></div>`;
    } catch (e) { out("#cmp-body", el).innerHTML = errorBox(e); }
  }
}
