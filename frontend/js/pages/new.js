// New request: herb (list + free text) and three optional fields, each with an explicit "I don't know".

import { get, post } from "../api.js";
import { clear, h } from "../dom.js";
import { errorMessage } from "../i18n.js";
import { main, requireAuth } from "../layout.js";

await requireAuth();
const root = main();

const OPTIONAL = [
  { name: "preparation", label: "צורת השימוש בצמח", hint: "למשל: תה, כמוסות, תבלין באוכל", max: 500 },
  { name: "cancer_type", label: "סוג הסרטן", hint: "אפשר לכתוב באופן כללי", max: 200 },
  { name: "treatment", label: "הטיפול הנוכחי", hint: "למשל: כימותרפיה, הקרנות", max: 500 },
];

let herbs = [];
try { herbs = await get("/herbs"); } catch { herbs = []; }

const errorBox = h("div", { id: "errors", tabindex: "-1" });
const herbInput = h("input", { id: "herb", name: "herb", type: "text", list: "herb-list", required: true, maxlength: 200,
  autocomplete: "off", "aria-describedby": "herb-hint herb-error" });
const herbError = h("span", { id: "herb-error", class: "error-text" });

function optionalField({ name, label, hint, max }) {
  const input = h("textarea", { id: name, name, rows: 2, maxlength: max, "aria-describedby": `${name}-hint` });
  const unknown = h("input", { type: "checkbox", id: `${name}-unknown`, checked: true });
  const sync = () => { input.disabled = unknown.checked; if (unknown.checked) input.value = ""; };
  unknown.addEventListener("change", () => { sync(); if (!unknown.checked) input.focus(); });
  sync();
  return {
    name, input, unknown,
    node: h("fieldset", { class: "field" },
      h("legend", {}, label, h("span", { class: "muted small" }, " (לא חובה)")),
      h("label", { class: "check", for: `${name}-unknown` }, unknown, "לא ידוע / מעדיף/ה לא לציין"),
      h("span", { class: "hint", id: `${name}-hint` }, hint),
      h("label", { class: "sr-only", for: name }, label),
      input),
  };
}

const optional = OPTIONAL.map(optionalField);
const submit = h("button", { class: "btn", type: "submit" }, "שליחת הבקשה");
const form = h("form", { novalidate: true },
  h("div", { class: "field" },
    h("label", { for: "herb" }, "שם הצמח"),
    h("span", { class: "hint", id: "herb-hint" }, "אפשר לבחור מהרשימה או להקליד שם אחר. צמח אחד בלבד."),
    herbInput, herbError,
    h("datalist", { id: "herb-list" }, herbs.map((x) => h("option", { value: x.name_he }, x.name_en || "")))),
  optional.map((f) => f.node),
  h("p", { class: "callout", role: "note" }, "לא נבקש מסמכים רפואיים, תעודת זהות או פרטים מזהים. התשובה תסכם מחקרים ולא תכלול המלצה או מינון."),
  submit);

clear(root).append(h("div", { class: "card" }, h("h1", {}, "בקשה חדשה"), errorBox, form));

function showErrors(messages) {
  clear(errorBox).append(h("div", { class: "error-summary", role: "alert" },
    h("h2", {}, "לא ניתן לשלוח את הבקשה"), h("ul", {}, messages.map((m) => h("li", {}, m)))));
  errorBox.focus();
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  herbError.textContent = "";
  herbInput.removeAttribute("aria-invalid");
  const herb = herbInput.value.trim();
  if (!herb) {
    herbError.textContent = "יש לכתוב שם של צמח.";
    herbInput.setAttribute("aria-invalid", "true");
    showErrors(["יש לכתוב שם של צמח."]);
    herbInput.focus();
    return;
  }
  const body = { herb_name: herb };
  for (const f of optional) body[f.name] = f.unknown.checked ? null : (f.input.value.trim() || null);
  submit.disabled = true;
  try {
    const created = await post("/requests", body);
    location.assign(`/request.html?id=${encodeURIComponent(created.id)}&new=1`);
  } catch (err) {
    submit.disabled = false;
    showErrors([errorMessage(err.code)]);
  }
});
