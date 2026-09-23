// Dummy data: herbs and diseases/symptoms with suitability guidance.
// This is placeholder content for the herb-search demo feature only.
// It is NOT medical advice and is not connected to the real evidence-review workflow.

const HERB_DATA = {
  conditions: [
    {
      id: "appetite-loss",
      name: "ירידה בתיאבון",
      description: "קושי לאכול או חוסר רצון לאכול, נפוץ בטיפולים אונקולוגיים.",
      recommended: ["ginger", "fennel", "peppermint"],
      notRecommended: ["licorice", "st-johns-wort"],
    },
    {
      id: "nausea",
      name: "בחילה",
      description: "תחושת בחילה, לרוב בעקבות טיפול תרופתי או כימותרפי.",
      recommended: ["ginger", "peppermint", "chamomile"],
      notRecommended: ["licorice"],
    },
    {
      id: "insomnia",
      name: "נדודי שינה",
      description: "קושי להירדם או לשמור על שינה רציפה.",
      recommended: ["chamomile", "valerian"],
      notRecommended: ["ginger", "st-johns-wort"],
    },
    {
      id: "anxiety",
      name: "חרדה וסטרס",
      description: "מתח נפשי, אי שקט או חרדה מוגברת.",
      recommended: ["chamomile", "valerian", "st-johns-wort"],
      notRecommended: ["fennel"],
    },
    {
      id: "digestive-discomfort",
      name: "אי נוחות במערכת העיכול",
      description: "נפיחות, גזים או קושי כללי בעיכול.",
      recommended: ["fennel", "peppermint", "ginger"],
      notRecommended: ["valerian", "st-johns-wort"],
    },
  ],

  herbs: {
    ginger: {
      id: "ginger",
      name: "זנגביל",
      latinName: "Zingiber officinale",
      note: "נחקר בעיקר לצמצום בחילה; יש להיזהר בשילוב עם נוגדי קרישה.",
    },
    fennel: {
      id: "fennel",
      name: "שומר",
      latinName: "Foeniculum vulgare",
      note: "שימוש מסורתי לתמיכה בעיכול ובתיאבון.",
    },
    peppermint: {
      id: "peppermint",
      name: "נענע פלפלית",
      latinName: "Mentha piperita",
      note: "עשוי להקל על בחילה ועל תחושת נפיחות.",
    },
    chamomile: {
      id: "chamomile",
      name: "קמומיל",
      latinName: "Matricaria chamomilla",
      note: "שימוש מסורתי להרגעה ולתמיכה בשינה.",
    },
    valerian: {
      id: "valerian",
      name: "ולריאן",
      latinName: "Valeriana officinalis",
      note: "נחקר בהקשר של שינה; עלול לגרום לישנוניות מוגברת ביום.",
    },
    "st-johns-wort": {
      id: "st-johns-wort",
      name: "פרע מנוקד (St. John's Wort)",
      latinName: "Hypericum perforatum",
      note: "אינטראקציות תרופתיות משמעותיות רבות — כולל עם טיפולים אונקולוגיים; דורש זהירות מיוחדת.",
    },
    licorice: {
      id: "licorice",
      name: "שוש (ליקריץ)",
      latinName: "Glycyrrhiza glabra",
      note: "שימוש ממושך עלול להשפיע על לחץ דם ואיזון אלקטרוליטים.",
    },
  },
};
