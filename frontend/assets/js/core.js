// Shared helpers: API client, escaping, formatting, charts, map, toasts.

const narrow = () => window.innerWidth < 640; // draw charts at a smaller size on phones so their text stays readable
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
// Write target for async results: if the visitor already left the page, the write goes to a detached node.
export const out = (sel, root = document) => root.querySelector(sel) || document.createElement("div");

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
// Every value from the API or the user passes through esc() before it reaches innerHTML.
export const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ESC[c]);

export const state = { user: null, states: null, categories: null };

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

function detailText(d) {
  if (!d) return "Request failed";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((e) => {
      const field = (e.loc || []).filter((x) => x !== "body").join(" ");
      return field ? `${field}: ${e.msg}` : e.msg;
    }).join(". ");
  }
  return "Request failed";
}

export async function api(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: { "X-Requested-With": "TripNest", ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Can't reach TripNest. Check your connection and try again.", 0);
  }
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) throw new ApiError(detailText(data && data.detail), res.status);
  return data;
}

let toastTimer;
export function toast(msg, isError = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (isError ? " err" : "");
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 3800);
}

export const hr = (h) => `${h % 12 || 12} ${h < 12 || h === 24 ? "AM" : "PM"}`;
export const hrRange = (o, c) => (o === 0 && c === 24 ? "Open all day" : `${hr(o)} – ${hr(c)}`);
export const pct = (u) => `${Math.round(u * 100)}%`;
export const inr = (n) => "₹" + Number(n).toLocaleString("en-IN");
export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const fmtDate = (iso) => new Date(iso + (iso.length === 10 ? "T00:00" : "")).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
export const fmtWhen = (iso) => new Date(iso).toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
export const levelClass = (l) => "lv-" + String(l).replace(/\s+/g, "-");
export const levelPill = (l) => `<span class="pill ${levelClass(l)}">${esc(l)}</span>`;
export const cap = (s) => String(s || "").charAt(0).toUpperCase() + String(s || "").slice(1);

export function isoLocal(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}
export const todayISO = () => isoLocal(new Date()).slice(0, 10);
export function nextWeekday(dow, hour) { // dow: 0=Sun..6=Sat
  const d = new Date();
  d.setDate(d.getDate() + ((dow - d.getDay() + 7) % 7 || 7));
  d.setHours(hour, 0, 0, 0);
  return d;
}

export function provenanceBox(p, extra = "") {
  if (!p) return "";
  const when = p.generated_at ? `Generated ${esc(fmtWhen(p.generated_at))}` : "";
  const trained = p.model_trained_at ? `model trained ${esc(fmtWhen(p.model_trained_at))}` : "";
  return `<div class="provenance" role="note"><strong>Demonstration data</strong>
    <span>${esc(p.note || "")}</span><span>${[when, trained].filter(Boolean).join(" · ")}</span>${extra}</div>`;
}

export const loading = (msg = "Loading") => `<p class="loading">${esc(msg)}</p>`;
export const errorBox = (e) => `<div class="error-box" role="alert">${esc(e.message || e)}</div>`;
export const empty = (title, text, action = "") => `<div class="empty"><strong>${esc(title)}</strong>${esc(text)} ${action}</div>`;

// ------------------------------------------------------------------ charts (inline SVG, single hue)
export function forecastChart(hourly, { selected = null, height = 220, label = "Hourly crowd forecast" } = {}) {
  if (!hourly || !hourly.length) return empty("No forecast", "This place is closed on the selected day.");
  const W = narrow() ? 320 : 720, H = height, padL = 34, padB = 26, padT = 10;
  const n = hourly.length, bw = (W - padL) / n;
  const maxU = Math.max(1.0, ...hourly.map((h) => h.high / Math.max(1, h.visitors / Math.max(h.util, 0.001))));
  const capU = Math.max(1.05, ...hourly.map((h) => h.util * 1.15));
  const y = (u) => padT + (H - padT - padB) * (1 - Math.min(u, capU) / capU);
  const peak = hourly.reduce((a, b) => (b.util > a.util ? b : a));
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}: busiest at ${esc(hr(peak.hour))} (${esc(peak.level)}, about ${esc(peak.visitors)} people).">`;
  [0.4, 0.7, 0.9].forEach((t) => {
    s += `<line class="thr" x1="${padL}" x2="${W}" y1="${y(t)}" y2="${y(t)}"/><text x="0" y="${y(t) + 4}">${t * 100}%</text>`;
  });
  hourly.forEach((h, i) => {
    const x = padL + i * bw + 2;
    const capPeople = h.util > 0 ? h.visitors / h.util : 0;
    const lo = capPeople ? h.low / capPeople : 0, hi = capPeople ? h.high / capPeople : 0;
    s += `<rect class="band" x="${x}" y="${y(hi)}" width="${bw - 4}" height="${Math.max(1, y(lo) - y(hi))}" opacity=".7"/>`;
    s += `<rect class="bar lvb-${esc(String(h.level).replace(/\s+/g, "-"))}${selected === h.hour ? " sel" : ""}" x="${x + bw * 0.22}" y="${y(h.util)}" width="${Math.max(2, bw * 0.56 - 4)}" height="${H - padB - y(h.util)}" rx="3"><title>${esc(hr(h.hour))}: ${esc(h.level)}, ~${esc(h.visitors)} people (${esc(h.low)}–${esc(h.high)})</title></rect>`;
    if (i % Math.ceil(n / (narrow() ? 5 : 9)) === 0) s += `<text x="${x}" y="${H - 8}">${esc(hr(h.hour))}</text>`;
  });
  void maxU;
  return s + "</svg>";
}

export function lineChart(series, { height = 260 } = {}) {
  const hours = [...new Set(series.flatMap((s) => s.points.map((p) => p.hour)))].sort((a, b) => a - b);
  if (!hours.length) return empty("Nothing to compare", "None of these places is open on that day.");
  const W = narrow() ? 320 : 720, H = height, padL = 34, padB = 26, padT = 10;
  const x0 = hours[0], x1 = hours[hours.length - 1];
  const x = (h) => padL + ((h - x0) / Math.max(1, x1 - x0)) * (W - padL - 10);
  const capU = Math.max(1.0, ...series.flatMap((s) => s.points.map((p) => p.util)));
  const y = (u) => padT + (H - padT - padB) * (1 - u / capU);
  const shades = ["#3d0012", "#b0125a", "#e0789f", "#7a5260", "#c9a3b5"];
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Hourly crowd comparison">`;
  [0.4, 0.7, 0.9].forEach((t) => (s += `<line class="thr" x1="${padL}" x2="${W}" y1="${y(t)}" y2="${y(t)}"/><text x="0" y="${y(t) + 4}">${t * 100}%</text>`));
  hours.forEach((h, i) => { if (i % (narrow() ? 4 : 2) === 0) s += `<text x="${x(h) - 8}" y="${H - 8}">${esc(hr(h))}</text>`; });
  series.forEach((sr, i) => {
    const d = sr.points.map((p, j) => `${j ? "L" : "M"}${x(p.hour).toFixed(1)},${y(p.util).toFixed(1)}`).join(" ");
    s += `<path d="${d}" fill="none" stroke="${shades[i % 5]}" stroke-width="${i === 0 ? 3.5 : 2.5}" stroke-linejoin="round"/>`;
  });
  s += "</svg>";
  s += `<div class="legend">${series.map((sr, i) => `<span><i style="background:${shades[i % 5]}"></i>${esc(sr.name)}</span>`).join("")}</div>`;
  return s;
}

export function barRow(values, labels, { height = 120 } = {}) {
  const W = 720, H = height, max = Math.max(0.01, ...values), bw = W / values.length;
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H + 20}" role="img" aria-label="Pattern chart">`;
  values.forEach((v, i) => {
    const h = (H - 6) * (v / max);
    s += `<rect class="bar" x="${i * bw + 4}" y="${H - h}" width="${bw - 8}" height="${h}" rx="3"><title>${esc(labels[i])}: ${esc(pct(v))}</title></rect>`;
    s += `<text x="${i * bw + 4}" y="${H + 16}">${esc(labels[i])}</text>`;
  });
  return s + "</svg>";
}

// The crowd curve as a filled silhouette (landing motif and auth art).
export function curvePath(hourly, W, H, { baseline = H } = {}) {
  if (!hourly.length) return "";
  const maxU = Math.max(...hourly.map((h) => h.util), 0.01);
  const pts = hourly.map((h, i) => [(i / (hourly.length - 1)) * W, H - (h.util / maxU) * H * 0.82]);
  let d = `M0,${baseline} L0,${pts[0][1].toFixed(1)}`;
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1], [x1, y1] = pts[i], mx = (x0 + x1) / 2;
    d += ` C${mx.toFixed(1)},${y0.toFixed(1)} ${mx.toFixed(1)},${y1.toFixed(1)} ${x1.toFixed(1)},${y1.toFixed(1)}`;
  }
  return d + ` L${W},${baseline} Z`;
}

// ------------------------------------------------------------------ map (Leaflet + OpenStreetMap)
const LEVEL_FILL = { Low: "#0b5a4b", Moderate: "#a07800", High: "#c2541b", "At Capacity": "#3d0012", Closed: "#8a7a82" };
export function makeMap(el, { center = [22.5, 79], zoom = 5 } = {}) {
  if (!window.L) {
    el.innerHTML = empty("Map unavailable", "The map library could not load. The list on this page has the same places.");
    return null;
  }
  const map = L.map(el, { scrollWheelZoom: false }).setView(center, zoom);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  return map;
}
export function dot(map, lat, lon, { level = null, radius = 8, popup = "" } = {}) {
  const fill = level ? LEVEL_FILL[level] || "#3d0012" : "#3d0012";
  const m = L.circleMarker([lat, lon], { radius, color: "#fff", weight: 2, fillColor: fill, fillOpacity: 0.95 }).addTo(map);
  if (popup) m.bindPopup(popup);
  return m;
}

export function whenLeafletReady(cb) {
  if (window.L) return cb();
  let tries = 0;
  const t = setInterval(() => { if (window.L || ++tries > 40) { clearInterval(t); cb(); } }, 100);
}

// Entrance: content stays visible if this never runs.
export function reveal(root = document) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) return;
  const els = $$(".rise", root);
  els.forEach((el) => el.classList.add("pre"));
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("in"); e.target.classList.remove("pre"); io.unobserve(e.target); }
  }), { threshold: 0.12 });
  els.forEach((el, i) => { el.style.transitionDelay = `${(i % 4) * 75}ms`; io.observe(el); });
}
