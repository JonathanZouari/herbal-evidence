// Staff workspace for one request: status, job errors, sources, draft editor and the actions its status allows.
// Only the assigned researcher can publish or save a reusable review (the backend enforces this too).

import { get, patch, post, put } from "../api.js";
import { bdi, clear, extLink, formatDate, h, param } from "../dom.js";
import { AI_FLAGS, errorMessage, internalStatus, JOB_STATUS, jobErrorLabel } from "../i18n.js";
import { confirmDialog, focusHeading, main, requireAuth, showError, toast } from "../layout.js";
import { blankContent, buildEditor, toSourceRefs } from "../render/editor.js";
import { isSchemaV1, renderContent } from "../render/response.js";

const me = await requireAuth(["researcher", "admin"]);
const root = main();
const id = param("id");
const base = `/staff/requests/${encodeURIComponent(id)}`;

function badge(code) {
  const s = internalStatus(code);
  return h("span", { class: `badge ${s.tone}`, "data-icon": s.icon }, s.label);
}

// Unsaved editor changes are lost on re-render: ask first.
let editorDirty = false;
const CLOSABLE = new Set(["submitted", "research_failed", "draft_ready", "in_review", "awaiting_clarification"]);

async function act(fn, success, { keepEdits = false } = {}) {
  if (editorDirty && !keepEdits && !(await confirmDialog({
    title: "שינויים שלא נשמרו", body: "בטיוטה יש שינויים שלא נשמרו. להמשיך בלי לשמור?", confirmLabel: "המשך בלי לשמור", danger: true,
  }))) return false;
  try {
    await fn();
    if (success) toast(success);
    await load();
    return true;
  } catch (e) {
    toast(errorMessage(e.code));
    return false;
  }
}

function jobPanel(r) {
  const job = r.jobs.at(-1);
  if (!job) return null;
  const err = job.last_error;
  return h("section", { class: `callout ${r.status === "research_failed" ? "danger" : "info"}` },
    h("h2", {}, "עבודת המחקר האחרונה"),
    h("p", {}, `ניסיון ${job.attempts} מתוך ${job.max_attempts} · מצב: ${JOB_STATUS[job.status] || job.status}`),
    err?.code ? h("p", {}, h("strong", {}, jobErrorLabel(err.code)), err.stage ? h("span", { class: "muted small" }, ` (שלב: ${err.stage})`) : null) : null);
}

function sourcesPanel(r) {
  return h("section", { class: "card stack" },
    h("h2", {}, `מקורות שנאספו (${r.sources.length})`),
    r.sources.length ? h("div", {}, r.sources.map((s) => h("div", { class: "source-item" },
      extLink(s.url, s.title),
      h("div", { class: "muted small" }, bdi([s.journal, s.pub_year, s.pmid ? `PMID ${s.pmid}` : s.doi].filter(Boolean).join(" · ")),
        " · ", h("span", { class: "tag" }, s.origin)),
      s.abstract ? h("details", {}, h("summary", {}, "תקציר"), h("p", { class: "small ltr", lang: "en" }, s.abstract)) : null)))
      : h("p", { class: "muted" }, "עדיין לא נאספו מקורות."));
}

function timeline(r) {
  return h("section", { class: "card" }, h("h2", {}, "היסטוריה"),
    h("ol", { class: "timeline" }, r.events.map((e) => h("li", {},
      h("strong", {}, internalStatus(e.to_status).label),
      h("div", { class: "muted small" }, formatDate(e.created_at), e.actor_id ? "" : " · מערכת")))));
}

async function herbPanel(r) {
  const herbs = await get("/herbs");
  const sel = h("select", { id: "herb-select" }, h("option", { value: "" }, "— בחירת צמח —"),
    herbs.map((x) => h("option", { value: x.id, selected: x.id === r.herb_id }, x.name_en ? `${x.name_he} (${x.name_en})` : x.name_he)));
  return h("section", { class: "card stack" },
    h("h2", {}, "זיהוי הצמח"),
    h("p", {}, "הקלט של המשתמש/ת: ", bdi(r.herb_name_input), r.herb ? ` · מזוהה כ: ${r.herb.name_he}` : " · לא זוהה"),
    h("div", { class: "field" }, h("label", { for: "herb-select" }, "צמח"), sel),
    h("button", { type: "button", class: "btn secondary", onclick: () => sel.value &&
      act(() => patch(`${base}/herb`, { herb_id: Number(sel.value) }), "הצמח עודכן. אפשר להריץ מחדש.") }, "שמירת הצמח"));
}

function rerunControls() {
  const fresh = h("input", { type: "checkbox", id: "fresh" });
  return h("div", { class: "row" },
    h("button", { type: "button", class: "btn secondary", onclick: () => act(() => post(`${base}/rerun`, { fresh: fresh.checked }), "המחקר יורץ מחדש.") }, "הרצת מחקר מחדש"),
    h("label", { class: "check", for: "fresh" }, fresh, "חיפוש חדש (בלי שימוש בסקירה קיימת)"));
}

function clarifyForm() {
  const ta = h("textarea", { id: "clar-q", maxlength: 2000, rows: 2 });
  return h("form", { class: "card stack", onsubmit: (e) => {
    e.preventDefault();
    if (ta.value.trim()) act(() => post(`${base}/clarifications`, { text: ta.value.trim() }), "השאלה נשלחה למשתמש/ת.");
  } }, h("h2", {}, "שאלת הבהרה למשתמש/ת"),
  h("div", { class: "field" }, h("label", { for: "clar-q" }, "השאלה"), ta),
  h("button", { class: "btn secondary", type: "submit" }, "שליחת שאלה"));
}

function showEditorError(box, e) {
  clear(box).append(h("div", { class: "error-summary", role: "alert", tabindex: "-1" },
    h("p", {}, errorMessage(e.code)),
    e.code === "content_invalid" && e.message ? h("p", { class: "small ltr" }, bdi(e.message)) : null));
  box.firstChild.focus();
}

async function publish(content, errorBox) {
  const send = (ack) => post(`${base}/publish`, { body: content, acknowledge_flags: ack });
  const ok = await confirmDialog({ title: "פרסום התשובה", body: "התשובה תוצג למשתמש/ת. האישור שלך הוא האישור היחיד הנדרש.", confirmLabel: "אישור ופרסום" });
  if (!ok) return;
  try {
    await put(`${base}/draft`, { content });   // the stored draft always equals what was published
    await send(false);
  } catch (e) {
    if (e.code !== "content_flags") return showEditorError(errorBox, e);
    const flags = e.message.split(",").map((f) => AI_FLAGS[f] || f).join("; ");
    const ack = await confirmDialog({ title: "ניסוח שדורש בדיקה", body: `נמצא: ${flags}. לפרסם בכל זאת?`, confirmLabel: "בדקתי — לפרסם" });
    if (!ack) return;
    try { await send(true); } catch (e2) { return showEditorError(errorBox, e2); }
  }
  editorDirty = false;
  toast("התשובה פורסמה.");
  await load();
}

function editorPanel(r, draft, isAssignedResearcher) {
  const content = isSchemaV1(draft?.content) ? draft.content : blankContent(r.herb);
  const known = toSourceRefs(r.sources);
  const sources = [...known, ...content.sources.filter((s) => !known.some((k) => k.ref === s.ref))];
  const editor = buildEditor(content, sources);
  const errorBox = h("div", { tabindex: "-1" });
  editor.node.addEventListener("input", () => { editorDirty = true; });
  const save = async () => {
    try {
      await put(`${base}/draft`, { content: editor.read() });
      editorDirty = false;
      clear(errorBox);
      toast("הטיוטה נשמרה.");
    } catch (e) { showEditorError(errorBox, e); }
  };
  return h("section", { class: "card stack", "aria-labelledby": "ed-title" },
    h("h2", { id: "ed-title" }, "עריכת הטיוטה"),
    draft?.meta?.reused_review_version ? h("p", { class: "callout info" }, `הטיוטה מבוססת על סקירה מאושרת (גרסה ${draft.meta.reused_review_version}). עדיין נדרש האישור שלך.`) : null,
    editor.node,
    errorBox,
    h("div", { class: "row" },
      h("button", { type: "button", class: "btn secondary", onclick: save }, "שמירת טיוטה"),
      isAssignedResearcher ? h("button", { type: "button", class: "btn", onclick: () => publish(editor.read(), errorBox) }, "אישור ופרסום")
        : h("p", { class: "muted small" }, "רק החוקר/ת המשויך/ת יכול/ה לאשר ולפרסם.")));
}

async function load() {
  let r, herbSection;
  try {
    r = await get(base);
    herbSection = !r.herb_id || ["submitted", "research_failed", "in_review"].includes(r.status) ? await herbPanel(r) : null;
  } catch (e) { return showError(root, e); }
  editorDirty = false;
  const draft = r.drafts.at(-1);
  const response = r.response[0];
  const assigned = r.assigned_researcher_id === me.id;
  const isAssignedResearcher = me.role === "researcher" && assigned;
  const flags = [...(draft?.meta?.ai_flags || [])];

  const actions = [];
  if (r.status === "draft_ready") actions.push(h("button", { type: "button", class: "btn", onclick: () => act(() => post(`${base}/start-review`), "הבקשה בבדיקה.") }, "התחלת בדיקה"));
  if (["research_failed", "in_review"].includes(r.status)) actions.push(rerunControls());
  if (response && isAssignedResearcher && r.herb_id) {
    actions.push(h("button", { type: "button", class: "btn secondary", onclick: () => act(() => post(`${base}/save-review`), "נשמרה סקירה לשימוש חוזר.") }, "שמירה כסקירה לשימוש חוזר"));
  }
  if (CLOSABLE.has(r.status)) {
    actions.push(h("button", { type: "button", class: "btn danger", onclick: async () => {
      if (await confirmDialog({ title: "סגירת הבקשה", body: "המשתמש/ת יראה/תראה שהבקשה נסגרה.", confirmLabel: "סגירה", danger: true })) {
        act(() => post(`${base}/close`), "הבקשה נסגרה.");
      }
    } }, "סגירת הבקשה"));
  }

  clear(root).append(
    h("p", {}, h("a", { href: "/staff.html" }, "← חזרה לתור")),
    h("div", { class: "card stack" },
      h("div", { class: "row spread" }, h("h1", {}, bdi(r.herb_name_input)), badge(r.status)),
      h("dl", { class: "grid-3" },
        ["preparation", "cancer_type", "treatment"].map((k, i) => h("div", {},
          h("dt", { class: "muted small" }, ["צורת שימוש", "סוג הסרטן", "טיפול נוכחי"][i]),
          h("dd", {}, r[k] ? bdi(r[k]) : "לא ידוע")))),
      h("p", { class: "muted small" }, `נשלחה ב-${formatDate(r.created_at)}`, assigned ? " · משויכת אליך" : ""),
      actions.length ? h("div", { class: "row" }, actions) : null),
    flags.length ? h("div", { class: "callout warning", role: "note" }, h("h2", {}, "נקודות לבדיקה בטיוטה"),
      h("ul", {}, flags.map((f) => h("li", {}, f === "partial_search" ? "אחד ממאגרי הספרות לא היה זמין בחיפוש" : AI_FLAGS[f] || f)))) : null,
    jobPanel(r),
    herbSection,
    r.clarifications.length ? h("section", { class: "card" }, h("h2", {}, "הבהרות"),
      h("ul", {}, r.clarifications.map((c) => h("li", {}, bdi(c.question), " — ", c.answer ? bdi(c.answer) : h("em", {}, "טרם נענתה"))))) : null,
    r.status === "in_review" ? editorPanel(r, draft, isAssignedResearcher) : null,
    r.status === "in_review" ? clarifyForm() : null,
    response ? h("section", { class: "card stack" }, h("h2", {}, "התשובה שפורסמה"), renderContent(response.body))
      : draft && r.status !== "in_review" ? h("section", { class: "card stack" }, h("h2", {}, "תצוגת הטיוטה"), renderContent(draft.content)) : null,
    sourcesPanel(r),
    timeline(r));
  focusHeading();
}

if (!id) showError(root, { code: "not_found" });
else await load();
