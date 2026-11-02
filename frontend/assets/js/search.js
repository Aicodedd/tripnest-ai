// Shared by the landing page and the explore page: interest list, city field, and location permission handling.
import { $, out, api, esc } from "./core.js";


export const INTEREST_LABELS = { heritage: "Heritage", spiritual: "Spiritual", beach: "Beaches", nature: "Nature", wildlife: "Wildlife",
  waterfall: "Waterfalls", lake: "Lakes", mountain: "Mountains", viewpoint: "Viewpoints", adventure: "Adventure", market: "Markets",
  museum: "Museums", garden: "Gardens", plantation: "Plantations", food: "Food", backwaters: "Backwaters", island: "Islands",
  desert: "Desert", snow: "Snow", river: "Rivers", trek: "Trekking", culture: "Culture" };
export const interestLabel = (k) => INTEREST_LABELS[k] || k.charAt(0).toUpperCase() + k.slice(1);

export function interestOptions(select, selected = "") {
  api("/api/categories").then((r) => {
    select.insertAdjacentHTML("beforeend", r.items.slice(0, 18).map((c) => `<option value="${esc(c.name)}" ${c.name === selected ? "selected" : ""}>${esc(interestLabel(c.name))}</option>`).join(""));
    if (selected && !r.items.slice(0, 18).some((c) => c.name === selected)) select.insertAdjacentHTML("beforeend", `<option value="${esc(selected)}" selected>${esc(interestLabel(selected))}</option>`);
  }).catch(() => {});
}

/**
 * City field + "use my location". Location is requested only when the visitor presses the button
 * (or automatically if the browser already has their permission). Coordinates are rounded to about 1 km.
 * Returns { resolve(): {lat, lon, name, src}, autoIfGranted() }.
 */
export function bindLocationField(root, S, { onGeo } = {}) {
  const input = $("#from", root), note = $("#loc-note", root), btn = $("#geo", root);
  api("/api/locations/all").then((r) => {
    out("#city-list", root).innerHTML = r.items.map((c) => `<option value="${esc(c.name)}">${esc(c.state)}</option>`).join("");
  }).catch(() => {});
  input.addEventListener("input", () => { S.geo = null; });

  async function useGeo(fromClick) {
    if (!navigator.geolocation) { problem("Your browser can't share a location."); return; }
    note.textContent = "Waiting for your browser's permission…";
    navigator.geolocation.getCurrentPosition(async (p) => {
      S.geo = { lat: +p.coords.latitude.toFixed(2), lon: +p.coords.longitude.toFixed(2) };
      try {
        const r = await api(`/api/locations/nearest?lat=${S.geo.lat}&lon=${S.geo.lon}`);
        S.geo.name = r.covered ? r.label.replace(/^near /, "") : "your location";
        S.geoInfo = r;
        input.value = r.covered ? `My location (${r.label})` : "My current location";
        note.textContent = r.covered ? "Using your current location. Type a city to change it." : r.message;
        if (onGeo) onGeo(r);
        if (fromClick && r.covered) root.querySelector("form")?.requestSubmit();
      } catch { problem("We couldn't work out where you are. Type your city instead."); }
    }, (err) => problem(err.code === 1 ? "Location permission was not given." : "Your location isn't available right now."),
    { timeout: 9000, maximumAge: 600000 });
  }
  function problem(why) {
    S.geo = null;
    note.textContent = `${why} That's fine: type your city instead.`;
    input.focus();
  }
  btn.addEventListener("click", () => useGeo(true));

  return {
    async resolve() {
      const text = input.value.trim();
      if (S.geo && S.geoInfo && !S.geoInfo.covered) throw new Error(S.geoInfo.message);
      if (S.geo && S.geoInfo && S.geoInfo.covered) return { lat: S.geo.lat, lon: S.geo.lon, name: S.geo.name, src: "gps" };
      if (!text) throw new Error("Enter your city, or use your current location.");
      const c = await api(`/api/locations/resolve?q=${encodeURIComponent(text)}`);
      return { lat: c.lat, lon: c.lon, name: c.name, src: "city" };
    },
    async autoIfGranted() {
      try {
        const perm = await navigator.permissions?.query({ name: "geolocation" });
        if (perm && perm.state === "granted") useGeo(false);
        else if (perm && perm.state === "denied") note.textContent = "Location is blocked in your browser settings. Type your city instead.";
      } catch { /* Permissions API unavailable: the visitor can still press the button */ }
    },
  };
}
