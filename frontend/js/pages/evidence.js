// Evidence map by symptom (public, demo data): what has been studied, at which evidence level, and known cautions.
// It shows research status only; it never recommends a herb, dose or combination.

import { CONDITIONS, HERBS, LEVELS } from "../evidence-demo.js";
import { bdi, clear, h, param } from "../dom.js";
import { announce, main, publicShell } from "../layout.js";

await publicShell();
const root = main();

const normalize = (text) => (text || "").replace(/\s+/g, " ").trim().toLowerCase();

function find(query) {
  const q = normalize(query);
  if (!q) return null;
  const terms = (c) => [c.name, ...c.aliases].map(normalize);
  return CONDITIONS.find((c) => terms(c).includes(q))
    || CONDITIONS.find((c) => terms(c).some((t) => t.includes(q) || q.includes(t)))
    || null;
}

const input = h("input", { id: "symptom", type: "search", list: "symptom-list", autocomplete: "off",
  placeholder: "לדוגמה: בחילה, שינה, תיאבון", "aria-describedby": "symptom-hint" });
const chips = new Map(CONDITIONS.map((c) => [c.id,
  h("button", { type: "button", class: "btn secondary small", "aria-pressed": "false", onclick: () => select(c) }, c.name)]));
const results = h("div", { id: "results", class: "results" });

const form = h("form", { role: "search", novalidate: true, onsubmit: (e) => { e.preventDefault(); search(); } },
  h("div", { class: "field" },
    h("label", { for: "symptom" }, "תסמין או מחלה"),
    h("span", { class: "hint", id: "symptom-hint" }, "אפשר להקליד במילים שלכם או לבחור מהרשימה."),
    h("div", { class: "row" }, h("div", { class: "grow" }, input), h("button", { class: "btn", type: "submit" }, "חיפוש")),
    h("datalist", { id: "symptom-list" }, CONDITIONS.map((c) => h("option", { value: c.name })))),
  h("div", { class: "row", role: "group", "aria-label": "תסמינים לדוגמה" }, [...chips.values()]));

clear(root).append(
  h("h1", {}, "מפת ראיות לפי תסמין"),
  h("p", { class: "muted" }, "אילו צמחים נחקרו בהקשר של תסמין מסוים, מה רמת הראיות, ולאילו צמחים כדאי לשים לב בזמן טיפול בגלל סיכונים ואינטראקציות ידועים."),
  h("p", { class: "callout warning", role: "note" },
    h("strong", {}, "נתוני הדגמה. "),
    "התוכן בעמוד נכתב להדגמת הממשק, חוקר/ת לא בדק/ה אותו, והוא אינו המלצה על צמח, מינון או שילוב עם טיפול."),
  h("div", { class: "card" }, form),
  results);

function herbHeading(id, badge) {
  const herb = HERBS[id];
  return h("div", { class: "row spread" },
    h("h4", {}, herb.name, " ", h("span", { class: "muted small ltr" }, bdi(herb.latin))),
    badge || null);
}

function levelBadge(key) {
  const level = LEVELS[key];
  return h("span", { class: `badge ${level.tone}`, dataset: { icon: level.icon }, title: level.help }, level.label);
}

function select(condition) {
  input.value = condition.name;
  render(condition);
}

function search() {
  if (!normalize(input.value)) return showMessage("הקלידו תסמין או בחרו אחד מהרשימה.");
  const condition = find(input.value);
  if (condition) render(condition);
  else showMessage("לא נמצא תסמין מתאים. נסו מילה אחרת או בחרו מהרשימה.");
}

function setState(id) {
  chips.forEach((chip, key) => chip.setAttribute("aria-pressed", String(key === id)));
  const url = new URL(location.href);
  if (id) url.searchParams.set("s", id); else url.searchParams.delete("s");
  history.replaceState(null, "", url);
}

function showMessage(text) {
  setState(null);
  clear(results).append(h("p", { class: "muted", role: "status" }, text));
  input.focus();
}

function render(c) {
  setState(c.id);
  clear(results).append(h("section", { class: "stack", "aria-labelledby": "condition-title" },
    h("div", {},
      h("h2", { id: "condition-title" }, c.name),
      h("p", { class: "muted" }, c.description)),
    h("div", { class: "grid-halves" },
      h("section", { class: "card flat" },
        h("h3", {}, "מה נחקר"),
        h("p", { class: "muted small" }, "צמחים שנבדקו בהקשר של התסמין, ורמת הראיות לגביהם."),
        c.studied.map((s) => h("div", { class: "finding" }, herbHeading(s.herb, levelBadge(s.level)), h("p", {}, s.summary)))),
      h("section", { class: "card flat caution" },
        h("h3", {}, "לשים לב"),
        h("p", { class: "muted small" }, "סיכונים ואינטראקציות ידועים שחשובים במיוחד בזמן טיפול."),
        c.cautions.map((x) => h("div", { class: "finding" }, herbHeading(x.herb), h("p", {}, x.reason))))),
    h("details", {},
      h("summary", {}, "מה המשמעות של רמות הראיות?"),
      h("dl", { class: "levels" }, Object.values(LEVELS).map((l) => [
        h("dt", {}, h("span", { class: `badge ${l.tone}`, dataset: { icon: l.icon } }, l.label)),
        h("dd", {}, l.help)]))),
    h("div", { class: "callout" },
      h("h3", {}, "רוצים סיכום מחקרים על צמח אחד?"),
      h("p", {}, "בחרו צמח, וחוקר/ת יסכם/תסכם עבורכם את המחקרים שפורסמו על השפעתו על התיאבון."),
      h("a", { class: "btn", href: "/new.html" }, "שליחת בקשה"))));
  announce(`${c.name}: ${c.studied.length} צמחים שנחקרו, ${c.cautions.length} אזהרות.`);
}

const initial = CONDITIONS.find((c) => c.id === param("s"));
if (initial) select(initial);
else results.append(h("p", { class: "muted" }, "בחרו תסמין כדי לראות את מפת הראיות."));
