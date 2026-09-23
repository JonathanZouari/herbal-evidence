// "My requests": status in words + icon. No ETA, no queue position (spec).

import { get } from "../api.js";
import { bdi, clear, formatDay, h } from "../dom.js";
import { publicStatus } from "../i18n.js";
import { main, requireAuth, showError } from "../layout.js";

await requireAuth();
const root = main();

function badge(code) {
  const s = publicStatus(code);
  return h("span", { class: `badge ${s.tone}`, "data-icon": s.icon }, s.label);
}

try {
  const rows = await get("/requests");
  const header = h("div", { class: "row spread" }, h("h1", {}, "הבקשות שלי"), h("a", { class: "btn", href: "/new.html" }, "בקשה חדשה"));
  if (!rows.length) {
    clear(root).append(header, h("div", { class: "card" },
      h("p", {}, "עדיין לא שלחת בקשות."),
      h("a", { href: "/new.html" }, "לשליחת בקשה ראשונה")));
  } else {
    clear(root).append(header, h("ul", { class: "stack", role: "list" }, rows.map((r) =>
      h("li", {},
        h("a", { class: "card list-card", href: `/request.html?id=${encodeURIComponent(r.id)}` },
          h("div", { class: "row spread" }, h("h2", {}, bdi(r.herb_name_input)), badge(r.public_status)),
          h("p", { class: "muted small" }, `נשלחה ב-${formatDay(r.created_at)}`),
          h("p", { class: "small" }, publicStatus(r.public_status).help))))));
  }
} catch (e) {
  showError(root, e);
}
