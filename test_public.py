import os
from supabase import create_client

from dotenv import load_dotenv
load_dotenv("/Users/chiragsingh/Desktop/360ghar-backend/.env")

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
sb.storage.update_bucket("splat-jobs", public=True)
print("Made bucket public!")
