// Structured editor for schema-v1 content. Builds a form from content and reads it back (read()).
// Citations can only point at the request's gathered sources (select), so a draft can't cite unknown papers.

import { bdi, h } from "../dom.js";
import { EVIDENCE_BASE, OUTCOMES, STUDY_TYPES } from "../i18n.js";

let seq = 0;
const uid = (p) => `${p}-${++seq}`;

function field(label, control, hint) {
  const id = control.id || uid("f");
  control.id = id;
  return h("div", { class: "field" }, h("label", { for: id }, label), hint ? h("span", { class: "hint" }, hint) : null, control);
}

// Same limits as backend DraftContent (app/ai/schema.py)
const MAX = { summary_he: 1500, population_he: 400, result_he: 800, text: 500, personal_context_he: 1500, consult_team_note_he: 600 };
const REQUIRED = new Set(["summary_he", "population_he", "result_he", "consult_team_note_he"]);

function textArea(name, value, rows = 3) {
  return h("textarea", { dataset: { name }, rows, value: value ?? "", maxlength: MAX[name] || null,
    required: REQUIRED.has(name) || null, "aria-required": REQUIRED.has(name) ? "true" : null });
}

function select(name, options, value) {
  return h("select", { dataset: { name } },
    Object.entries(options).map(([v, label]) => h("option", { value: v, selected: v === value }, label)));
}

function removeBtn(row, label) {
  return h("button", { type: "button", class: "btn secondary small", onclick: () => {
    const next = row.nextElementSibling || row.previousElementSibling;
    const fieldset = row.closest("fieldset");
    row.remove();
    (next?.querySelector("textarea, select") || fieldset?.querySelector("button"))?.focus();
  } }, `הסרת ${label}`);
}

/** Emptyable list of rows with an "add" button. */
function repeatable(title, items, makeRow, blank) {
  const list = h("div", { class: "rows" }, items.map(makeRow));
  return h("fieldset", { class: "stack" },
    h("legend", {}, title),
    list,
    h("button", { type: "button", class: "btn secondary small", onclick: () => list.append(makeRow(blank())) }, `הוספת ${title}`));
}

export function buildEditor(content, sources) {
  const refs = Object.fromEntries(sources.map((s) => [s.ref, `${s.ref} — ${s.title.slice(0, 80)}`]));

  const findingRow = (f) => {
    const row = h("div", { class: "editor-row", dataset: { kind: "finding" } });
    row.append(
      field("מקור", select("source_ref", refs, f.source_ref)),
      field("סוג המחקר", select("study_type", STUDY_TYPES, f.study_type)),
      field("אוכלוסייה", textArea("population_he", f.population_he, 2)),
      field("ממצא", textArea("result_he", f.result_he, 3)),
      removeBtn(row, "ממצא"));
    return row;
  };
  const blankFinding = () => ({ source_ref: sources[0]?.ref, study_type: "other", population_he: "", result_he: "" });

  const outcome = (key, section) => {
    const box = h("fieldset", { class: "card flat stack", dataset: { outcome: key } },
      h("legend", {}, h("strong", {}, OUTCOMES[key])),
      field("סיכום", textArea("summary_he", section?.summary_he, 4)),
      sources.length ? repeatable("ממצא", section?.findings || [], findingRow, blankFinding)
        : h("p", { class: "muted small" }, "אין מקורות לצטט."));
    return box;
  };

  const secondaryByKey = Object.fromEntries((content.secondary || []).map((s) => [s.outcome, s]));
  const secondaryBoxes = ["food_intake", "weight", "quality_of_life"].map((key) => {
    const include = h("input", { type: "checkbox", checked: Boolean(secondaryByKey[key]) });
    const box = outcome(key, secondaryByKey[key]);
    box.hidden = !include.checked;
    include.addEventListener("change", () => { box.hidden = !include.checked; });
    return { key, include, box };
  });

  const textRow = (label) => (text) => {
    const row = h("div", { class: "editor-row", dataset: { kind: "text" } });
    row.append(field(label, textArea("text", text, 2)), removeBtn(row, label));
    return row;
  };

  const evidenceBase = select("evidence_base", EVIDENCE_BASE, content.evidence_base);
  const appetite = outcome("appetite", content.appetite);
  const safety = repeatable("הערת בטיחות", content.safety_notes_he || [], textRow("הערת בטיחות"), () => "");
  const limits = repeatable("מגבלה", content.limitations_he || [], textRow("מגבלה"), () => "");
  const personal = textArea("personal_context_he", content.personal_context_he, 3);
  const consult = textArea("consult_team_note_he", content.consult_team_note_he, 2);

  const node = h("div", { class: "stack" },
    field("בסיס הראיות", evidenceBase, "קטגוריה בלבד, ללא ציון מספרי"),
    appetite,
    h("fieldset", { class: "stack" }, h("legend", {}, h("strong", {}, "תוצאות משניות")),
      secondaryBoxes.map(({ key, include, box }) => h("div", {},
        h("label", { class: "check" }, include, `לכלול: ${OUTCOMES[key]}`), box))),
    safety, limits,
    field("הקשר אישי", personal, "קשר בין מה שהמשתמש/ת ציין/ה לבין הראיות, ללא ייעוץ"),
    field("הערה על התייעצות עם הצוות המטפל", consult),
    h("details", {}, h("summary", {}, `מקורות שנאספו (${sources.length})`),
      h("ul", {}, sources.map((s) => h("li", {}, bdi(s.ref), " — ", bdi(s.title))))));

  const val = (root, name) => root.querySelector(`[data-name="${name}"]`)?.value.trim() ?? "";
  const readOutcome = (box) => ({
    summary_he: val(box, "summary_he"),
    findings: [...box.querySelectorAll('[data-kind="finding"]')].map((row) => ({
      source_ref: val(row, "source_ref"), study_type: val(row, "study_type"),
      population_he: val(row, "population_he"), result_he: val(row, "result_he"),
    })),
  });
  const readTexts = (fs) => [...fs.querySelectorAll('[data-kind="text"]')].map((r) => val(r, "text")).filter(Boolean);

  function read() {
    const out = {
      schema_version: "1",
      herb: content.herb,
      evidence_base: evidenceBase.value,
      appetite: readOutcome(appetite),
      secondary: secondaryBoxes.filter((s) => s.include.checked).map((s) => ({ outcome: s.key, ...readOutcome(s.box) })),
      safety_notes_he: readTexts(safety),
      limitations_he: readTexts(limits),
      personal_context_he: personal.value.trim() || null,
      consult_team_note_he: consult.value.trim(),
    };
    const cited = new Set([out.appetite, ...out.secondary].flatMap((s) => s.findings.map((f) => f.source_ref)));
    out.sources = sources.filter((s) => cited.has(s.ref)).map(({ ref, title, journal, year, url }) => ({ ref, title, journal, year, url }));
    return out;
  }

  return { node, read };
}

/** Request sources (DB rows) -> citation list entries matching the schema's SourceRef. */
export function toSourceRefs(rows) {
  return rows.map((s) => ({
    ref: s.pmid ? `pmid:${s.pmid}` : s.doi ? `doi:${s.doi.toLowerCase()}` : `pmcid:${s.pmcid}`,
    title: (s.title || "").slice(0, 1000),
    journal: s.journal || null,
    year: s.pub_year ?? null,
    url: s.url && s.url.startsWith("https://") ? s.url : null,
  }));
}

/** Blank schema-v1 content for writing a draft by hand (e.g. AI not configured). */
export function blankContent(herb) {
  return {
    schema_version: "1",
    herb: { name_he: herb?.name_he || "", name_en: herb?.name_en || null, latin_name: herb?.latin_name || null },
    evidence_base: "none_found",
    appetite: { summary_he: "", findings: [] },
    secondary: [],
    safety_notes_he: [],
    limitations_he: [],
    sources: [],
    personal_context_he: null,
    consult_team_note_he: "המידע כאן מסכם מחקרים ואינו המלצה טיפולית. לפני שימוש בכל צמח או תוסף, חשוב להתייעץ עם הצוות המטפל, במיוחד בזמן טיפול אונקולוגי.",
  };
}
