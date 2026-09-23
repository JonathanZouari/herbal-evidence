import { $, clear, h } from "../dom.js";
import { publicShell } from "../layout.js";

const me = await publicShell();
if (me) {
  const home = me.role === "user" ? "/requests.html" : "/staff.html";
  clear($("#cta")).append(
    h("a", { class: "btn", href: "/new.html" }, "שליחת בקשה"),
    h("a", { class: "btn secondary", href: home }, me.role === "user" ? "הבקשות שלי" : "לתור הבקשות"));
}
