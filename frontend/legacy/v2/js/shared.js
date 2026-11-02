// Helpers shared by the three pages: crowd colours, labels, photos and the heat map.
import { $, $$, api, esc, hr, whenLeafletReady } from "./core.js";

export const LEVEL_FILL = { Low: "#e8ebe6", Moderate: "#ffc23d", High: "#ff8233", "At Capacity": "#e0261a", Closed: "#d8dbd5" };
export const LEVEL_HEAT = { Moderate: 0.4, High: 0.68, "At Capacity": 0.95 };
// Calibrated for leaflet.heat blur: Moderate renders yellow, High orange, At Capacity red; Low renders nothing.
export const HEAT_GRADIENT = { 0.12: "#fff3a6", 0.25: "#ffd84a", 0.38: "#ffb43d", 0.5: "#ff8233", 0.62: "#f24a22", 0.78: "#d81b12" };

export const INTEREST_LABELS = { heritage: "Heritage", spiritual: "Spiritual", beach: "Beaches", nature: "Nature", wildlife: "Wildlife",
  waterfall: "Waterfalls", lake: "Lakes", mountain: "Mountains", viewpoint: "Viewpoints", adventure: "Adventure", market: "Markets",
  museum: "Museums", garden: "Gardens", plantation: "Plantations", food: "Food", backwaters: "Backwaters", island: "Islands",
  desert: "Desert", snow: "Snow", river: "Rivers", family: "Family", trek: "Trekking" };
export const interestLabel = (k) => INTEREST_LABELS[k] || k.charAt(0).toUpperCase() + k.slice(1);

export const dayLabel = (iso) => new Date(iso + "T12:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
export const longDay = (iso) => new Date(iso + "T12:00").toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
export const nextSaturday = () => {
  const d = new Date();
  d.setDate(d.getDate() + ((6 - d.getDay() + 7) % 7 || 7));
  return localISO(d);
};
export const localISO = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
export const todayISO = () => localISO(new Date());
export const maxDateISO = () => { const d = new Date(); d.setMonth(d.getMonth() + 17); return localISO(d); };

const photoCache = {};
export const getPhoto = (kind, slug) => (photoCache[kind + slug] ||= api(`/api/${kind}/${encodeURIComponent(slug)}/photo`).catch(() => ({ available: false })));

/** Fill [data-photo] elements inside root; returns the photo records that were found (for credits). */
export async function fillPhotos(root, kind, slugs) {
  const found = [];
  await Promise.all(slugs.map(async (slug) => {
    const ph = await getPhoto(kind, slug);
    const box = root.querySelector(`[data-photo="${CSS.escape(slug)}"]`);
    if (!box || !ph.available) return;
    box.style.backgroundImage = `url("${ph.url.replace(/"/g, "")}")`;
    box.classList.add("has-photo");
    box.setAttribute("role", "img");
    box.setAttribute("aria-label", `Photo of ${ph.title}`);
    found.push(ph);
  }));
  return found;
}
export const creditLine = (photos) => photos.length
  ? "Photos via Wikimedia Commons: " + photos.map((p) => `<a href="${esc(p.source_page || p.article)}" target="_blank" rel="noopener">${esc(p.credit)}</a> (${esc(p.licence)})`).join(", ")
  : "";

export const typeTags = () => `<span class="tag">ML prediction</span><span class="tag demo">Demonstration data</span><span class="tag">Not live</span>`;

/** Heat + dots map. Returns {map, setPoints(points), fitTo(latlngs)}; points: [{lat, lon, level, name, popup}] */
export function crowdMap(box, { center = [22.6, 80.5], zoom = 5, onClick = null } = {}) {
  const api2 = { map: null, heat: null, dots: null, ready: false, pending: null };
  whenLeafletReady(() => {
    if (!window.L || !box.isConnected) return;
    const map = L.map(box, { scrollWheelZoom: matchMedia("(min-width: 1101px)").matches }).setView(center, zoom);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, className: "soft-tiles",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map);
    api2.map = map; api2.dots = L.layerGroup().addTo(map); api2.ready = true;
    map.on("zoomend", () => api2.heat && api2.heat.setOptions(heatOpts(map)));
    if (api2.pending) api2.setPoints(api2.pending);
  });
  const heatOpts = (map) => {
    const z = map.getZoom();
    const radius = z >= 13 ? 90 : z >= 11 ? 60 : z >= 8 ? 38 : 22;
    return { radius, blur: radius * 0.8, max: 1, minOpacity: 0.35, gradient: HEAT_GRADIENT };
  };
  api2.setPoints = (points) => {
    api2.pending = points;
    if (!api2.ready) return;
    const hot = points.filter((p) => LEVEL_HEAT[p.level]).map((p) => [p.lat, p.lon, LEVEL_HEAT[p.level]]);
    if (window.L && L.heatLayer) {
      if (api2.heat) { api2.heat.setLatLngs(hot); api2.heat.setOptions(heatOpts(api2.map)); }
      else api2.heat = L.heatLayer(hot, heatOpts(api2.map)).addTo(api2.map);
    }
    api2.dots.clearLayers();
    points.forEach((p) => {
      const m = L.circleMarker([p.lat, p.lon], { radius: p.radius || 6, color: "#141414", weight: p.ring ? 3 : 1.5,
        fillColor: p.ring ? "#fff" : (LEVEL_FILL[p.level] || "#fff"), fillOpacity: 1 }).addTo(api2.dots);
      m.bindTooltip(esc(p.name) + (p.level && !p.ring ? ` · ${esc(p.level)}` : ""), { direction: "top" });
      if (p.popup) m.bindPopup(p.popup, { className: "stat-pop", closeButton: false, maxWidth: 360 });
      if (onClick && !p.ring) m.on("click", () => onClick(p));
      p.marker = m;
    });
  };
  api2.fit = (latlngs, opts = {}) => { if (api2.ready && latlngs.length) api2.map.flyToBounds(latlngs, { padding: [60, 60], maxZoom: 11, duration: 0.7, ...opts }); };
  api2.focus = (lat, lon, z = 11) => api2.ready && api2.map.flyTo([lat, lon], z, { duration: 0.6 });
  return api2;
}

export const mapShell = (note = "") => `<div class="d-map"><div id="d-map" role="region" aria-label="Map of predicted crowds"></div>
  <div class="when" id="map-when">${esc(note)}</div>
  <div class="legend-box" aria-label="Map key"><span><i style="background:#e8ebe6;border:1px solid #b9bdb6"></i>Low</span><span><i style="background:#ffc23d"></i>Moderate</span><span><i style="background:#ff8233"></i>High</span><span><i style="background:#e0261a"></i>At capacity</span></div></div>`;

export { $, $$, hr };
