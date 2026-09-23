# Privacy and retention

_Full document in Phase 6. Recorded here as soon as a phase creates a data flow._

## Data sent to third parties

| Flow | What is sent | Why | Notes |
|------|--------------|-----|-------|
| PubMed (NCBI E-utilities), Europe PMC | herb English/Latin names + fixed outcome/cancer terms | literature search | no user data; never the Hebrew free text |
| AI provider (OpenAI, only when `AI_API_KEY` is set) | herb names, abstracts of found studies, and the request's **optional free-text fields**: preparation, cancer type, treatment (`"לא ידוע"` when not given) | personal-context paragraph of the draft | `store: false`; no name, email, user id or request id is sent. **Open decision for the product owner:** whether these free-text fields may go to the AI provider at all, or should be omitted (the draft then has no personal-context paragraph). |

## Not collected
No medical profile, ID number or medical records (spec). Users are asked only for the herb and three optional fields.
