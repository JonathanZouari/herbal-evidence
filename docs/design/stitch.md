# Google Stitch design record

- Stitch project: `projects/12444680124780591192` (title "Herbal Evidence", private, owner: project author)
- Design system asset: `assets/602809031577218080` ("Herbal Evidence – Calm Research"; light, neutral variant, primary #3F6B5A, neutral #F7F7F4, Noto Sans, 8px radius). The full DESIGN.md text (RTL, bidi isolation, status never by color alone, no numeric certainty score, a11y rules) is stored in the asset and applied to the project theme (confirmed via `get_project`).

## Screen generation log (2026-09-16)

| Screen | Model | Result |
|--------|-------|--------|
| Landing page | Gemini 3.5 Flash-Lite | **Generated** — tool returned confirmation text and session `9514389530113482844` |
| Authentication | Gemini 3.5 Flash-Lite | **Generated** — session `9637325417085802655` |
| User dashboard "הבקשות שלי" | Gemini 3.5 Flash-Lite | **Generated** — session `6931086469320335492` |
| New request form | Flash / Flash-Lite | Timed out client-side (3 attempts); not confirmed |
| Waiting status + clarification | Flash / Flash-Lite | Timed out client-side (2 attempts); not confirmed |
| Approved response view | — | Not yet requested |
| Researcher queue | — | Not yet requested |
| Review / editor workspace | — | Not yet requested |
| Review repository | — | Not yet requested |
| Staff management | — | Not yet requested |

**Update 2026-09-23:** `list_screens` now returns the screens. The "timed out" generations did complete server-side.

## Screen inventory (from `list_screens`, 2026-09-23)

All screens are DESKTOP, 2560px wide. Prefix: `projects/12444680124780591192/screens/`.

| Screen | Title in Stitch | Screen ID |
|--------|-----------------|-----------|
| Landing page | דף נחיתה - ראיות צמחים | `ad213f5ee98e431dbd490d510d9f6e8f` |
| Authentication | התחברות והרשמה - סקירת ראיות | `2158256724cb4381a40ea372f900cc5c` |
| User dashboard | הבקשות שלי - לוח משתמש | `cb5c8eee9b5d423c9b6deeafeebfedcf` |
| New request form (v1) | בקשה חדשה - סקירת ראיות צמחים | `f2887c4a698c45a2bd40cbf2dd830c34` |
| New request form (v2) | בקשה חדשה - סקירת ראיות צמחים | `bb43eca2e15847078fe133358ec806df` |
| New request form (v3) | בקשה חדשה - סקירת ראיות צמחים | `f99e2c1053b543b8b533914db98eaa95` |
| New request form (v4) | בקשה חדשה - סקירת ראיות צמחים | `3b22cf2aaab44f069a6eb072d47ea98f` |
| Request detail – waiting + clarification (v1) | פרטי בקשה - ג'ינג'ר (בהמתנה) | `f53ca0490351483080d8052e70f7c62a` |
| Request detail – waiting + clarification (v2) | פרטי בקשה - ג'ינג'ר (בהמתנה) | `5af6b8a2aaa2430085aeb8943935ef8a` |

Still not generated: approved response view, researcher queue, review/editor workspace, review repository, staff management.

## Spec deviations to fix (Phase 4)

1. **ETA shown** — dashboard shows "זמן מענה משוער: 3-5 ימי עבודה"; form v1 shows "הבקשה תיבדק תוך 3 ימי עסקים". Spec forbids showing an ETA.
2. **Inconsistent branding** — form v1 uses "Herbal Evidence" in Latin script; other screens use "ראיות צמחים" / "סקירת ראיות — צמחי מרפא".
3. **Approval count** — dashboard says "הסקירה אושרה ע״י שני חוקרים"; spec requires one researcher approval.
