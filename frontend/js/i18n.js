// Hebrew strings. Keys mirror stable backend codes, so a new code falls back to a generic message.

export const BRAND = "ראיות צמחים";

// What users see. No ETA, no queue position, no drafts, no failures (D-015).
const PUBLIC_STATUS = {
  in_progress: { label: "בטיפול", icon: "⏳", tone: "progress", help: "הבקשה נבדקת על ידי צוות המחקר." },
  needs_clarification: { label: "נדרשת הבהרה", icon: "❓", tone: "attention", help: "החוקר/ת שאל/ה שאלה. אפשר לענות בעמוד הבקשה." },
  published: { label: "התשובה פורסמה", icon: "✔", tone: "done", help: "התשובה נבדקה ואושרה על ידי חוקר/ת." },
  withdrawn: { label: "בוטלה", icon: "✕", tone: "neutral", help: "ביטלת את הבקשה." },
  closed: { label: "נסגרה", icon: "■", tone: "neutral", help: "הבקשה נסגרה על ידי הצוות." },
};

const INTERNAL_STATUS = {
  submitted: { label: "התקבלה", icon: "•", tone: "progress" },
  researching: { label: "חיפוש ספרות", icon: "⏳", tone: "progress" },
  research_failed: { label: "החיפוש נכשל", icon: "!", tone: "failed" },
  draft_ready: { label: "טיוטה מוכנה", icon: "✎", tone: "attention" },
  in_review: { label: "בבדיקת חוקר/ת", icon: "✎", tone: "progress" },
  awaiting_clarification: { label: "ממתין להבהרה", icon: "❓", tone: "attention" },
  published: { label: "פורסם", icon: "✔", tone: "done" },
  withdrawn: { label: "בוטל על ידי המשתמש/ת", icon: "✕", tone: "neutral" },
  closed: { label: "נסגר", icon: "■", tone: "neutral" },
};

export const INTERNAL_STATUSES = Object.keys(INTERNAL_STATUS);

export function publicStatus(code) {
  return PUBLIC_STATUS[code] || { label: code, icon: "•", tone: "neutral", help: "" };
}

export function internalStatus(code) {
  return INTERNAL_STATUS[code] || { label: code, icon: "•", tone: "neutral" };
}

const ERRORS = {
  missing_token: "יש להתחבר מחדש.",
  invalid_token: "פג תוקף ההתחברות. יש להתחבר מחדש.",
  unknown_user: "החשבון לא נמצא. יש להתחבר מחדש.",
  forbidden: "אין לך הרשאה לפעולה זו.",
  not_found: "הפריט לא נמצא.",
  invalid_transition: "לא ניתן לבצע את הפעולה במצב הנוכחי של הבקשה.",
  not_awaiting_clarification: "הבקשה אינה ממתינה לתשובה כרגע.",
  not_in_review: "אפשר לשמור טיוטה רק כשהבקשה בבדיקה.",
  cannot_change_own_role: "לא ניתן לשנות את התפקיד של עצמך.",
  constraint_violation: "הנתונים אינם תקינים.",
  validation_error: "חלק מהשדות אינם תקינים. יש לבדוק ולנסות שוב.",
  content_invalid: "התוכן אינו תואם את מבנה הסקירה. יש לבדוק את השדות המסומנים.",
  content_too_large: "הטיוטה ארוכה מדי.",
  unknown_herb: "הצמח שנבחר לא נמצא ברשימה.",
  not_a_researcher: "אפשר לשייך בקשה רק לחוקר/ת.",
  not_published: "אפשר לשמור סקירה רק מתשובה שפורסמה.",
  review_exists: "כבר נשמרה סקירה מהתשובה הזו.",
  job_pending: "עבודת מחקר כבר ממתינה או רצה עבור הבקשה הזו.",
  content_flags: "בתוכן יש ניסוח שדורש בדיקה לפני פרסום.",
  herb_required: "יש לזהות את הצמח לפני שמירת סקירה.",
  quota_daily: "הגעת למספר הבקשות המרבי ליום. אפשר לשלוח בקשה נוספת מחר.",
  quota_open: "יש לך כבר שלוש בקשות פתוחות. אפשר לשלוח בקשה חדשה אחרי שאחת מהן תושלם.",
  rate_limited: "נשלחו יותר מדי פניות. יש לנסות שוב בעוד דקה.",
  internal_error: "אירעה שגיאה. יש לנסות שוב מאוחר יותר.",
  network: "אין חיבור לשרת. יש לבדוק את החיבור ולנסות שוב.",
};

export function errorMessage(code) {
  return ERRORS[code] || ERRORS.internal_error;
}

// research_jobs.last_error.code (staff only)
const JOB_ERRORS = {
  ai_not_configured: "ספק הבינה המלאכותית לא הוגדר (חסר מפתח או מודל). המקורות נשמרו; אפשר לכתוב טיוטה ידנית אחרי הגדרה והרצה מחדש.",
  ai_auth_failed: "מפתח ספק הבינה המלאכותית נדחה.",
  ai_unavailable: "ספק הבינה המלאכותית לא זמין זמנית.",
  ai_refused: "ספק הבינה המלאכותית סירב לבקשה.",
  ai_bad_output: "הפלט של הבינה המלאכותית לא עמד במבנה הנדרש.",
  ai_request_rejected: "ספק הבינה המלאכותית דחה את הבקשה.",
  herb_unidentified: "הצמח לא זוהה ואין לו שם באנגלית או בלטינית לחיפוש. יש לבחור צמח ולהריץ מחדש.",
  literature_unavailable: "מאגרי הספרות (PubMed ו-Europe PMC) לא היו זמינים.",
  lease_expired_exhausted: "העבודה נקטעה פעמים רבות מדי.",
  internal: "שגיאה פנימית בעיבוד.",
};

export function jobErrorLabel(code) {
  return JOB_ERRORS[code] || `שגיאה: ${code}`;
}

export const JOB_STATUS = { queued: "ממתינה", running: "רצה", succeeded: "הסתיימה", dead: "נכשלה סופית" };

export const STUDY_TYPES = {
  systematic_review: "סקירה שיטתית",
  rct: "ניסוי מבוקר אקראי",
  controlled_trial: "ניסוי מבוקר",
  observational: "מחקר תצפיתי",
  case_series: "סדרת מקרים",
  animal: "מחקר בבעלי חיים",
  in_vitro: "מחקר מעבדה (תאים)",
  other: "אחר",
};

export const EVIDENCE_BASE = {
  none_found: "לא נמצאו מחקרים",
  preclinical_only: "מחקרי מעבדה ובעלי חיים בלבד",
  limited_human: "מחקרים מעטים בבני אדם",
  mixed_human: "מחקרים בבני אדם עם תוצאות לא עקביות",
  consistent_human: "מחקרים בבני אדם עם תוצאות עקביות",
};

export const OUTCOMES = {
  appetite: "תיאבון",
  food_intake: "צריכת מזון",
  weight: "משקל",
  quality_of_life: "איכות חיים",
};

export const ROLES = { user: "משתמש/ת", researcher: "חוקר/ת", admin: "מנהל/ת" };

export const AI_FLAGS = {
  dose: "ייתכן שמופיע מינון או כמות",
  recommendation: "ייתכן שמופיע ניסוח של המלצה",
  cure_claim: "ייתכן שמופיעה טענה על ריפוי או השפעה על הגידול",
  numeric_score: "ייתכן שמופיע ציון או אחוז",
};
