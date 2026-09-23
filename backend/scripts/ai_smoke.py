"""Live end-to-end check of the AI step (no DB): real PubMed/Europe PMC search -> OpenAI -> schema-v1 draft.

    cd backend && uv run python -m scripts.ai_smoke [herb_en] [latin]

Needs AI_PROVIDER=openai, AI_MODEL and AI_API_KEY in backend/.env. Costs one model call.
"""

import json
import sys
import time

from app.ai.guard import flag_content
from app.ai.provider import DraftInput, NullProvider, get_provider
from app.ai.schema import HerbRef, assemble_draft
from app.jobs.research import Deps, _search, _source_ref
from app.research.http import SafeClient
from app.research.sources import build_terms
from app.settings import get_settings


def main() -> int:
    s = get_settings()
    http = SafeClient()
    provider = get_provider(s, http)
    if isinstance(provider, NullProvider):
        print("AI not configured (AI_PROVIDER / AI_MODEL / AI_API_KEY)")
        return 1
    name_en = sys.argv[1] if len(sys.argv) > 1 else "Ginger"
    latin = sys.argv[2] if len(sys.argv) > 2 else "Zingiber officinale"
    herb = HerbRef(name_he="ג׳ינג׳ר" if name_en == "Ginger" else name_en, name_en=name_en, latin_name=latin)

    sources, meta = _search(Deps(http=http, provider=provider, settings=s), build_terms(herb.model_dump(), name_en))
    print(f"sources: {meta['counts']}")
    t = time.monotonic()
    analysis = provider.generate(DraftInput(herb=herb.model_dump(), sources=sources,
                                            request={"preparation": "תה", "cancer_type": None, "treatment": "כימותרפיה"}))
    draft = assemble_draft(herb, analysis, [_source_ref(x) for x in sources])
    print(f"model {provider.model}: {time.monotonic() - t:.1f}s, evidence_base={draft.evidence_base}, "
          f"appetite findings={len(draft.appetite.findings)}, secondary={[x.outcome for x in draft.secondary]}, "
          f"cited sources={len(draft.sources)}, flags={flag_content(draft)}")
    print(json.dumps(draft.model_dump(mode="json"), ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
