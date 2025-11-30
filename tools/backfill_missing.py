import os
import json
import time
from typing import Any, Dict, List

import psycopg
import google.generativeai as genai

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.vector.compose import build_embedding_text, build_metadata


def fetch_missing(conn, limit: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.*
        FROM public.properties p
        LEFT JOIN public.property_embeddings e ON e.property_id = p.id
        WHERE e.property_id IS NULL
        ORDER BY p.created_at ASC NULLS LAST
        LIMIT %s
        """,
        (limit,),
    )
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    if not rows:
        return []
    # Fetch amenities
    pids = [r["id"] for r in rows]
    cur.execute(
        """
        SELECT pa.property_id, a.title
        FROM public.property_amenities pa
        JOIN public.amenities a ON a.id = pa.amenity_id
        WHERE pa.property_id = ANY(%s)
        """,
        (pids,),
    )
    amap: Dict[int, List[str]] = {}
    for pid, title in cur.fetchall():
        amap.setdefault(pid, []).append(title)
    # Attach amenities and tags
    for r in rows:
        r["_amenities"] = amap.get(r["id"], [])
        tags = r.get("tags") or []
        r["_tags"] = [str(t) for t in tags] if isinstance(tags, list) else []
    return rows


def embed_one(model: str, text: str) -> List[float]:
    retries = 3
    delay = 1.0
    last: Exception | None = None
    for _ in range(retries):
        try:
            r = genai.embed_content(model=model, content=text, task_type="retrieval_document")
            emb = r["embedding"] if isinstance(r, dict) else r.embedding
            vals = emb["values"] if isinstance(emb, dict) else emb
            return [float(x) for x in vals]
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(delay)
            delay = min(8.0, delay * 2)
    assert last is not None
    raise last


def upsert(conn, pid: int, vec: List[float], md: Dict[str, Any], text_hash: str) -> None:
    cur = conn.cursor()
    vec_lit = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
    cur.execute(
        """
        INSERT INTO public.property_embeddings (property_id, embedding, metadata, emb_text_hash, created_at, updated_at)
        VALUES (%s, CAST(%s AS vector), CAST(%s AS jsonb), %s, NOW(), NOW())
        ON CONFLICT (property_id)
        DO UPDATE SET embedding = EXCLUDED.embedding,
                      metadata = EXCLUDED.metadata,
                      emb_text_hash = EXCLUDED.emb_text_hash,
                      updated_at = NOW()
        """,
        (pid, vec_lit, json.dumps(md), text_hash),
    )


def main():
    db = os.environ["DATABASE_URL"]
    api_key = os.environ["GOOGLE_API_KEY"]
    model = os.environ.get("GEMINI_EMBED_MODEL", "text-embedding-004")
    batch = int(os.environ.get("BACKFILL_BATCH", "100"))

    genai.configure(api_key=api_key)

    with psycopg.connect(db) as conn:
        conn.autocommit = True
        try:
            conn.prepare_threshold = None  # avoid server-side prepared statements (PgBouncer-friendly)
        except Exception:
            pass
        rows = fetch_missing(conn, batch)
        print(f"missing={len(rows)}")
        if not rows:
            return
        import hashlib
        inserted = 0
        for r in rows:
            pid = int(r["id"])
            text = build_embedding_text(r, r["_amenities"], r["_tags"])
            md = build_metadata(r, r["_amenities"], r["_tags"])
            h = hashlib.sha256(text.encode("utf-8")).hexdigest()
            vec = embed_one(model, text)
            upsert(conn, pid, vec, md, h)
            inserted += 1
            if inserted % 10 == 0:
                print(f"upserted={inserted}")
        print(f"upserted_total={inserted}")


if __name__ == "__main__":
    main()
