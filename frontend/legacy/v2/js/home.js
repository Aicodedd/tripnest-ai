// Home: start location + date + optional interest -> recommendations; or check one destination.
import { $, out, api, esc, toast } from "./core.js";
import { crowdMap, mapShell, nextSaturday, todayISO, maxDateISO, interestLabel, dayLabel } from "./shared.js";

export async function home(el) {
  const S = { geo: null, cities: [], dests: new Map() };
  el.innerHTML = `<div class="discover">
    <div class="d-panel">
      <section class="d-card">
        <p class="brandline">TripNest AI</p>
        <h1>Explore beyond the crowds</h1>
        <p class="lede">Tell us where you are starting and when you want to travel. We predict how crowded Indian destinations will be, then recommend the ones that suit you.</p>
        <p class="tagline">Discover Smarter. Travel Better. Explore Beyond the Crowds.</p>
      </section>
      <form class="d-card form-stack" id="find" novalidate aria-labelledby="find-h">
        <h2 id="find-h">Find destinations</h2>
        <label class="field" for="from">Starting location</label>
        <input class="fieldinput" id="from" list="city-list" autocomplete="off" placeholder="Start typing a city, for example Chennai" maxlength="80" required aria-describedby="loc-note">
        <datalist id="city-list"></datalist>
        <p class="note" id="loc-note">Pick a city from the list, type your own, or <button type="button" class="linkish" id="geo">use my current location</button> (your browser will ask first).</p>
        <div class="two">
          <label class="field">Travel date<input type="date" id="date" min="${todayISO()}" max="${maxDateISO()}" value="${nextSaturday()}" required></label>
          <label class="field">Interest (optional)<select id="interest"><option value="">Any interest</option></select></label>
        </div>
        <p class="form-error" id="form-err" role="alert"></p>
        <button class="big-action" type="submit" style="border:0;cursor:pointer;font:inherit">Find Destinations</button>
      </form>
      <form class="d-card form-stack" id="check" novalidate aria-labelledby="check-h">
        <h2 id="check-h">Already have a place in mind?</h2>
        <label class="field" for="dest">Destination</label>
        <input class="fieldinput" id="dest" list="dest-list" autocomplete="off" placeholder="For example Jaipur" maxlength="80" required>
        <datalist id="dest-list"></datalist>
        <p class="note">Uses the travel date above. You can set a time range on the next screen.</p>
        <p class="form-error" id="check-err" role="alert"></p>
        <button class="btn" type="submit">Check crowd prediction</button>
      </form>
      <details class="d-card" id="accuracy"><summary>How good are the predictions?</summary><div id="acc-body" class="note" style="margin-top:10px">Loading…</div></details>
    </div>
    ${mapShell()}</div>`;

  // ---- lookups: cities, interests, destinations
  api("/api/locations/all").then((r) => {
    S.cities = r.items;
    out("#city-list", el).innerHTML = r.items.map((c) => `<option value="${esc(c.name)}">${esc(c.state)}</option>`).join("");
  }).catch(() => {});
  api("/api/categories").then((r) => {
    out("#interest", el).insertAdjacentHTML("beforeend", r.items.slice(0, 14).map((c) => `<option value="${esc(c.name)}">${esc(interestLabel(c.name))}</option>`).join(""));
  }).catch(() => {});
  Promise.all([api("/api/destinations?limit=60&sort=name"), api("/api/destinations?limit=60&sort=name&page=2")]).then(([a, b]) => {
    [...a.items, ...b.items].forEach((d) => S.dests.set(d.name.toLowerCase(), d));
    out("#dest-list", el).innerHTML = [...S.dests.values()].map((d) => `<option value="${esc(d.name)}">${esc(d.state.name)}</option>`).join("");
  }).catch(() => {});
  api("/api/model").then((m) => {
    out("#acc-body", el).innerHTML = `<p>Predictions come from a gradient-boosted model trained on <strong>demonstration data</strong> (no verified visitor counts exist for Indian attractions).</p>
      <p style="margin-top:8px">On a fortnight the model never saw, its hourly forecasts were off by <strong>${m.test_metrics.mape}%</strong> on average. Repeating last week's numbers was off by ${m.baselines.seasonal_naive.mape}%, and a weekday average by ${m.baselines.weekday_hour_mean.mape}%.</p>
      <p style="margin-top:8px">Because the history is simulated, this shows the pipeline works, not real-world accuracy. Real gate or sensor counts can be loaded and the model retrained.</p>`;
  }).catch(() => (out("#acc-body", el).textContent = "Model details are unavailable right now."));

  // ---- location: typed, or browser location only after the visitor asks for it
  const fromEl = $("#from", el), note = $("#loc-note", el);
  fromEl.addEventListener("input", () => { S.geo = null; });
  $("#geo", el).addEventListener("click", () => {
    if (!navigator.geolocation) { noLocation("Your browser can't share a location."); return; }
    note.textContent = "Waiting for your browser's permission…";
    navigator.geolocation.getCurrentPosition((p) => {
      S.geo = { lat: +p.coords.latitude.toFixed(2), lon: +p.coords.longitude.toFixed(2) }; // about 1 km: enough to rank destinations, no precise position kept
      fromEl.value = "My current location";
      note.textContent = "Using your current location. Type a city instead to change it.";
    }, (err) => noLocation(err.code === 1 ? "Location permission was not given." : "Your location isn't available right now."), { timeout: 8000, maximumAge: 600000 });
  });
  function noLocation(why) {
    note.innerHTML = `${esc(why)} That's fine: type your starting city instead.`;
    fromEl.focus();
  }

  // ---- map: predicted crowd around midday on the chosen date
  const map = crowdMap($("#d-map", el), { onClick: (p) => (location.hash = `#/d/${p.destination}?date=${$("#date", el).value}`) });
  let mapSeq = 0;
  async function drawMap() {
    const date = $("#date", el).value;
    if (!date) return;
    const seq = ++mapSeq;
    out("#map-when", el).textContent = `Predicted crowds at midday, ${dayLabel(date)}`;
    try {
      const r = await api(`/api/crowd/map?at=${date}T12:00`);
      if (seq !== mapSeq) return;
      map.setPoints(r.points.map((p) => ({ lat: p.lat, lon: p.lon, level: p.level, name: p.name, radius: 4.5, destination: p.destination,
        popup: `<div class="pop-name" style="margin:0"><strong style="color:#fff">${esc(p.name)}</strong><br>${esc(p.level)} · <a href="#/d/${esc(p.destination)}?date=${date}">View prediction</a></div>` })));
    } catch (e) { toast(e.message, true); }
  }
  drawMap();
  let t; $("#date", el).addEventListener("change", () => { clearTimeout(t); t = setTimeout(drawMap, 150); });

  // ---- submit: find destinations
  $("#find", el).addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = out("#form-err", el); err.textContent = "";
    const date = $("#date", el).value, text = fromEl.value.trim();
    if (!text) { err.textContent = "Enter your starting city, or use your current location."; fromEl.focus(); return; }
    if (!date) { err.textContent = "Choose a travel date."; return; }
    if (date < todayISO() || date > maxDateISO()) { err.textContent = "Choose a date from today to about 18 months ahead."; return; }
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      let o = S.geo ? { name: "Your location", ...S.geo } : await api(`/api/locations/resolve?q=${encodeURIComponent(text)}`);
      const q = new URLSearchParams({ lat: o.lat, lon: o.lon, from: o.name, date });
      const interest = $("#interest", el).value;
      if (interest) q.set("interest", interest);
      location.hash = `#/results?${q}`;
    } catch (ex) { err.textContent = ex.message; btn.disabled = false; }
  });

  // ---- submit: check one destination
  $("#check", el).addEventListener("submit", (e) => {
    e.preventDefault();
    const d = S.dests.get($("#dest", el).value.trim().toLowerCase());
    const err = out("#check-err", el);
    if (!d) { err.textContent = "Choose a destination from the list."; return; }
    if (!$("#date", el).value) { err.textContent = "Choose a travel date above."; return; }
    err.textContent = "";
    location.hash = `#/d/${d.slug}?date=${$("#date", el).value}`;
  });
}
