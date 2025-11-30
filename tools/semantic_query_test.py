import os
import psycopg
import google.generativeai as genai


def main():
    db = os.environ["DATABASE_URL"]
    api = os.environ["GOOGLE_API_KEY"]
    model = os.environ.get("GEMINI_EMBED_MODEL", "text-embedding-004")

    genai.configure(api_key=api)
    qtext = os.environ.get(
        "TEST_QUERY",
        "2 bhk apartment for rent in Koramangala under 60000 with parking",
    )
    resp = genai.embed_content(model=model, content=qtext, task_type="retrieval_query")
    emb = resp["embedding"] if isinstance(resp, dict) else resp.embedding
    vals = emb["values"] if isinstance(emb, dict) else emb
    vec_lit = "[" + ",".join(str(float(x)) for x in vals) + "]"

    with psycopg.connect(db) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.id, p.title, p.city, p.monthly_rent, (e.embedding <#> CAST(%s AS vector)) AS distance
            FROM public.property_embeddings e
            JOIN public.properties p ON p.id = e.property_id
            WHERE p.is_available = TRUE
              AND (p.bedrooms IS NULL OR p.bedrooms >= 2)
              AND (p.monthly_rent IS NULL OR p.monthly_rent <= 60000)
            ORDER BY distance ASC
            LIMIT 10
            """,
            (vec_lit,),
        )
        rows = cur.fetchall()
        for r in rows:
            print(r)


if __name__ == "__main__":
    main()
