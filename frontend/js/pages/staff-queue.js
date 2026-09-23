// Staff queue. Researchers see requests assigned to them; admins see all and assign.

import { get, post } from "../api.js";
import { bdi, clear, formatDay, h, param } from "../dom.js";
import { errorMessage, INTERNAL_STATUSES, internalStatus } from "../i18n.js";
import { main, requireAuth, showError, toast } from "../layout.js";

const me = await requireAuth(["researcher", "admin"]);
const root = main();
const isAdmin = me.role === "admin";
let researchers = [];

function badge(code) {
  const s = internalStatus(code);
  return h("span", { class: `badge ${s.tone}`, "data-icon": s.icon }, s.label);
}

function assignControl(r) {
  const sel = h("select", { "aria-label": `שיוך בקשה ${r.herb_name_input} לחוקר/ת` },
    h("option", { value: "" }, "— לא משויך —"),
    researchers.map((x) => h("option", { value: x.id, selected: x.id === r.assigned_researcher_id },
      `${x.display_name || x.email} (${x.open_assigned} פתוחות)`)));
  sel.addEventListener("change", async () => {
    if (!sel.value) return;
    try {
      await post(`/admin/requests/${r.id}/assign`, { researcher_id: sel.value });
      toast("הבקשה שויכה.");
    } catch (e) { toast(errorMessage(e.code)); }
  });
  return sel;
}

async function load(status) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  let rows;
  try {
    [rows, researchers] = await Promise.all([get(`/staff/requests${qs}`), isAdmin ? get("/admin/researchers") : []]);
  } catch (e) { return showError(root, e); }

  const filter = h("select", { id: "status-filter" },
    h("option", { value: "" }, "כל הסטטוסים"),
    INTERNAL_STATUSES.map((s) => h("option", { value: s, selected: s === status }, internalStatus(s).label)));
  filter.addEventListener("change", () => {
    const url = new URL(location.href);
    if (filter.value) url.searchParams.set("status", filter.value); else url.searchParams.delete("status");
    history.replaceState(null, "", url);
    load(filter.value);
  });

  const table = rows.length ? h("div", { class: "table-wrap" }, h("table", {},
    h("caption", { class: "sr-only" }, "רשימת בקשות"),
    h("thead", {}, h("tr", {},
      ["צמח", "סטטוס", isAdmin ? "חוקר/ת" : null, "נשלחה", "עודכנה"].filter(Boolean).map((t) => h("th", { scope: "col" }, t)))),
    h("tbody", {}, rows.map((r) => h("tr", {},
      h("td", {}, h("a", { href: `/staff-request.html?id=${encodeURIComponent(r.id)}` }, bdi(r.herb_name_input)),
        r.herb_name_he && r.herb_name_he !== r.herb_name_input ? h("div", { class: "muted small" }, bdi(r.herb_name_he)) : null,
        !r.herb_id ? h("div", { class: "small" }, h("span", { class: "tag" }, "צמח לא זוהה")) : null),
      h("td", {}, badge(r.status)),
      isAdmin ? h("td", {}, assignControl(r)) : null,
      h("td", {}, formatDay(r.created_at)),
      h("td", {}, formatDay(r.updated_at)))))))
    : h("p", { class: "card" }, "אין בקשות להצגה.");

  clear(root).append(
    h("h1", {}, isAdmin ? "כל הבקשות" : "הבקשות ששויכו אליי"),
    h("div", { class: "field" }, h("label", { for: "status-filter" }, "סינון לפי סטטוס"), filter),
    table);
}

await load(param("status") || "");
