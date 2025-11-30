import os
import psycopg


def main():
    db = os.environ["DATABASE_URL"]
    with psycopg.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM public.users LIMIT 1")
        row = cur.fetchone()
        if not row:
            raise SystemExit("No users found to assign as owner")
        owner_id = row[0]
        cur.execute(
            """
            INSERT INTO public.properties (
                title, property_type, purpose, base_price, owner_id, city, country, is_available, created_at, updated_at
            ) VALUES (
                %s, 'apartment'::property_type, 'rent'::property_purpose, %s, %s, %s, %s, true, NOW(), NOW()
            ) RETURNING id
            """,
            ("Test Auto Insert Property", 4500000, owner_id, "Bengaluru", "India"),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        print(f"inserted_id={new_id}")


if __name__ == "__main__":
    main()

