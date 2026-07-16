import os
from supabase import create_client

from dotenv import load_dotenv
load_dotenv("/Users/chiragsingh/Desktop/360ghar-backend/.env")

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
res = sb.storage.from_("splat-jobs").download("00000000-0000-0000-0000-000000000000/48ec7ef3-144c-40e6-b4ee-3645a1145ab3/splat.splat")
with open("splat.splat", "wb") as f:
    f.write(res)
print("Saved to splat.splat")
