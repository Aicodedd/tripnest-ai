// Landing page — "One motif": the Taj Mahal's forecast crowd curve for next Saturday is the shape that runs the page.
import { $, $$, out, api, esc, hr, curvePath, nextWeekday, isoLocal, state, reveal, levelPill, makeMap, dot, whenLeafletReady } from "./core.js";

const SHOWCASE = [
  { slug: "amritsar-golden-temple-harmandir-sahib", dest: "amritsar", tab: "Amritsar" },
  { slug: "madurai-meenakshi-amman-temple", dest: "madurai", tab: "Madurai" },
  { slug: "jaipur-amber-amer-fort", dest: "jaipur", tab: "Jaipur" },
];

const wordmark = `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M2 28 C8 28 10 8 16 8 S24 26 30 26 L30 30 L2 30Z" fill="currentColor"/></svg>`;

export function landingShell() {
  const signedIn = !!state.user;
  return `
  <div class="landing">
    <header class="l-nav">
      <a class="wordmark" href="#/">${wordmark}TripNest AI</a>
      <nav aria-label="Main">
        <a href="#/discover" class="hide-sm">Discover</a>
        <a href="#/plan" class="hide-sm">Plan a trip</a>
        <a href="#/community" class="hide-sm">Community</a>
        <a href="${signedIn ? "#/discover" : "#/login"}">${signedIn ? "My TripNest" : "Sign in"}</a>
      </nav>
    </header>
    <main id="main">
      <section class="hero" aria-labelledby="hero-title">
        <svg class="motif shutter" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true"><path class="fill" id="motif-path" d="M0,1000 L0,700 C300,700 400,120 560,120 S800,760 1000,780 L1000,1000 Z"/><circle class="marker" id="motif-marker" r="0" cx="0" cy="0"/></svg>
        <div class="copy">
          <h1 id="hero-title">Go at the quiet hour</h1>
          <p class="lede">Hour-by-hour crowd forecasts for over 200 attractions across all 36 states and union territories, with calmer alternatives and day plans built around them.</p>
          <a class="motif-btn" href="#/discover">Open the crowd map</a>
          <div class="dial" data-ui aria-live="polite">
            <div class="readout"><span id="dial-when">Taj Mahal, next Saturday</span><b id="dial-level">…</b></div>
            <label class="sr-only" for="dial-hour">Hour of the day</label>
            <input id="dial-hour" type="range" min="6" max="18" step="1" value="15" aria-describedby="dial-advice">
            <p class="advice" id="dial-advice">Loading the forecast…</p>
            <p class="src">Model forecast trained on demonstration data, not live counts.</p>
          </div>
        </div>
      </section>

      <section class="l-section" aria-labelledby="sc-title">
        <div class="showcase">
          <div class="plate rise" data-ui id="plate"><h3>Loading…</h3></div>
          <div class="side-copy rise">
            <div class="ltabs" role="tablist" aria-label="Places">${SHOWCASE.map((s, i) =>
              `<button role="tab" aria-selected="${i === 0}" data-i="${i}">${esc(s.tab)}</button>`).join("")}</div>
            <div><h2 id="sc-title">Know the rush before you queue</h2><p id="sc-text"></p></div>
            <div class="cells"><a id="sc-forecast" href="#/explore">See the full forecast</a><a id="sc-plan" href="#/plan">Plan a day around it</a></div>
          </div>
        </div>
      </section>

      <section class="l-section" aria-labelledby="ft-title">
        <h2 id="ft-title" class="rise">What TripNest does for you</h2>
        <div class="bands" id="bands"></div>
      </section>

      <section class="l-section" aria-labelledby="lu-title">
        <h2 id="lu-title" class="rise">Next Saturday, hour by hour</h2>
        <table class="lineup rise" aria-describedby="lu-title">
          <thead><tr><th scope="col">Place</th><th scope="col">State</th><th scope="col">Busiest</th><th scope="col">Quietest</th></tr></thead>
          <tbody id="lineup"><tr><td colspan="4">Loading forecasts…</td></tr></tbody>
        </table>
      </section>

      <section class="l-section" aria-labelledby="mp-title">
        <h2 id="mp-title" class="rise">Every state, one map</h2>
        <div class="mapband rise" id="lmap" data-ui role="region" aria-label="Map of TripNest destinations"></div>
        <p class="map-note rise">Each dot is a destination with hour-by-hour forecasts for its attractions. Select one to open it. Map © OpenStreetMap contributors.</p>
      </section>

      <section class="l-section" aria-labelledby="hw-title">
        <h2 id="hw-title" class="rise">How a forecast is made</h2>
        <div class="stages rise" data-ui>
          <div style="flex-grow:5"><b>A year of hourly history</b><p class="inline-note">First, a demonstration history for every attraction.</p></div>
          <div style="flex-grow:2"><b id="st-train">Half a minute of training</b><p class="inline-note">Then a gradient-boosted model learns the patterns.</p></div>
          <div style="flex-grow:1.3"><b>Under a second</b><p class="inline-note">Next, a forecast for any place and hour.</p></div>
          <div style="flex-grow:1.6"><b>Your day</b><p class="inline-note">Finally, a plan that dodges the rush.</p></div>
        </div>
        <div class="stage-notes">
          <p class="rise" style="flex-grow:5">First, a year of hourly demonstration visits for each attraction, shaped by weekday, season, holidays and rain.</p>
          <p style="flex-grow:2">Then a gradient-boosted model learns those patterns, tested on a fortnight it never saw.</p>
          <p style="flex-grow:1.3">Next, it forecasts any place and hour.</p>
          <p style="flex-grow:1.6">Finally, your plan avoids the rush.</p>
        </div>
        <p class="metrics-line rise" id="metrics-line"></p>
      </section>

      <section class="l-section" aria-labelledby="cta-title">
        <h2 id="cta-title" class="sr-only">Start planning</h2>
        <form class="blank-form rise" id="cta-form">
          Quiet trips to <label class="sr-only" for="cta-q">Place or state</label><input id="cta-q" name="q" placeholder="Kerala" maxlength="60" autocomplete="off"> <button type="submit">go</button>
        </form>
        <p class="cta-note">Type a place or state. We'll show matching destinations, each with its crowd forecast.</p>
      </section>
    </main>
    <footer class="l-footer">
      <div class="blocks rise" aria-label="TripNest">${"TripNest".split("").map((c, i) =>
        `<span aria-hidden="true" style="height:${[100, 72, 88, 64, 94, 70, 84, 60][i]}%">${c}</span>`).join("")}</div>
      <div class="foot-cols">
        <ul><li><a href="#/explore">Destinations</a></li><li><a href="#/map">Map</a></li><li><a href="#/compare">Compare crowds</a></li></ul>
        <ul><li><a href="#/recommend">Recommendations</a></li><li><a href="#/plan">Trip planner</a></li><li><a href="#/trips">My trips</a></li></ul>
        <ul><li><a href="#/community">Community</a></li><li><a href="#/community/guidelines">Guidelines</a></li><li><a href="${signedIn ? "#/profile" : "#/register"}">${signedIn ? "Profile" : "Create account"}</a></li></ul>
        <ul><li><a href="#/about">How our data works</a></li><li><a href="/docs">API documentation</a></li><li><a href="/api/health">Service status</a></li></ul>
        <p>Crowd figures are forecasts from a model trained on demonstration data. Hours and fees are indicative. Map © OpenStreetMap contributors. Weather from Open-Meteo.</p>
      </div>
      <div class="foot-last"><span>© 2026 TripNest AI · hackathon prototype</span><a href="#/">Back to top</a></div>
    </footer>
  </div>`;
}

const sat = () => nextWeekday(6, 12);

export async function mountLanding() {
  reveal();
  const day = isoLocal(sat()).slice(0, 10);
  const dayLabel = sat().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });
  out("#dial-when").textContent = `Taj Mahal, ${dayLabel}`;

  // Hero: real forecast drives the motif shape and the dial.
  let taj, alt;
  try {
    [taj, alt] = await Promise.all([
      api(`/api/attractions/agra-taj-mahal/forecast?date=${day}`),
      api(`/api/attractions/agra-mehtab-bagh/forecast?date=${day}`),
    ]);
  } catch (e) {
    out("#dial-advice").textContent = "Forecasts are unavailable right now. " + e.message;
    return;
  }
  const path = $("#motif-path");
  if (!path) return; // the visitor left the landing page while forecasts were loading
  const hourly = taj.hourly.filter((h) => h.hour >= 6 && h.hour <= 18);
  path.setAttribute("d", curvePath(hourly, 1000, 1000));
  const byHour = Object.fromEntries(hourly.map((h) => [h.hour, h]));
  const altBy = Object.fromEntries(alt.hourly.map((h) => [h.hour, h]));
  const quiet = hourly.reduce((a, b) => (b.util < a.util ? b : a));
  const maxU = Math.max(...hourly.map((h) => h.util));
  const range = $("#dial-hour");
  const marker = $("#motif-marker");

  const update = () => {
    const h = byHour[+range.value];
    if (!h) return;
    out("#dial-level").textContent = h.level;
    range.setAttribute("aria-valuetext", `${hr(h.hour)}, ${h.level}`);
    const i = hourly.indexOf(h);
    marker.setAttribute("cx", (i / (hourly.length - 1)) * 1000);
    marker.setAttribute("cy", 1000 - (h.util / maxU) * 820);
    marker.setAttribute("r", 14);
    let advice = `<strong>${esc(hr(h.hour))}:</strong> about ${h.visitors.toLocaleString("en-IN")} people inside (likely ${h.low.toLocaleString("en-IN")}–${h.high.toLocaleString("en-IN")}).`;
    if (h.level === "High" || h.level === "At Capacity") {
      const a = altBy[h.hour];
      advice += ` Come at <strong>${esc(hr(quiet.hour))}</strong> instead (${esc(quiet.level)})`;
      if (a) advice += `, or watch it from Mehtab Bagh across the river (${esc(a.level)} then).`;
      else advice += ".";
    } else {
      advice += " A good time to go.";
    }
    out("#dial-advice").innerHTML = advice;
  };
  range.addEventListener("input", update);
  update();

  // Feature bands with working switches; consequences use the same real figures.
  const pk = taj.peak;
  const altPk = altBy[pk.hour];
  const bands = [
    ["Send me at the quiet hour", `Taj Mahal on ${dayLabel}: ${hr(pk.hour)} is ${pk.level} (~${pk.visitors.toLocaleString("en-IN")} people); ${hr(quiet.hour)} is ${quiet.level} (~${quiet.visitors.toLocaleString("en-IN")}).`, true],
    ["Offer a calmer place nearby", altPk ? `At ${hr(pk.hour)}, Mehtab Bagh across the Yamuna is ${altPk.level} with ~${altPk.visitors.toLocaleString("en-IN")} people and a view of the Taj.` : "Each busy place lists quieter alternatives that match your interests.", true],
    ["Hold fragile places to stricter limits", "Sensitive sites such as Dzukou Valley and Bangaram Island count as 'At capacity' from 70% of their assumed limit, not 90%.", false],
    ["Keep my day inside opening hours", "Plans fit every stop into its listed hours and add straight-line travel estimates between stops, so you know what is a guess.", false],
  ];
  out("#bands").innerHTML = bands.map(([say, then, on], i) => `
    <div class="bandrow rise" data-on="${on}">
      <div><p class="say" id="band-${i}">${esc(say)}</p><p class="then" ${on ? "" : "hidden"}>${esc(then)}</p></div>
      <button class="switch" role="switch" aria-checked="${on}" aria-labelledby="band-${i}"></button>
    </div>`).join("");
  $$("#bands .switch").forEach((b) => b.addEventListener("click", () => {
    const row = b.closest(".bandrow");
    const on = b.getAttribute("aria-checked") !== "true";
    b.setAttribute("aria-checked", on);
    row.dataset.on = on;
    row.querySelector(".then").hidden = !on;
  }));

  // Showcase: three real places, tabbed.
  const cache = {};
  const show = async (i) => {
    $$(".ltabs button").forEach((b) => b.setAttribute("aria-selected", +b.dataset.i === i));
    const s = SHOWCASE[i];
    try {
      cache[i] = cache[i] || (await api(`/api/attractions/${s.slug}/forecast?date=${day}`));
    } catch (e) { out("#sc-text").textContent = e.message; return; }
    const f = cache[i];
    const q = f.hourly.filter((h) => h.hour >= 6 && h.hour <= 20).reduce((a, b) => (b.util < a.util ? b : a), f.hourly[0]);
    out("#plate").innerHTML = `<h3>${esc(f.attraction.name)}</h3><p class="sub">${esc(f.attraction.destination.name)} · ${esc(dayLabel)}</p>
      <div class="mini">
        <div><span>Busiest</span><span>${esc(hr(f.peak.hour))} ${levelPill(f.peak.level)}</span></div>
        <div><span>Quietest</span><span>${esc(hr(q.hour))} ${levelPill(q.level)}</span></div>
        <div><span>People at peak</span><span>~${f.peak.visitors.toLocaleString("en-IN")}</span></div>
        <div><span>Assumed capacity</span><span>${f.capacity.value.toLocaleString("en-IN")}</span></div>
      </div>`;
    out("#sc-text").textContent = `${f.attraction.name} peaks around ${hr(f.peak.hour)} (${f.peak.level}). Arrive at ${hr(q.hour)} and you share it with about ${q.visitors.toLocaleString("en-IN")} people instead of ${f.peak.visitors.toLocaleString("en-IN")}.`;
    out("#sc-forecast").href = `#/d/${s.dest}`;
    out("#sc-plan").href = `#/plan?d=${s.dest}`;
  };
  $$(".ltabs button").forEach((b) => b.addEventListener("click", () => show(+b.dataset.i)));
  show(0);

  // Line-up and model metrics.
  api(`/api/crowd/highlights?date=${day}&limit=14`).then((r) => {
    out("#lineup").innerHTML = r.items.map((x) => `<tr class="rise">
      <td><a href="#/d/${esc(x.destination.slug)}">${esc(x.attraction)}</a></td><td>${esc(x.state)}</td>
      <td>${esc(hr(x.peak.hour))} · ${esc(x.peak.level)}</td><td>${esc(hr(x.quietest.hour))} · ${esc(x.quietest.level)}</td></tr>`).join("");
    reveal($("#lineup"));
  }).catch((e) => (out("#lineup").innerHTML = `<tr><td colspan="4">${esc(e.message)}</td></tr>`));
  api("/api/model").then((m) => {
    out("#st-train").textContent = `${Math.round(m.seconds)} seconds of training`;
    out("#metrics-line").textContent = `On a fortnight it never saw, the model's hourly forecasts are off by ${m.test_metrics.mape}% on average. Repeating last week's numbers would be off by ${m.baselines.seasonal_naive.mape}%. Both are measured on demonstration data, so this proves the pipeline, not real-world accuracy.`;
  }).catch(() => {});

  api("/api/destinations?limit=60").then((r) => whenLeafletReady(() => {
    const map = makeMap($("#lmap"), { center: [22.8, 81], zoom: 5 });
    if (!map) return;
    r.items.forEach((d) => dot(map, d.lat, d.lon, { radius: 8, popup: `<strong>${esc(d.name)}</strong><br>${esc(d.state.name)}<br><a href="#/d/${esc(d.slug)}">Open forecasts</a>` }));
  })).catch(() => {});

  $("#cta-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = $("#cta-q").value.trim();
    location.hash = q ? `#/explore?q=${encodeURIComponent(q)}` : "#/discover";
  });
}
