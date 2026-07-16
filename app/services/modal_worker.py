import os
import subprocess
from pathlib import Path

import modal

app = modal.App("splat-lab-gpu")

image = (
    modal.Image.from_registry("pytorch/pytorch:2.1.2-cuda11.8-cudnn8-devel")
    .env({"DEBIAN_FRONTEND": "noninteractive", "TZ": "Etc/UTC"})
    .apt_install("git", "build-essential", "ninja-build", "ffmpeg", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install("numpy<2.0.0", "nerfstudio==1.1.3", "gsplat==1.0.0", "plyfile")
    .pip_install("supabase")
    .apt_install("colmap", "xvfb")
)

vol = modal.Volume.from_name("splat-lab-data", create_if_missing=True)

@app.function(
    gpu="A10G", 
    image=image, 
    timeout=3600,
    secrets=[
        modal.Secret.from_name("supabase-secret")
    ],
    volumes={"/data": vol}
)
def train_splat(job_id: str, storage_path: str, quality_preset: str = "balanced"):
    from supabase import create_client
    import shutil
    
    sb_url = os.environ["SUPABASE_URL"]
    sb_key = os.environ["SUPABASE_SECRET_KEY"]
    bucket = os.environ["SPLAT_BUCKET_NAME"]
    
    sb = create_client(sb_url, sb_key)
    
    try:
        sb.table("splat_jobs").update({
            "status": "extracting", 
            "stage_message": "Processing video into 3D dataset on GPU..."
        }).eq("id", job_id).execute()
    except Exception:
        pass
        
    persistent_workspace = Path(f"/data/{job_id}")
    persistent_workspace.mkdir(parents=True, exist_ok=True)
    
    workspace = Path("/workspace/data")
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Restore checkpoint
    if list(persistent_workspace.iterdir()):
        print("Restoring checkpoint from volume...")
        os.system(f"cp -r {persistent_workspace}/* {workspace}/")
    
    video_path = workspace / "video.mp4"
    
    if not video_path.exists():
        print("Downloading video from Supabase...")
        try:
            res = sb.storage.from_(bucket).download(f"{storage_path}/video.mp4")
            with open(video_path, "wb") as f:
                f.write(res)
            os.system(f"cp {video_path} {persistent_workspace}/")
            vol.commit()
        except Exception as e:
            error = f"Failed to download video: {e}"
            sb.table("splat_jobs").update({"status": "failed", "error_message": error}).eq("id", job_id).execute()
            return {"success": False, "error": error}
            
    colmap_db = workspace / "colmap/database.db"
    if not colmap_db.exists():
        print("Running ns-process-data video (Extract + COLMAP)...")
        try:
            cmd_process = [
                "xvfb-run", "-a",
                "ns-process-data", "video",
                "--data", str(video_path),
                "--output-dir", str(workspace),
                "--no-gpu",
                "--camera-type", "equirectangular",
                "--images-per-equirect", "8",
                "--num-frames-target", "200" # 200 frames is enough for a good splat and fast
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
                error = f"ns-process-data failed with code {process_data.returncode}: {error_text[-1000:]}"
                sb.table("splat_jobs").update({"status": "failed", "error_message": error}).eq("id", job_id).execute()
                return {"success": False, "error": error}
                
            print("Checkpointing colmap data...")
            os.system(f"cp -r {workspace}/* {persistent_workspace}/")
            vol.commit()
        except Exception as e:
            error = f"Exception in ns-process-data: {e}"
            sb.table("splat_jobs").update({"status": "failed", "error_message": error}).eq("id", job_id).execute()
            return {"success": False, "error": error}
        
    sb.table("splat_jobs").update({
        "status": "training", 
        "stage_message": "Training Gaussian Splats on GPU..."
    }).eq("id", job_id).execute()

    print("Starting training...")
    max_steps = 7000 if quality_preset == "fast" else (15000 if quality_preset == "balanced" else 30000)
    output_dir = Path("/workspace/outputs")
    
    config_yml_exists = False
    config_files = list(Path(f"{persistent_workspace}/outputs").glob("**/*/config.yml")) if (persistent_workspace / "outputs").exists() else []
    if config_files:
        config_yml_exists = True
        print("Restoring training outputs from checkpoint...")
        output_dir.mkdir(parents=True, exist_ok=True)
        os.system(f"cp -r {persistent_workspace}/outputs/* {output_dir}/")
        
    if not config_yml_exists:
        try:
            cmd_train = [
                "ns-train", "splatfacto",
                "--data", str(workspace),
                "--output-dir", str(output_dir),
                "--max-num-iterations", str(max_steps),
                "--vis", "tensorboard",
                "nerfstudio-data"
            ]
            
            process = subprocess.Popen(cmd_train, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                print(line, end="")
                
            process.wait()
            if process.returncode != 0:
                error = f"Training failed with exit code {process.returncode}"
                sb.table("splat_jobs").update({"status": "failed", "error_message": error}).eq("id", job_id).execute()
                return {"success": False, "error": error}
                
            print("Checkpointing training data...")
            os.system(f"cp -r {output_dir} {persistent_workspace}/")
            vol.commit()
        except Exception as e:
            error = f"Exception in training: {e}"
            sb.table("splat_jobs").update({"status": "failed", "error_message": error}).eq("id", job_id).execute()
            return {"success": False, "error": error}
        
    print("Exporting splat files...")
    try:
        config_files = list(output_dir.glob("**/*/config.yml"))
        if not config_files:
            raise RuntimeError("No config.yml found in output_dir")
        config_file = config_files[0]
        
        ply_path = workspace / "splat.ply"
        cmd_export_ply = [
            "ns-export", "gaussian-splat",
            "--load-config", str(config_file),
            "--output-dir", str(workspace)
        ]
        r = subprocess.run(cmd_export_ply, capture_output=True, text=True)
        if r.returncode != 0:
            error = f"Export failed: {r.stderr[-500:]}"
            sb.table("splat_jobs").update({"status": "failed", "error_message": error}).eq("id", job_id).execute()
            return {"success": False, "error": error}
            
    except Exception as e:
        error = f"Failed to export splat: {e}"
        sb.table("splat_jobs").update({"status": "failed", "error_message": error}).eq("id", job_id).execute()
        return {"success": False, "error": error}
        
    print("Compressing to .splat format to bypass 50MB limit...")
    try:
        sb.table("splat_jobs").update({"status": "compressing", "stage_message": "Compressing 3D models..."}).eq("id", job_id).execute()
        
        # Check if the export generated .ply or .splat directly in the workspace directory
        actual_ply = None
        for p in workspace.iterdir():
            if p.suffix == ".ply" and "splat" in p.name.lower():
                actual_ply = p
                break
        
        if not actual_ply:
            actual_ply = workspace / "splats" / "splat.ply" # Check ns-export defaults
            
        if actual_ply and actual_ply.exists():
            ply_path = actual_ply
            
        import numpy as np
        from plyfile import PlyData
        
        plydata = PlyData.read(str(ply_path))
        v = plydata['vertex']
        n = len(v)
        
        dt = np.dtype([
            ('pos', 'f4', 3),
            ('scale', 'f4', 3),
            ('color', 'u1', 4),
            ('rot', 'u1', 4)
        ])
        
        data = np.zeros(n, dtype=dt)
        data['pos'][:, 0] = v['x']
        data['pos'][:, 1] = v['y']
        data['pos'][:, 2] = v['z']
        
        data['scale'][:, 0] = np.exp(v['scale_0'])
        data['scale'][:, 1] = np.exp(v['scale_1'])
        data['scale'][:, 2] = np.exp(v['scale_2'])
        
        SH_C0 = 0.28209479177387814
        data['color'][:, 0] = np.clip((0.5 + SH_C0 * v['f_dc_0']) * 255, 0, 255)
        data['color'][:, 1] = np.clip((0.5 + SH_C0 * v['f_dc_1']) * 255, 0, 255)
        data['color'][:, 2] = np.clip((0.5 + SH_C0 * v['f_dc_2']) * 255, 0, 255)
        data['color'][:, 3] = np.clip((1 / (1 + np.exp(-v['opacity']))) * 255, 0, 255)
        
        rots = np.vstack((v['rot_0'], v['rot_1'], v['rot_2'], v['rot_3'])).T
        rots /= np.linalg.norm(rots, axis=1, keepdims=True)
        data['rot'] = np.clip(rots * 128 + 128, 0, 255)
        
        splat_path = workspace / "splat.splat"
        with open(splat_path, 'wb') as f:
            f.write(data.tobytes())
            
        print("Uploading .splat results...")
        sb.table("splat_jobs").update({"stage_message": "Uploading compressed 3D model..."}).eq("id", job_id).execute()
        
        with open(splat_path, "rb") as f:
            sb.storage.from_(bucket).upload(
                f"{storage_path}/splat.splat", 
                f.read(),
                file_options={"content-type": "application/octet-stream", "upsert": "true"}
            )
            
        ply_url = sb.storage.from_(bucket).get_public_url(f"{storage_path}/splat.splat")
        supersplat_url = f"https://playcanvas.com/supersplat/editor?load={ply_url}"
        
        sb.table("splat_jobs").update({
            "status": "ready",
            "progress": 100,
            "stage_message": "Splat is ready to view!",
            "splat_url": ply_url,
            "supersplat_url": supersplat_url
        }).eq("id", job_id).execute()
        
    except Exception as e:
        error = f"Failed to upload final splat: {e}"
        sb.table("splat_jobs").update({"status": "failed", "error_message": error}).eq("id", job_id).execute()
        return {"success": False, "error": error}
        
    return {"success": True, "splat_url": ply_url}

