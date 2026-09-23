// Demo content for evidence.html. Written to show the interface: not reviewed by a researcher, not from the API.

export const LEVELS = {
  mixed: { label: "ממצאים מעורבים", icon: "±", tone: "progress", help: "נערכו מחקרים קליניים; חלקם הראו השפעה וחלקם לא." },
  limited: { label: "ראיות מוגבלות", icon: "◔", tone: "attention", help: "מחקרים מעטים או קטנים; קשה להסיק מהם מסקנה." },
  traditional: { label: "שימוש מסורתי", icon: "~", tone: "neutral", help: "שימוש מסורתי מתועד, כמעט ללא מחקר קליני." },
};

export const HERBS = {
  ginger: { name: "זנגביל", latin: "Zingiber officinale" },
  fennel: { name: "שומר", latin: "Foeniculum vulgare" },
  peppermint: { name: "נענע פלפלית", latin: "Mentha × piperita" },
  chamomile: { name: "קמומיל", latin: "Matricaria chamomilla" },
  valerian: { name: "ולריאן", latin: "Valeriana officinalis" },
  "st-johns-wort": { name: "פרע מנוקד", latin: "Hypericum perforatum" },
  licorice: { name: "שוש קירח (ליקוריץ)", latin: "Glycyrrhiza glabra" },
};

export const CONDITIONS = [
  {
    id: "appetite",
    name: "ירידה בתיאבון",
    aliases: ["תיאבון", "חוסר תיאבון", "אנורקסיה", "לא רוצה לאכול"],
    description: "קושי לאכול או חוסר רצון לאכול, תופעה נפוצה במהלך טיפולים אונקולוגיים.",
    studied: [
      { herb: "ginger", level: "limited", summary: "נבדק בעיקר בהקשר של בחילה; מעט מחקרים בדקו השפעה ישירה על התיאבון." },
      { herb: "fennel", level: "traditional", summary: "שימוש מסורתי לעידוד תיאבון ועיכול, ללא מחקר קליני מבוסס." },
    ],
    cautions: [
      { herb: "st-johns-wort", reason: "מאיץ פירוק של תרופות רבות בכבד ועלול להוריד את רמתן של תרופות כימותרפיות בדם." },
      { herb: "licorice", reason: "שימוש ממושך עלול להעלות לחץ דם ולהוריד אשלגן, בעיקר כשיש גם הקאות או שלשולים." },
    ],
  },
  {
    id: "nausea",
    name: "בחילה",
    aliases: ["בחילות", "הקאות", "הקאה", "בחילה מכימותרפיה"],
    description: "תחושת בחילה, לרוב בעקבות טיפול כימותרפי או תרופתי.",
    studied: [
      { herb: "ginger", level: "mixed", summary: "נבדק בכמה מחקרים כתוסף לטיפול נגד בחילה בכימותרפיה; התוצאות אינן עקביות." },
      { herb: "peppermint", level: "limited", summary: "מחקרים קטנים, בעיקר על שאיפת שמן אתרי." },
    ],
    cautions: [
      { herb: "licorice", reason: "עלול להחמיר חוסר איזון במלחים בגוף כשיש הקאות חוזרות." },
      { herb: "st-johns-wort", reason: "אינטראקציות משמעותיות עם תרופות, כולל חלק מהתרופות נגד בחילה ותרופות כימותרפיות." },
    ],
  },
  {
    id: "sleep",
    name: "נדודי שינה",
    aliases: ["שינה", "קשיי שינה", "לא מצליח לישון", "התעוררויות"],
    description: "קושי להירדם או לשמור על שינה רציפה.",
    studied: [
      { herb: "valerian", level: "mixed", summary: "נבדק גם באנשים עם סרטן; מחקר גדול לא מצא שיפור משמעותי בשינה." },
      { herb: "chamomile", level: "limited", summary: "מעט מחקרים קטנים, עם תוצאות לא חד-משמעיות." },
    ],
    cautions: [
      { herb: "st-johns-wort", reason: "עלול להפריע לשינה אצל חלק מהאנשים, ובנוסף יש לו אינטראקציות תרופתיות רבות." },
      { herb: "valerian", reason: "עלול להגביר ישנוניות בשילוב עם תרופות הרגעה או משככי כאבים." },
    ],
  },
  {
    id: "anxiety",
    name: "חרדה ומתח",
    aliases: ["חרדה", "מתח", "סטרס", "לחץ", "דאגה"],
    description: "מתח נפשי, אי שקט או חרדה מוגברת.",
    studied: [
      { herb: "chamomile", level: "limited", summary: "כמה מחקרים קטנים בחרדה כללית, לא באנשים עם סרטן." },
      { herb: "valerian", level: "limited", summary: "מעט מחקרים עם תוצאות לא עקביות." },
    ],
    cautions: [
      { herb: "st-johns-wort", reason: "נחקר בדיכאון, אבל ידוע באינטראקציות עם תרופות כימותרפיות, נוגדי קרישה ותרופות נוגדות דיכאון." },
    ],
  },
  {
    id: "digestion",
    name: "אי נוחות במערכת העיכול",
    aliases: ["עיכול", "נפיחות", "גזים", "כאבי בטן", "צרבת"],
    description: "נפיחות, גזים או קושי כללי בעיכול.",
    studied: [
      { herb: "peppermint", level: "mixed", summary: "נבדק בעיקר בתסמונת המעי הרגיז; לא ברור אם הממצאים רלוונטיים לתופעות לוואי של טיפולים." },
      { herb: "fennel", level: "traditional", summary: "שימוש מסורתי להקלה על גזים ונפיחות." },
    ],
    cautions: [
      { herb: "ginger", reason: "במינונים גבוהים עלול לגרום לצרבת ולהשפיע על קרישת הדם, שחשובה כשספירת הטסיות נמוכה." },
      { herb: "licorice", reason: "שימוש ממושך עלול להעלות לחץ דם ולגרום לאגירת נוזלים." },
    ],
  },
];
