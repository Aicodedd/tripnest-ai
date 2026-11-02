// Shared UI pieces: icons, crowd chips, photos, timeline, session memory, map helpers, date helpers.
import { esc, hr, whenLeafletReady } from "./core.js";

const i = (d, extra = "") => `<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra}>${d}</svg>`;
export const ICON = {
  pin: i('<path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>'),
  calendar: i('<rect x="3.5" y="5" width="17" height="15" rx="3"/><path d="M8 3v4M16 3v4M3.5 10h17"/>'),
  star: i('<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8L3.5 9.7l5.9-.9z"/>'),
  clock: i('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
  arrow: i('<path d="M5 12h14M13 6l6 6-6 6"/>'),
  plane: i('<path d="M21 3 3 10.5l7 2.5 2.5 7z"/><path d="m10 13 11-10"/>'),
  gem: i('<path d="M6 4h12l3 5-9 11L3 9z"/><path d="M3 9h18M9 4l-1 5 4 11 4-11-1-5"/>'),
  map: i('<path d="M9 4 3 6.5V20l6-2.5 6 2.5 6-2.5V4l-6 2.5z"/><path d="M9 4v13.5M15 6.5V20"/>'),
  target: i('<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>'),
  check: i('<path d="m5 12.5 4.5 4.5L19 7.5"/>'),
  info: i('<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>'),
  chart: i('<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>'),
};

export const COLOR = { Low: "green", Moderate: "yellow", High: "red", "At Capacity": "red", Closed: "grey" };
export const COLOR_LABEL = { green: "Low crowd", yellow: "Moderate crowd", red: "High crowd", grey: "Closed" };
export const MARKER_FILL = { green: "#22c55e", yellow: "#f5b301", red: "#ef4444", grey: "#94a3b8" };

export const chip = (level, extra = "") => {
  const c = COLOR[level] || "grey";
  const near = level === "At Capacity" ? ' title="Near or above the assumed capacity"' : "";
  return `<span class="chip ${c} ${extra}"${near}><i aria-hidden="true"></i>${esc(COLOR_LABEL[c])}</span>`;
};

export const SLOT_OPTIONS = [["all", "Any time (busiest hour)"], ["early", "Early morning (5–8 AM)"], ["morning", "Morning (8 AM–12 PM)"],
  ["afternoon", "Afternoon (12–4 PM)"], ["evening", "Evening (4–8 PM)"]];

// ------------------------------------------------------------------ dates
export const localISO = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
export const todayISO = () => localISO(new Date());
export const maxDateISO = () => { const d = new Date(); d.setMonth(d.getMonth() + 17); return localISO(d); };
export const nextSaturday = () => { const d = new Date(); d.setDate(d.getDate() + ((6 - d.getDay() + 7) % 7 || 7)); return localISO(d); };
export const dayLabel = (iso) => new Date(iso + "T12:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
export const longDay = (iso) => new Date(iso + "T12:00").toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

// ------------------------------------------------------------------ session memory (a per-visitor convenience; the app works without it)
export const mem = {
  get(k) { try { return JSON.parse(sessionStorage.getItem("tn_" + k) || "null"); } catch { return null; } },
  set(k, v) { try { sessionStorage.setItem("tn_" + k, JSON.stringify(v)); } catch { /* storage unavailable */ } },
};

export const exploreUrl = (q, extra = {}) => {
  const p = new URLSearchParams({ lat: q.lat, lon: q.lon, date: q.date });
  if (q.interest) p.set("interest", q.interest);
  if (q.slot && q.slot !== "all") p.set("slot", q.slot);
  if (q.src) p.set("src", q.src);
  Object.entries(extra).forEach(([k, v]) => v && p.set(k, v));
  return `#/explore?${p}`;
};

// ------------------------------------------------------------------ photos
// Images carry width/height boxes from CSS (fixed ratios), lazy loading, and a placeholder if they fail.
export const photo = (img, name, cls = "") => img
  ? `<div class="ph ${cls}"><img src="${esc(img.url)}" alt="Photo of ${esc(name)}" loading="lazy" decoding="async"></div>`
  : `<div class="ph ${cls} broken" role="img" aria-label="No photo available for ${esc(name)}"><span>${esc(name.charAt(0))}</span></div>`;
document.addEventListener("error", (e) => {                // a failed image becomes a clean placeholder (error events do not bubble: capture)
  const t = e.target;
  if (t instanceof HTMLImageElement && t.closest(".ph")) {
    const ph = t.closest(".ph");
    ph.classList.add("broken");
    ph.innerHTML = `<span>${esc((t.alt || "?").replace("Photo of ", "").charAt(0))}</span>`;
  }
}, true);
export const credit = (img) => img ? `<a href="${esc(img.source_page || "#")}" target="_blank" rel="noopener">${esc(img.credit || "Wikimedia Commons")}</a> (${esc(img.licence || "see source")})` : "";

// ------------------------------------------------------------------ crowd timeline (four times of day)
export function timelineMini(tl) {
  return `<ol class="tl" aria-label="Predicted crowd through the day">${tl.map((s) => {
    const c = COLOR[s.level] || "grey";
    const text = s.available ? `${s.label} ${s.range}: ${COLOR_LABEL[c]}${s.best ? ", the calmest period" : ""}` : `${s.label}: closed`;
    return `<li class="${c}${s.best ? " best" : ""}" title="${esc(text)}" aria-label="${esc(text)}"><span class="seg"></span><small>${esc(s.label.split(" ")[0])}</small></li>`;
  }).join("")}</ol>`;
}
export function timelineBig(tl) {
  return `<ol class="tl big" aria-label="Predicted crowd through the day">${tl.map((s) => {
    const c = COLOR[s.level] || "grey";
    return `<li class="${c}${s.best ? " best" : ""}"><b>${esc(s.label)}</b><span>${esc(s.range)}</span>${s.available ? chip(s.level) : '<span class="chip grey"><i></i>Closed</span>'}
      ${s.best ? `<em>${ICON.check} Calmest</em>` : ""}</li>`;
  }).join("")}</ol>`;
}
export const bestLine = (bw) => bw.available
  ? `<p class="bestline">${ICON.clock}<span>Best time to visit: <b>${esc(bw.label)}</b></span></p><p class="note">${esc(bw.message)}</p>`
  : `<p class="bestline off">${ICON.info}<span>No quiet time to recommend</span></p><p class="note">${esc(bw.message)}</p>`;

// ------------------------------------------------------------------ map markers
export const markerIcon = (group, color, selected = false) => L.divIcon({
  className: "mkwrap", iconSize: [34, 34], iconAnchor: [17, 17], popupAnchor: [0, -14],
  html: `<span class="mk ${group} ${color}${selected ? " sel" : ""}">${group === "popular" ? "" : ""}</span>`,
});
export const youIcon = () => L.divIcon({ className: "mkwrap", iconSize: [34, 34], iconAnchor: [17, 17], html: '<span class="mk you"></span>' });

export function newMap(box) {
  return new Promise((resolve) => whenLeafletReady(() => {
    if (!window.L || !box.isConnected) return resolve(null);
    const map = L.map(box, { scrollWheelZoom: false, zoomControl: true }).setView([21.5, 79], 5);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, className: "soft-tiles",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map);
    map.on("click", () => { if (!matchMedia("(pointer: coarse)").matches) map.scrollWheelZoom.enable(); });
    resolve(map);
  }));
}

export const popupHTML = (p, href) => `<div class="pop">${p.image_url ? `<div class="ph pimg"><img src="${esc(p.image_url)}" alt="Photo of ${esc(p.name)}" loading="lazy" decoding="async"></div>` : ""}
  <div class="pbody"><div class="ptop"><b>${esc(p.name)}</b>${chip(p.level)}</div><p class="note">${esc(p.state)} · ${p.distance_km.toLocaleString("en-IN")} km</p>
  <p>${esc(p.blurb)}</p><p class="note">Best time: <b>${esc(p.best_label)}</b></p>
  <a class="btn primary small" href="${esc(href)}">View Details</a></div></div>`;

export { esc, hr };
