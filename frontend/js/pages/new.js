// New request: herb (list + free text) and three optional fields, each with an explicit "I don't know".

import { get, post } from "../api.js";
import { bdi, clear, h } from "../dom.js";
import { CERTAINTY, errorMessage } from "../i18n.js";
import { announce, main, requireAuth } from "../layout.js";

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

// Photo -> most likely herb name (D-021). The photo is resized here (which also drops EXIF/GPS) and not stored.
const MAX_SIDE = 1024;
const photoInput = h("input", { type: "file", accept: "image/*", capture: "environment", class: "sr-only",
  tabindex: "-1", "aria-hidden": "true" });
const photoButton = h("button", { class: "btn secondary small", type: "button", "aria-describedby": "photo-status" },
  "📷 צילום הצמח");
const photoPreview = h("img", { class: "photo-preview", alt: "התמונה שנבחרה", hidden: true });
const photoStatus = h("div", { id: "photo-status", class: "hint" });

async function toJpeg(file) {
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = h("canvas", { width: Math.round(bitmap.width * scale), height: Math.round(bitmap.height * scale) });
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return canvas.toDataURL("image/jpeg", 0.85);
}

function photoMessage(...children) {
  clear(photoStatus).append(h("p", {}, ...children));
}

async function identifyPhoto(file) {
  photoButton.disabled = true;
  photoButton.textContent = "מזהה…";
  photoMessage("מזהה את הצמח מהתמונה…");
  try {
    let image;
    try { image = await toJpeg(file); } catch { throw Object.assign(new Error(), { code: "image_invalid" }); }
    photoPreview.src = image;
    photoPreview.hidden = false;
    const r = await post("/herbs/identify", { image });
    const name = r.name_he || r.latin_name;
    herbInput.value = name;
    herbError.textContent = "";
    herbInput.removeAttribute("aria-invalid");
    photoMessage("זוהה: ", h("strong", {}, bdi(name)),
      r.latin_name && r.latin_name !== name ? [" (", h("i", {}, bdi(r.latin_name)), ")"] : null,
      `. ודאות: ${CERTAINTY[r.certainty] || r.certainty}. `,
      "זיהוי מתמונה עלול לטעות, אפשר לתקן את השם לפני השליחה.");
    announce(`זוהה: ${name}. אפשר לתקן לפני השליחה.`);
  } catch (err) {
    clear(photoStatus).append(h("p", { class: "error-text", role: "alert" }, errorMessage(err.code)));
  } finally {
    photoButton.disabled = false;
    photoButton.textContent = "📷 צילום הצמח";
    photoInput.value = "";
  }
}

photoButton.addEventListener("click", () => photoInput.click());
photoInput.addEventListener("change", () => { if (photoInput.files[0]) identifyPhoto(photoInput.files[0]); });

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
    h("div", { class: "row" }, photoButton, h("span", { class: "hint" }, "או צלמו את הצמח ונזהה את שמו")),
    photoInput, photoPreview, photoStatus,
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
