import modal
import os
import subprocess
from pathlib import Path

app = modal.App("splat-lab-gpu-test")

image = (
    modal.Image.from_registry("pytorch/pytorch:2.1.2-cuda11.8-cudnn8-devel")
    .env({"DEBIAN_FRONTEND": "noninteractive", "TZ": "Etc/UTC"})
    .apt_install("git", "build-essential", "ninja-build", "ffmpeg", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install("nerfstudio==1.1.3", "gsplat==1.0.0", "supabase")
)

@app.function(
    gpu="A10G", 
    image=image, 
    timeout=3600,
    secrets=[modal.Secret.from_name("supabase-secret")]
)
def train_splat_test(job_id: str, storage_path: str, quality_preset: str = "balanced"):
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    bucket = os.environ.get("SPLAT_BUCKET_NAME", "splat-jobs")
    
    workspace = Path("/workspace/data")
    workspace.mkdir(parents=True, exist_ok=True)
    video_path = workspace / "video.mp4"
    
    print("Downloading video from Supabase...")
    res = sb.storage.from_(bucket).download(f"{storage_path}/video.mp4")
    with open(video_path, "wb") as f:
        f.write(res)
        
    print("Running ns-process-data video (Extract + COLMAP)...")
    cmd_process = [
        "ns-process-data", "video",
        "--data", str(video_path),
        "--output-dir", str(workspace),
        "--num-frames-target", "200"
    ]
    process_data = subprocess.Popen(cmd_process, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    last_lines = []
    for line in process_data.stdout:
        print(line, end="")
        last_lines.append(line)
        if len(last_lines) > 50:
            last_lines.pop(0)
            
    process_data.wait()
    if process_data.returncode != 0:
        error_text = "".join(last_lines)
        return {"success": False, "error": f"Code {process_data.returncode}: {error_text[-1000:]}"}
        
    print("Starting training...")
    max_steps = 7000 if quality_preset == "fast" else 15000
    output_dir = Path("/workspace/outputs")
    
    cmd_train = [
        "ns-train", "splatfacto",
        "--data", str(workspace),
        "--output-dir", str(output_dir),
        "--max-num-iterations", str(max_steps),
        "--vis", "viewer+tensorboard",
        "nerfstudio-data"
    ]
    
    process = subprocess.Popen(cmd_train, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()
    if process.returncode != 0:
        return {"success": False, "error": f"Training failed with exit code {process.returncode}"}
        
    print("Exporting splat files...")
    config_file = list(output_dir.glob("**/*/config.yml"))[0]
    ply_path = workspace / "splat.ply"
    cmd_export = ["ns-export", "gaussian-splat", "--load-config", str(config_file), "--output-dir", str(workspace)]
    r = subprocess.run(cmd_export, capture_output=True, text=True)
    if r.returncode != 0:
        return {"success": False, "error": f"Export failed: {r.stderr[-500:]}"}
        
    print("Uploading results...")
    actual_ply = None
    for p in workspace.iterdir():
        if p.suffix == ".ply" and "splat" in p.name.lower():
            actual_ply = p
            break
    if not actual_ply:
        actual_ply = workspace / "splats" / "splat.ply"
    if actual_ply and actual_ply.exists():
        ply_path = actual_ply
        
    with open(ply_path, "rb") as f:
        sb.storage.from_(bucket).upload(
            f"{storage_path}/splat.ply", 
            f.read(),
            file_options={"content-type": "application/octet-stream", "upsert": "true"}
        )
        
    ply_url = sb.storage.from_(bucket).get_public_url(f"{storage_path}/splat.ply")
    supersplat_url = f"https://playcanvas.com/supersplat/editor?load={ply_url}"
    
    sb.table("splat_jobs").update({
        "status": "ready",
        "progress": 100,
        "stage_message": "Splat is ready to view!",
        "splat_url": ply_url,
        "supersplat_url": supersplat_url
    }).eq("id", job_id).execute()
    
    return {"success": True, "splat_url": ply_url}

@app.local_entrypoint()
def main():
    job_id = "48ec7ef3-144c-40e6-b4ee-3645a1145ab3"
    storage_path = f"00000000-0000-0000-0000-000000000000/{job_id}"
    quality = "fast"
    print(train_splat_test.remote(job_id, storage_path, quality))

