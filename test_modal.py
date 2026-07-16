import modal
import os
from dotenv import load_dotenv

load_dotenv()

job_id = "48ec7ef3-144c-40e6-b4ee-3645a1145ab3"
storage_path = f"00000000-0000-0000-0000-000000000000/{job_id}"
quality = "fast"

print("Looking up modal function...")
f = modal.Function.from_name("splat-lab-gpu", "train_splat")
print("Calling modal function remotely...")
res = f.remote(job_id, storage_path, quality)
print(res)
