// Landing: hero photo, location-first search panel, location permission handled only by the visitor's choice.
import { $, out, api, esc } from "./core.js";
import { ICON, mem, exploreUrl, nextSaturday, todayISO, maxDateISO, credit } from "./ui.js";
import { interestOptions, bindLocationField } from "./search.js";

const HERO_SLUG = "valparai";

export async function landing(el) {
  const last = mem.get("last") || {};
  el.innerHTML = `
  <section class="hero" aria-labelledby="hero-title">
    <div class="hero-bg" id="hero-bg" aria-hidden="true"></div><div class="hero-scrim" aria-hidden="true"></div>
    <div class="wrap hero-inner">
      <h1 id="hero-title"><span>Explore More. Wait Less.</span><span>Discover Beyond the Crowds.</span></h1>
      <p class="hero-sub">Discover popular destinations around you, predict tourist crowds and find peaceful places to explore.</p>
      <p class="greet" id="greet" hidden></p>
      <form class="searchpanel" id="find" novalidate aria-label="Find destinations">
        <div class="sfield wide"><label for="from">${ICON.pin}<span>Location</span></label>
          <div class="inrow"><input id="from" list="city-list" autocomplete="off" placeholder="e.g. Coimbatore" maxlength="80" aria-describedby="loc-note">
          <button type="button" class="geo" id="geo" title="Use my current location (your browser will ask first)">${ICON.target}<span>Use my location</span></button></div>
          <datalist id="city-list"></datalist></div>
        <div class="sfield"><label for="date">${ICON.calendar}<span>Travel date</span></label>
          <input type="date" id="date" min="${todayISO()}" max="${maxDateISO()}" value="${esc(last.date && last.date >= todayISO() ? last.date : nextSaturday())}" required></div>
        <div class="sfield"><label for="interest">${ICON.star}<span>Interest (optional)</span></label>
          <select id="interest"><option value="">Any interest</option></select></div>
        <button class="btn primary big" type="submit">Explore Destinations ${ICON.arrow}</button>
        <p class="note panelnote" id="loc-note" role="status">Choose a city, or let your browser share your location. Nothing is stored.</p>
        <p class="form-error" id="form-err" role="alert"></p>
      </form>
    </div>
    <p class="herocredit" id="herocredit"></p>
  </section>
  <section class="wrap values" aria-label="What TripNest AI does">
    <article><span class="vi">${ICON.map}</span><h2>Popular places near you</h2><p>See well-known destinations around you, each with the crowd predicted for your travel date.</p></article>
    <article><span class="vi">${ICON.clock}</span><h2>Best time to visit</h2><p>See how the crowd changes from early morning to evening, and the calmest hour to go.</p></article>
    <article><span class="vi">${ICON.gem}</span><h2>Escape the crowds</h2><p>Find lesser-known places nearby that are predicted to be calm on your date.</p></article>
  </section>`;

  interestOptions(out("#interest", el), last.interest);
  const S = { geo: null };
  const loc = bindLocationField(el, S, { onGeo: (r) => toGreeting(r) });
  if (last.lat) { /* keep the previous city name when we have it */ if (last.name) $("#from", el).value = last.name; }

  // hero photograph (stored in the database, with credit)
  api(`/api/destinations/${HERO_SLUG}`).then((d) => {
    if (!d.image) return;
    const bg = out("#hero-bg", el);
    const img = new Image();
    img.onload = () => { bg.style.backgroundImage = `url("${d.image.url}")`; bg.classList.add("on"); };
    img.src = d.image.url;
    out("#herocredit", el).innerHTML = `Photo: ${credit(d.image)}`;
  }).catch(() => {});

  const toGreeting = (r) => {
    const g = out("#greet", el);
    g.hidden = false;
    g.textContent = r.covered ? `Discover amazing places ${r.label.startsWith("near ") ? r.label : "around " + r.label}.`
                              : r.message;
  };
  // If the visitor already allowed location for this site, use it right away (no prompt appears in that case).
  loc.autoIfGranted();

  $("#find", el).addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = out("#form-err", el); err.textContent = "";
    const date = $("#date", el).value, interest = $("#interest", el).value;
    if (date < todayISO() || date > maxDateISO()) { err.textContent = "Choose a date from today to about 18 months ahead."; return; }
    const btn = e.target.querySelector("button[type=submit]"); btn.disabled = true;
    try {
      const o = await loc.resolve();
      const q = { lat: o.lat, lon: o.lon, date, interest, name: o.name, src: o.src };
      mem.set("last", q);
      location.hash = exploreUrl(q);
    } catch (ex) { err.textContent = ex.message; btn.disabled = false; $("#from", el).focus(); }
  });
}
