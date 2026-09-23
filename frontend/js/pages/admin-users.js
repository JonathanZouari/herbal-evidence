// Admin: users and roles. An admin cannot change their own role (the backend refuses too).

import { get, patch } from "../api.js";
import { bdi, clear, formatDay, h } from "../dom.js";
import { errorMessage, ROLES } from "../i18n.js";
import { confirmDialog, main, requireAuth, showError, toast } from "../layout.js";

const me = await requireAuth(["admin"]);
const root = main();

function roleSelect(u) {
  const sel = h("select", { "aria-label": `תפקיד עבור ${u.email}`, disabled: u.id === me.id },
    Object.entries(ROLES).map(([v, label]) => h("option", { value: v, selected: v === u.role }, label)));
  sel.addEventListener("change", async () => {
    const ok = await confirmDialog({ title: "שינוי תפקיד", body: `לשנות את התפקיד של ${u.email} ל${ROLES[sel.value]}?`, confirmLabel: "שינוי" });
    if (!ok) { sel.value = u.role; return; }
    try {
      await patch(`/admin/users/${u.id}/role`, { role: sel.value });
      u.role = sel.value;
      toast("התפקיד עודכן.");
    } catch (e) {
      sel.value = u.role;
      toast(errorMessage(e.code));
    }
  });
  return sel;
}

try {
  const users = await get("/admin/users");
  clear(root).append(
    h("h1", {}, "ניהול משתמשים"),
    h("p", { class: "muted" }, "שינוי תפקיד נכנס לתוקף מיד. אי אפשר לשנות את התפקיד של עצמך."),
    h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, ["דוא״ל", "שם", "תפקיד", "נרשם/ה"].map((t) => h("th", { scope: "col" }, t)))),
      h("tbody", {}, users.map((u) => h("tr", {},
        h("td", {}, bdi(u.email)),
        h("td", {}, u.display_name ? bdi(u.display_name) : "—"),
        h("td", {}, roleSelect(u), u.id === me.id ? h("span", { class: "muted small" }, " (את/ה)") : null),
        h("td", {}, formatDay(u.created_at))))))));
} catch (e) {
  showError(root, e);
}
