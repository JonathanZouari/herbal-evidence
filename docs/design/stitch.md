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

**Known issue:** `list_screens` for this project returned an empty object after confirmed generations, so screen IDs could not be recorded yet. The project thumbnail updated after each generation. Screen IDs will be recorded when the MCP listing works; remaining screens are generated at the start of Phase 4 (frontend), where they are consumed.

Nothing above claims a screen exists unless the generation tool returned a success payload.
