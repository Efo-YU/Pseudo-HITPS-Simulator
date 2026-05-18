#!/usr/bin/env python3
import os
import time
import requests
import opengate_core.g4DataSetup as g4s

def robust_download(url, out, retries=15, delay=5):
    print(f"\n[Robust Download] Starting fresh download (no-resume) for:")
    print(f"URL: {url}")
    print(f"Target: {out}")
    
    for attempt in range(retries):
        # Always remove partial/target files first to start from absolute scratch
        temp_file = str(out) + ".part"
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        if os.path.exists(out):
            try:
                os.remove(out)
            except Exception:
                pass
                
        try:
            print(f"Attempt {attempt + 1}/{retries}...")
            # Use stream=True and a generous timeout (60 seconds)
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                # Track download size
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                
                with open(temp_file, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024): # 1 MB chunks
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\rProgress: {percent:.1f}% ({downloaded / (1024*1024):.1f}/{total_size / (1024*1024):.1f} MB)", end="", flush=True)
                            else:
                                print(f"\rDownloaded: {downloaded / (1024*1024):.1f} MB", end="", flush=True)
                print()
            os.rename(temp_file, str(out))
            print(f"[Robust Download] Successfully downloaded {url}!")
            return
        except Exception as e:
            print(f"\n[Robust Download] Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                print(f"Retrying from scratch in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"[Robust Download] Exceeded maximum retries.")
                raise e

# Monkeypatch the download function in the opengate_core module
g4s.download_with_resume = robust_download

if __name__ == "__main__":
    print("Starting Geant4 robust data download and setup...")
    g4s.check_g4_data()
    print("Geant4 data check and setup complete!")
