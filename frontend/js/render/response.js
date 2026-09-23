// Read-only rendering of schema-v1 content (published response, draft preview, reusable review).
// Appetite first; secondary outcomes each in their own section; evidence base as words, never a number.

import { bdi, extLink, h } from "../dom.js";
import { EVIDENCE_BASE, OUTCOMES, STUDY_TYPES } from "../i18n.js";
import { toast } from "../layout.js";

export function isSchemaV1(content) {
  return Boolean(content && content.schema_version === "1" && content.appetite && Array.isArray(content.sources));
}

function citation(ref, sources) {
  const i = sources.findIndex((s) => s.ref === ref);
  if (i < 0) return h("span", { class: "tag" }, bdi(ref));
  return h("a", { href: `#src-${i + 1}`, class: "tag", "aria-label": `מקור ${i + 1}` }, `[${i + 1}]`);
}

function findings(list, sources) {
  if (!list?.length) return null;
  return h("ul", { class: "findings" }, list.map((f) => h("li", { class: "finding" },
    h("div", { class: "row" }, h("span", { class: "tag" }, STUDY_TYPES[f.study_type] || f.study_type), citation(f.source_ref, sources)),
    h("p", { class: "small muted" }, "אוכלוסייה: ", f.population_he),
    h("p", {}, f.result_he))));
}

function outcomeSection(key, title, section, sources, level = "h2") {
  return h("section", { "aria-labelledby": `sec-${key}` },
    h(level, { id: `sec-${key}` }, title),
    h("p", {}, section.summary_he),
    findings(section.findings, sources));
}

function bullets(title, items, emptyText) {
  return h("section", {},
    h("h2", {}, title),
    items?.length ? h("ul", {}, items.map((t) => h("li", {}, t))) : h("p", { class: "muted" }, emptyText));
}

async function copyCitation(s) {
  const text = [s.title, [s.journal, s.year].filter(Boolean).join(", "), s.ref, s.url].filter(Boolean).join(". ");
  try {
    await navigator.clipboard.writeText(text);
    toast("הציטוט הועתק.");
  } catch {
    toast("לא ניתן היה להעתיק את הציטוט.");
  }
}

export function sourceList(sources) {
  if (!sources?.length) return h("p", { class: "muted" }, "לא צוטטו מקורות.");
  return h("ol", { class: "sources" }, sources.map((s, i) => h("li", { id: `src-${i + 1}` },
    s.url ? extLink(s.url, s.title) : bdi(s.title),
    h("span", { class: "muted small" }, " · ", bdi([s.journal, s.year].filter(Boolean).join(", ")), " · ", bdi(s.ref)),
    " ",
    h("button", { class: "btn secondary small no-print", type: "button", "aria-label": `העתקת ציטוט למקור ${i + 1}`,
      onclick: () => copyCitation(s) }, "העתק ציטוט"))));
}

/** Render content; `personal` = include the personal-context and consult sections (responses and drafts). */
export function renderContent(content, { personal = true } = {}) {
  if (!isSchemaV1(content)) {
    return h("div", { class: "callout warning" }, h("p", {}, "התוכן אינו זמין בתצוגה זו."));
  }
  const sources = content.sources;
  const secondaryByOutcome = Object.fromEntries((content.secondary || []).map((s) => [s.outcome, s]));
  return h("div", { class: "evidence stack" },
    h("p", {},
      h("strong", {}, "בסיס הראיות: "),
      h("span", { class: "badge neutral", "data-icon": "📚" }, EVIDENCE_BASE[content.evidence_base] || content.evidence_base)),
    outcomeSection("appetite", `${OUTCOMES.appetite} (התוצאה העיקרית)`, content.appetite, sources),
    h("section", {},
      h("h2", {}, "תוצאות נוספות"),
      h("div", { class: "grid-3" }, ["food_intake", "weight", "quality_of_life"].map((key) => {
        const s = secondaryByOutcome[key];
        return h("div", { class: "card flat" },
          h("h3", {}, OUTCOMES[key]),
          s ? [h("p", {}, s.summary_he), findings(s.findings, sources)] : h("p", { class: "muted" }, "לא נבדק במחקרים שנמצאו."));
      }))),
    bullets("בטיחות ואינטראקציות", content.safety_notes_he, "לא דווחו במקורות שנמצאו."),
    bullets("מגבלות הראיות", content.limitations_he, "—"),
    personal && content.personal_context_he ? h("section", {}, h("h2", {}, "הקשר אישי"), h("p", {}, content.personal_context_he)) : null,
    personal && content.consult_team_note_he ? h("div", { class: "callout", role: "note" },
      h("p", {}, h("strong", {}, content.consult_team_note_he)),
      h("p", { class: "small" }, "המידע אינו המלצה טיפולית ואינו כולל מינונים.")) : null,
    h("section", {}, h("h2", {}, "מקורות"), sourceList(sources)));
}
