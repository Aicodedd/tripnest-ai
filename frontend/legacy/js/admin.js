// Admin console (role=admin). The server enforces access; this view only hides itself from others.
import { $, $$, api, esc, toast, hr, pct, isoLocal, nextWeekday, levelPill, cap, fmtWhen, loading, errorBox, empty, state, provenanceBox } from "./core.js";

const TABS = [["alerts", "Capacity alerts"], ["destinations", "Destinations"], ["attractions", "Attractions"], ["users", "Users"],
  ["reviews", "Reviews"], ["reports", "Reported content"], ["listings", "Listings"], ["sources", "Data sources"], ["system", "System & model"]];

export async function admin(el, params) {
  if (!state.user || state.user.role !== "admin") {
    el.innerHTML = `<div class="page">${empty("Administrators only", "Sign in with an administrator account to manage TripNest.")}</div>`;
    return;
  }
  const tab = params.get("tab") || "alerts";
  let stats = {};
  try { stats = await api("/api/admin/stats"); } catch (e) { el.innerHTML = errorBox(e); return; }
  el.innerHTML = `<div class="page"><div class="page-head"><div><h1>Admin console</h1>
      <p>${stats.users} users · ${stats.destinations} destinations · ${stats.attractions} attractions · ${stats.reviews} reviews · ${stats.itineraries} saved trips · ${stats.open_reports} open reports</p></div></div>
    <div class="tabs" role="tablist">${TABS.map(([k, l]) => `<button role="tab" aria-selected="${k === tab}" data-tab="${k}">${esc(l)}${k === "reports" && stats.open_reports ? ` (${stats.open_reports})` : ""}</button>`).join("")}</div>
    <div id="admin-body">${loading()}</div></div>`;
  $$(".tabs button", el).forEach((b) => b.addEventListener("click", () => (location.hash = `#/admin?tab=${b.dataset.tab}`)));
  const body = $("#admin-body");
  try { await VIEWS[tab](body, params); } catch (e) { body.innerHTML = errorBox(e); }
}

const VIEWS = {
  async alerts(body, params) {
    const at = params.get("at") || isoLocal(new Date());
    const draw = async (t) => {
      const r = await api(`/api/admin/alerts?at=${encodeURIComponent(t)}`);
      $("#al").innerHTML = r.items.length ? `<div class="table-wrap"><table class="data"><thead><tr><th>Attraction</th><th>Peak in next 6 h</th><th>Level</th><th>Chance of capacity</th><th>Suggested action</th></tr></thead>
        <tbody>${r.items.map((a) => `<tr><td><a href="#/d/${esc(a.slug.split("-")[0])}">${esc(a.name)}</a><div class="note">${esc(a.destination)}${a.sensitive ? " · fragile site" : ""}</div></td>
          <td>${esc(hr(a.hour))} (${a.lead_hours ? `in ${a.lead_hours} h` : "now"})</td><td>${levelPill(a.level)} ${pct(a.util)}</td><td>${pct(a.p_exceed)}</td><td>${esc(a.action)}</td></tr>`).join("")}</tbody></table></div>${provenanceBox(r.provenance)}`
        : empty("No alerts", "No attraction is forecast to reach High or At capacity in the next six hours.");
    };
    body.innerHTML = `<section class="panel"><header><h2>Forecast alerts</h2><div class="chips"><button class="chip" data-t="now">Now</button><button class="chip" data-t="sat">Saturday 1 PM</button>
      <label class="sr-only" for="al-at">Time</label><input class="input" style="width:auto;min-height:36px" type="datetime-local" id="al-at" value="${esc(at)}"></div></header><div id="al">${loading()}</div></section>`;
    $$("[data-t]", body).forEach((b) => b.addEventListener("click", () => { const t = b.dataset.t === "now" ? isoLocal(new Date()) : isoLocal(nextWeekday(6, 13)); $("#al-at").value = t; draw(t); }));
    $("#al-at").addEventListener("change", (e) => draw(e.target.value));
    await draw(at);
  },

  async destinations(body) {
    const all = [...(await api("/api/destinations?limit=60&sort=name")).items, ...(await api("/api/destinations?limit=60&page=2&sort=name")).items];
    const states = (await api("/api/states")).items;
    body.innerHTML = `<div class="grid12"><section class="panel s8"><header><h2>Destinations (${all.length})</h2></header><div class="table-wrap"><table class="data">
      <thead><tr><th>Name</th><th>State</th><th>Budget</th><th>Featured</th><th></th></tr></thead><tbody>${all.map((d) => `<tr><td><a href="#/d/${esc(d.slug)}">${esc(d.name)}</a></td><td>${esc(d.state.name)}</td><td>${esc(d.budget)}</td>
      <td><button class="btn small quiet" data-feat="${esc(d.slug)}" data-on="${d.featured}">${d.featured ? "Featured" : "Not featured"}</button></td>
      <td><button class="btn small danger" data-deld="${esc(d.slug)}">Delete</button></td></tr>`).join("")}</tbody></table></div></section>
      <section class="panel s4"><header><h2>Add destination</h2></header><form id="nd" style="display:grid;gap:12px">
        <label class="field">Name<input name="name" required maxlength="120"></label>
        <label class="field">Short ID (lowercase-with-dashes)<input name="slug" required pattern="[a-z0-9]+(-[a-z0-9]+)*" maxlength="80"></label>
        <label class="field">State or UT<select name="state_code">${states.map((s) => `<option value="${esc(s.code)}">${esc(s.name)}</option>`).join("")}</select></label>
        <div class="form-grid"><label class="field">Latitude<input name="lat" type="number" step="0.0001" min="6" max="37.5" required></label><label class="field">Longitude<input name="lon" type="number" step="0.0001" min="68" max="98" required></label></div>
        <label class="field">Categories (comma separated)<input name="categories" placeholder="heritage, nature"></label>
        <label class="field">Budget<select name="budget"><option>low</option><option selected>mid</option><option>high</option></select></label>
        <label class="field">Climate<select name="climate">${["plains", "coastal", "mountain", "desert", "tropical"].map((c) => `<option>${c}</option>`).join("")}</select></label>
        <label class="field">Best months (numbers, comma separated)<input name="best_months" placeholder="10, 11, 12, 1, 2"></label>
        <label class="field">Description<textarea name="description" maxlength="2000"></textarea></label>
        <div><button class="btn">Add destination</button></div></form></section></div>`;
    $("#nd").addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = e.target;
      try {
        await api("/api/admin/destinations", { method: "POST", body: { name: f.name.value, slug: f.slug.value, state_code: f.state_code.value, lat: +f.lat.value, lon: +f.lon.value,
          categories: f.categories.value.split(",").map((s) => s.trim()).filter(Boolean), budget: f.budget.value, climate: f.climate.value,
          best_months: f.best_months.value.split(",").map((s) => +s.trim()).filter((n) => n >= 1 && n <= 12), description: f.description.value } });
        toast("Destination added"); VIEWS.destinations(body);
      } catch (err) { toast(err.message, true); }
    });
    $$("[data-feat]", body).forEach((b) => b.addEventListener("click", async () => {
      try { await api(`/api/admin/destinations/${b.dataset.feat}`, { method: "PUT", body: { featured: b.dataset.on !== "true" } }); toast("Updated"); VIEWS.destinations(body); } catch (err) { toast(err.message, true); }
    }));
    $$("[data-deld]", body).forEach((b) => b.addEventListener("click", async () => {
      if (!confirm(`Delete ${b.dataset.deld} and all its attractions, reviews and listings?`)) return;
      try { await api(`/api/admin/destinations/${b.dataset.deld}`, { method: "DELETE" }); toast("Destination deleted"); VIEWS.destinations(body); } catch (err) { toast(err.message, true); }
    }));
  },

  async attractions(body, params) {
    const all = [...(await api("/api/destinations?limit=60&sort=name")).items, ...(await api("/api/destinations?limit=60&page=2&sort=name")).items];
    const sel = params.get("d") || all[0].slug;
    const d = await api(`/api/destinations/${sel}`);
    body.innerHTML = `<section class="panel"><header><h2>Attractions in</h2><select class="input" style="width:auto" id="ad">${all.map((x) => `<option value="${esc(x.slug)}" ${x.slug === sel ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></header>
      <div class="table-wrap"><table class="data"><thead><tr><th>Name</th><th>Category</th><th>Assumed capacity</th><th>Hours</th><th>Fee ₹</th><th>Sensitive</th><th></th></tr></thead><tbody>
      ${d.attractions.map((a) => `<tr data-slug="${esc(a.slug)}"><td>${esc(a.name)}</td><td>${esc(a.category)}</td>
        <td><label class="sr-only" for="c-${esc(a.slug)}">Capacity</label><input class="input" style="width:110px" id="c-${esc(a.slug)}" type="number" min="10" name="capacity" value="${a.capacity}"></td>
        <td>${esc(hr(a.open_hour))}–${esc(hr(a.close_hour))}</td><td><input class="input" style="width:90px" type="number" min="0" name="fee" value="${a.fee}" aria-label="Fee"></td>
        <td><input type="checkbox" name="sensitive" ${a.sensitive ? "checked" : ""} aria-label="Ecologically sensitive"></td>
        <td style="display:flex;gap:6px"><button class="btn small" data-save>Save</button><button class="btn small danger" data-del>Delete</button></td></tr>`).join("")}</tbody></table></div></section>
      <section class="panel" style="margin-top:16px"><header><h2>Add attraction to ${esc(d.name)}</h2></header><form id="na" class="form-grid">
        <label class="field">Name<input name="name" required maxlength="140"></label>
        <label class="field">Category<select name="category">${["heritage", "spiritual", "beach", "nature", "waterfall", "lake", "viewpoint", "wildlife", "museum", "market", "garden", "adventure", "plantation", "river"].map((c) => `<option>${c}</option>`).join("")}</select></label>
        <label class="field">Latitude<input name="lat" type="number" step="0.0001" required value="${d.lat}"></label><label class="field">Longitude<input name="lon" type="number" step="0.0001" required value="${d.lon}"></label>
        <label class="field">Assumed capacity<input name="capacity" type="number" min="10" required value="500"></label>
        <label class="field">Opens (hour)<input name="open_hour" type="number" min="0" max="23" value="9"></label><label class="field">Closes (hour)<input name="close_hour" type="number" min="1" max="24" value="18"></label>
        <label class="field">Fee ₹<input name="fee" type="number" min="0" value="0"></label>
        <div><button class="btn">Add attraction</button></div></form></section>`;
    $("#ad").addEventListener("change", (e) => (location.hash = `#/admin?tab=attractions&d=${e.target.value}`));
    $$("[data-save]", body).forEach((b) => b.addEventListener("click", async () => {
      const tr = b.closest("tr");
      try { await api(`/api/admin/attractions/${tr.dataset.slug}`, { method: "PUT", body: { capacity: +tr.querySelector("[name=capacity]").value, fee: +tr.querySelector("[name=fee]").value, sensitive: tr.querySelector("[name=sensitive]").checked } }); toast("Attraction saved; forecasts now use the new values"); } catch (err) { toast(err.message, true); }
    }));
    $$("[data-del]", body).forEach((b) => b.addEventListener("click", async () => {
      const tr = b.closest("tr");
      if (!confirm("Delete this attraction?")) return;
      try { await api(`/api/admin/attractions/${tr.dataset.slug}`, { method: "DELETE" }); toast("Attraction deleted"); VIEWS.attractions(body, params); } catch (err) { toast(err.message, true); }
    }));
    $("#na").addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = e.target;
      try {
        await api("/api/admin/attractions", { method: "POST", body: { destination: sel, name: f.name.value, category: f.category.value, lat: +f.lat.value, lon: +f.lon.value,
          capacity: +f.capacity.value, open_hour: +f.open_hour.value, close_hour: +f.close_hour.value, fee: +f.fee.value } });
        toast("Attraction added; it gets forecasts immediately"); VIEWS.attractions(body, params);
      } catch (err) { toast(err.message, true); }
    });
  },

  async users(body) {
    const r = await api("/api/admin/users");
    body.innerHTML = `<section class="panel"><header><h2>Users (${r.items.length})</h2></header><div class="table-wrap"><table class="data"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Joined</th><th></th></tr></thead><tbody>
      ${r.items.map((u) => `<tr><td>${esc(u.name)}</td><td>${esc(u.email)}</td><td>${esc(u.role)}</td><td>${u.is_active ? "Active" : "Deactivated"}</td><td>${esc(fmtWhen(u.created_at))}</td>
        <td style="display:flex;gap:6px;flex-wrap:wrap">${u.id === state.user.id ? '<span class="note">You</span>' : `<button class="btn small quiet" data-u="${u.id}" data-k="is_active" data-v="${!u.is_active}">${u.is_active ? "Deactivate" : "Reactivate"}</button>
        <button class="btn small quiet" data-u="${u.id}" data-k="role" data-v="${u.role === "admin" ? "traveller" : "admin"}">${u.role === "admin" ? "Make traveller" : "Make admin"}</button>`}</td></tr>`).join("")}</tbody></table></div></section>`;
    $$("[data-u]", body).forEach((b) => b.addEventListener("click", async () => {
      const v = b.dataset.k === "is_active" ? b.dataset.v === "true" : b.dataset.v;
      try { await api(`/api/admin/users/${b.dataset.u}`, { method: "PATCH", body: { [b.dataset.k]: v } }); toast("User updated"); VIEWS.users(body); } catch (err) { toast(err.message, true); }
    }));
  },

  async reviews(body, params) {
    const src = params.get("source") || "user";
    const r = await api(`/api/admin/reviews?source=${src}`);
    body.innerHTML = `<section class="panel"><header><h2>Reviews</h2><div class="chips"><a class="chip" href="#/admin?tab=reviews&source=user" aria-pressed="${src === "user"}" style="display:inline-flex;align-items:center;text-decoration:none">Traveller reviews</a><a class="chip" href="#/admin?tab=reviews&source=demo" aria-pressed="${src === "demo"}" style="display:inline-flex;align-items:center;text-decoration:none">Demo reviews</a></div></header>
      ${r.items.length ? `<div class="table-wrap"><table class="data"><thead><tr><th>Review</th><th>Author</th><th>Rating</th><th>Sentiment</th><th>Status</th><th></th></tr></thead><tbody>
      ${r.items.map((x) => `<tr><td style="max-width:460px">${esc(x.text)}</td><td>${esc(x.author)}</td><td>${x.rating}/5</td><td>${esc(x.sentiment)}</td><td>${esc(x.status)}</td>
        <td><button class="btn small quiet" data-rv="${x.id}" data-to="${x.status === "visible" ? "hidden" : "visible"}">${x.status === "visible" ? "Hide" : "Show"}</button></td></tr>`).join("")}</tbody></table></div>` : empty("No reviews", "Nothing to moderate here yet.")}</section>`;
    $$("[data-rv]", body).forEach((b) => b.addEventListener("click", async () => {
      try { await api(`/api/admin/reviews/${b.dataset.rv}`, { method: "PATCH", body: { status: b.dataset.to } }); toast(b.dataset.to === "hidden" ? "Review hidden" : "Review visible"); VIEWS.reviews(body, params); } catch (err) { toast(err.message, true); }
    }));
  },

  async reports(body) {
    const r = await api("/api/admin/content-reports?status=open");
    body.innerHTML = `<section class="panel"><header><h2>Open reports</h2></header>${r.items.length ? `<div class="rows">${r.items.map((x) => `<div class="row" style="display:grid;grid-template-columns:1fr auto;gap:12px">
      <div><strong>${esc(cap(x.target_type))} #${x.target_id}</strong> <span class="meta">reported by ${esc(x.reporter)}, ${esc(fmtWhen(x.created_at))}</span><p style="margin-top:4px">Reason: ${esc(x.reason)}</p>
      <p class="note">${x.preview ? "“" + esc(x.preview) + "”" : "The content no longer exists."}</p></div>
      <div style="display:flex;gap:6px;align-items:start"><button class="btn small danger" data-rp="${x.id}" data-hide="true">Hide content</button><button class="btn small quiet" data-rp="${x.id}" data-hide="false">Dismiss</button></div></div>`).join("")}</div>`
      : empty("No open reports", "Reported posts, comments and reviews will appear here.")}</section>`;
    $$("[data-rp]", body).forEach((b) => b.addEventListener("click", async () => {
      const hide = b.dataset.hide === "true";
      try { await api(`/api/admin/content-reports/${b.dataset.rp}`, { method: "PATCH", body: { status: hide ? "actioned" : "dismissed", hide_target: hide } }); toast(hide ? "Content hidden" : "Report dismissed"); VIEWS.reports(body); } catch (err) { toast(err.message, true); }
    }));
  },

  async listings(body) {
    const r = await api("/api/admin/listings");
    const all = [...(await api("/api/destinations?limit=60&sort=name")).items, ...(await api("/api/destinations?limit=60&page=2&sort=name")).items];
    body.innerHTML = `<div class="grid12"><section class="panel s8"><header><h2>Listings (${r.items.length})</h2></header><div class="table-wrap"><table class="data"><thead><tr><th>Name</th><th>Destination</th><th>Kind</th><th>Source</th><th>Verified</th><th></th></tr></thead><tbody>
      ${r.items.map((l) => `<tr><td>${esc(l.name)}</td><td>${esc(l.destination)}</td><td>${esc(l.kind)}</td><td>${esc(l.source)}</td>
        <td><button class="btn small quiet" data-ver="${l.id}" data-v="${!l.verified}">${l.verified ? "Verified" : "Mark verified"}</button></td><td><button class="btn small danger" data-dl="${l.id}">Delete</button></td></tr>`).join("")}</tbody></table></div></section>
      <section class="panel s4"><header><h2>Add listing</h2></header><form id="nl" style="display:grid;gap:12px">
        <label class="field">Destination<select name="destination">${all.map((d) => `<option value="${esc(d.slug)}">${esc(d.name)}</option>`).join("")}</select></label>
        <label class="field">Business name<input name="name" required maxlength="120"></label>
        <label class="field">Kind<select name="kind">${["homestay", "food", "guide", "shop", "transport"].map((k) => `<option>${k}</option>`).join("")}</select></label>
        <label class="field">Description<textarea name="description" maxlength="1000"></textarea></label>
        <label class="field">Contact<input name="contact" maxlength="120"></label><div><button class="btn">Add listing</button></div></form></section></div>`;
    $("#nl").addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = e.target;
      try { await api("/api/admin/listings", { method: "POST", body: { destination: f.destination.value, name: f.name.value, kind: f.kind.value, description: f.description.value, contact: f.contact.value || null } }); toast("Listing added"); VIEWS.listings(body); } catch (err) { toast(err.message, true); }
    });
    $$("[data-ver]", body).forEach((b) => b.addEventListener("click", async () => {
      try { await api(`/api/admin/listings/${b.dataset.ver}`, { method: "PUT", body: { verified: b.dataset.v === "true" } }); toast("Listing updated"); VIEWS.listings(body); } catch (err) { toast(err.message, true); }
    }));
    $$("[data-dl]", body).forEach((b) => b.addEventListener("click", async () => {
      if (!confirm("Delete this listing?")) return;
      try { await api(`/api/admin/listings/${b.dataset.dl}`, { method: "DELETE" }); toast("Listing deleted"); VIEWS.listings(body); } catch (err) { toast(err.message, true); }
    }));
  },

  async sources(body) {
    const r = await api("/api/admin/data-sources");
    body.innerHTML = `<section class="panel"><header><h2>Data sources</h2></header><div class="rows">${r.items.map((s) => `<div class="row"><div><strong>${esc(s.name)}</strong> <span class="tag ${s.kind === "demonstration" ? "demo" : s.kind === "live" ? "live" : ""}">${esc(cap(s.kind))}</span>
      <div class="meta">${esc(s.description)}${s.last_updated ? ` Updated ${esc(fmtWhen(s.last_updated))}.` : ""}</div></div>
      <button class="switch" role="switch" style="font-size:1rem" aria-checked="${s.enabled}" aria-label="${esc(s.name)} enabled" data-src="${esc(s.key)}"></button></div>`).join("")}</div>
      <p class="note" style="margin-top:10px">Turning off Open-Meteo shows travellers a clear “weather unavailable” message instead of calling the service.</p></section>`;
    $$("[data-src]", body).forEach((b) => b.addEventListener("click", async () => {
      const on = b.getAttribute("aria-checked") !== "true";
      try { await api(`/api/admin/data-sources/${b.dataset.src}`, { method: "PATCH", body: { enabled: on } }); b.setAttribute("aria-checked", on); toast(on ? "Source enabled" : "Source disabled"); } catch (err) { toast(err.message, true); }
    }));
  },

  async system(body) {
    const s = await api("/api/admin/system");
    const m = s.model;
    body.innerHTML = `<div class="grid12"><section class="panel s5"><header><h2>Application status</h2></header><div class="rows">
      ${[["Database", `${s.database} (${s.database_engine})`], ["Environment", s.environment], ["Weather provider", s.weather_provider], ["LLM narrative", s.llm_configured ? "Key configured" : "Not configured (off by default)"],
         ["Uptime", `${Math.round(s.uptime_seconds / 60)} min`], ["Server time", fmtWhen(s.server_time)]].map(([k, v]) => `<div class="row"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join("")}</div></section>
      <section class="panel s7"><header><h2>Crowd model</h2></header><p>${esc(m.backend)}, trained ${esc(fmtWhen(m.trained_at))} on ${m.history_days} days × ${m.attractions} attractions.</p>
        <table class="data" style="margin-top:12px"><thead><tr><th>Test fortnight</th><th>MAPE</th><th>WAPE</th><th>MAE</th><th>R²</th></tr></thead><tbody>
        <tr><td><strong>Model</strong></td><td>${m.test_metrics.mape}%</td><td>${m.test_metrics.wape}%</td><td>${m.test_metrics.mae}</td><td>${m.test_metrics.r2}</td></tr>
        ${Object.entries(m.baselines).map(([k, b]) => `<tr><td>${esc(b.description)}</td><td>${b.mape}%</td><td>${b.wape}%</td><td>${b.mae}</td><td>${b.r2}</td></tr>`).join("")}</tbody></table>
        <p class="note" style="margin-top:10px">${esc(m.note)}</p><p class="note">Retrain: <code>python -m scripts.train_model --days 365</code></p></section></div>`;
  },
};
