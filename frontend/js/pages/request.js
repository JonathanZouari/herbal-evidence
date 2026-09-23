// A user's request: status in words, clarification answers, the approved response, withdraw.

import { get, post } from "../api.js";
import { bdi, charCounter, clear, formatDate, h, param } from "../dom.js";
import { errorMessage, publicStatus } from "../i18n.js";
import { confirmDialog, main, requireAuth, showError, toast } from "../layout.js";
import { renderContent } from "../render/response.js";

await requireAuth();
const root = main();
const id = param("id");

function badge(code) {
  const s = publicStatus(code);
  return h("span", { class: `badge ${s.tone}`, "data-icon": s.icon }, s.label);
}

function details(r) {
  const row = (label, value) => h("div", {}, h("dt", { class: "muted small" }, label), h("dd", {}, value ? bdi(value) : "לא צוין"));
  return h("dl", { class: "grid-3" },
    row("צורת שימוש", r.preparation), row("סוג הסרטן", r.cancer_type), row("טיפול נוכחי", r.treatment));
}

function clarifications(r) {
  const open = r.clarifications.filter((c) => !c.answer);
  const done = r.clarifications.filter((c) => c.answer);
  if (!r.clarifications.length) return null;
  return h("section", { class: "card stack", "aria-labelledby": "clar-title" },
    h("h2", { id: "clar-title" }, "שאלות מהחוקר/ת"),
    open.map((c) => {
      const ta = h("textarea", { id: `ans-${c.id}`, required: true, maxlength: 2000, rows: 3, "aria-describedby": `ans-${c.id}-err` });
      const err = h("span", { class: "error-text", id: `ans-${c.id}-err` });
      const form = h("form", {},
        h("div", { class: "field" },
          h("label", { for: ta.id }, bdi(c.question)),
          h("span", { class: "hint" }, `נשאל ב-${formatDate(c.asked_at)}`), ta, charCounter(ta), err),
        h("button", { class: "btn", type: "submit" }, "שליחת תשובה"));
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!ta.value.trim()) { err.textContent = "יש לכתוב תשובה."; ta.setAttribute("aria-invalid", "true"); ta.focus(); return; }
        try {
          await post(`/requests/${id}/clarifications/${c.id}/answer`, { text: ta.value.trim() });
          toast("התשובה נשלחה. תודה!");
          await load();
        } catch (ex) { err.textContent = errorMessage(ex.code); ta.focus(); }
      });
      return form;
    }),
    done.length ? h("ul", {}, done.map((c) => h("li", {}, h("strong", {}, bdi(c.question)), h("br"), bdi(c.answer)))) : null);
}

async function withdraw(published) {
  const body = published
    ? "לאחר הביטול התשובה שפורסמה לא תוצג לך יותר, ולא ניתן יהיה לחדש את הבקשה."
    : "לאחר הביטול לא ניתן יהיה לחדש את הבקשה.";
  const ok = await confirmDialog({ title: "ביטול הבקשה", body, confirmLabel: "ביטול הבקשה", danger: true });
  if (!ok) return;
  try {
    await post(`/requests/${id}/withdraw`);
    toast("הבקשה בוטלה.");
    await load();
  } catch (e) { toast(errorMessage(e.code)); }
}

async function load() {
  let r;
  try { r = await get(`/requests/${encodeURIComponent(id)}`); } catch (e) { return showError(root, e); }
  const s = publicStatus(r.public_status);
  const canWithdraw = !["withdrawn", "closed"].includes(r.public_status);
  clear(root).append(
    h("p", {}, h("a", { href: "/requests.html" }, "← חזרה לבקשות שלי")),
    param("new") ? h("div", { class: "callout", role: "status" }, h("p", {}, "הבקשה התקבלה. נעדכן כאן כשתהיה תשובה.")) : null,
    h("div", { class: "card stack" },
      h("div", { class: "row spread" }, h("h1", {}, bdi(r.herb_name_input)), badge(r.public_status)),
      h("p", {}, s.help),
      h("p", { class: "muted small" }, `נשלחה ב-${formatDate(r.created_at)}`),
      details(r)),
    clarifications(r),
    r.response ? h("article", { class: "card stack", "aria-labelledby": "resp-title" },
      h("h2", { id: "resp-title" }, "התשובה לבקשה שלך"),
      h("p", { class: "badge done", "data-icon": "✔" }, "נבדקה ואושרה על ידי חוקר/ת"),
      h("p", { class: "muted small" }, `פורסמה ב-${formatDate(r.response.published_at)}`),
      renderContent(r.response.body)) : null,
    canWithdraw ? h("p", {}, h("button", { class: "btn danger", type: "button", onclick: () => withdraw(r.public_status === "published") }, "ביטול הבקשה")) : null);
}

if (!id) showError(root, { code: "not_found" });
else await load();
