// Repository of reusable evidence reviews (staff). ?id= shows one review.

import { get } from "../api.js";
import { bdi, clear, extLink, formatDate, h, param } from "../dom.js";
import { EVIDENCE_BASE } from "../i18n.js";
import { main, requireAuth, showError } from "../layout.js";
import { renderContent } from "../render/response.js";

await requireAuth(["researcher", "admin"]);
const root = main();

async function detail(id) {
  let r;
  try { r = await get(`/staff/reviews/${encodeURIComponent(id)}`); } catch (e) { return showError(root, e); }
  clear(root).append(
    h("p", {}, h("a", { href: "/reviews.html" }, "← חזרה למאגר")),
    h("div", { class: "card stack" },
      h("h1", {}, `${r.herb_name_he} — גרסה ${r.version}`),
      h("p", { class: "muted" }, `אושרה ${r.approved_at ? formatDate(r.approved_at) : "—"}`, r.approved_by_name ? ` על ידי ${r.approved_by_name}` : ""),
      h("p", { class: "callout info" }, "סקירה זו משמשת בסיס לטיוטות חדשות לאותו צמח. כל תשובה אישית עדיין דורשת אישור של החוקר/ת המשויך/ת."),
      renderContent(r.content, { personal: false }),
      r.sources.length ? h("section", {}, h("h2", {}, "מקורות מקושרים במאגר"),
        h("ul", {}, r.sources.map((s) => h("li", {}, extLink(s.url, s.title), h("span", { class: "muted small" }, " · ", bdi(String(s.pub_year || ""))))))) : null));
}

async function list(herbId) {
  let rows, herbs;
  try { [rows, herbs] = await Promise.all([get(`/staff/reviews${herbId ? `?herb_id=${encodeURIComponent(herbId)}` : ""}`), get("/herbs")]); }
  catch (e) { return showError(root, e); }
  const filter = h("select", { id: "herb-filter" }, h("option", { value: "" }, "כל הצמחים"),
    herbs.map((x) => h("option", { value: x.id, selected: String(x.id) === String(herbId) }, x.name_he)));
  filter.addEventListener("change", () => list(filter.value));
  clear(root).append(
    h("h1", {}, "מאגר סקירות"),
    h("p", { class: "muted" }, "סקירות מאושרות לפי צמח. גרסה חדשה נוצרת משמירת תשובה שפורסמה."),
    h("div", { class: "field" }, h("label", { for: "herb-filter" }, "צמח"), filter),
    rows.length ? h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, ["צמח", "גרסה", "בסיס הראיות", "מקורות", "אושרה"].map((t) => h("th", { scope: "col" }, t)))),
      h("tbody", {}, rows.map((r) => h("tr", {},
        h("td", {}, h("a", { href: `/reviews.html?id=${encodeURIComponent(r.id)}` }, r.herb_name_he)),
        h("td", {}, String(r.version)),
        h("td", {}, r.schema_version === "1" ? EVIDENCE_BASE[r.evidence_base] || r.evidence_base : h("span", { class: "tag" }, "פורמט ישן / דמה")),
        h("td", {}, String(r.source_count)),
        h("td", {}, r.approved_at ? formatDate(r.approved_at) : "—"))))))
      : h("p", { class: "card" }, "אין עדיין סקירות."));
}

const id = param("id");
if (id) await detail(id);
else await list("");
