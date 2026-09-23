import re

from psycopg import Connection

# Hebrew geresh/gershayim and their ASCII/typographic look-alikes -> one canonical apostrophe.
_QUOTES = str.maketrans({"׳": "'", "’": "'", "‘": "'", "`": "'", "״": '"', "“": '"', "”": '"'})


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip().lower()


# ponytail: exact match on normalized names/aliases; add pg_trgm fuzzy matching if real inputs often miss.
def identify(conn: Connection, text: str) -> int | None:
    """Herb id for a user-typed name, or None (a researcher resolves it)."""
    # same quote folding on the DB side, so names stored with a real geresh still match
    row = conn.execute(
        """select id from public.herbs h
            where %(n)s in (select translate(lower(btrim(x)), %(src)s, %(dst)s)
                              from unnest(h.aliases || array[h.name_he, h.name_en, h.latin_name]) x)
            order by id limit 1""",
        {"n": normalize(text), "src": "׳’‘`״“”", "dst": "''''\"\"\""},
    ).fetchone()
    return row["id"] if row else None
