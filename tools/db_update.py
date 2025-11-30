import os
import argparse
import psycopg


def update_description(property_id: int, suffix: str) -> int:
    db = os.environ["DATABASE_URL"]
    with psycopg.connect(db) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE public.properties SET description = COALESCE(description,'') || %s, updated_at = NOW() WHERE id = %s",
            (" " + suffix, property_id),
        )
        conn.commit()
        return cur.rowcount


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--append", type=str, required=True)
    args = ap.parse_args()
    n = update_description(args.id, args.append)
    print(f"updated_rows={n}")


if __name__ == "__main__":
    main()

