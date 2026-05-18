#!/usr/bin/env python3
import http.server
import socketserver
import json
import subprocess
import os
import glob
import numpy as np
from pathlib import Path

PORT = 8080

class HadronConsoleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Route root path to index.html
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()
        else:
            return super().do_GET()

    def do_POST(self):
        if self.path == "/api/simulate":
            self._handle_simulate()
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_simulate(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            params = json.loads(post_data.decode('utf-8'))
            modality = params.get("type", "proton")
            energy = float(params.get("energy", 150.0))
            particles = int(params.get("particles", 10000))
            phantom_type = params.get("phantom_type", "water") # "water" or "patient"
            mode = params.get("mode", "single") # "single", "sobp", or "multifield"
            bio_model = params.get("bio_model", "mkm") # "mkm" or "lem"
        except Exception as e:
            self._send_json({"error": f"Invalid request body: {e}"}, status=400)
            return

        print(f"\n[SERVER] Received simulation request: Modality={modality}, Energy={energy}, Particles={particles}, Phantom={phantom_type}, Mode={mode}, BioModel={bio_model}")
        
        # Determine paths and execute subprocesses
        output_prefix = ""
        cmd = []
        
        if phantom_type == "patient":
            output_prefix = "output/patient_dose"
            cmd = [
                "python3", "physics/simulate_patient.py",
                "--modality", modality,
                "--energy", str(energy),
                "--particles", str(particles),
                "--mode", mode,
                "--output", f"{output_prefix}.mhd"
            ]
        else:
            # Water phantom
            if modality == "proton":
                output_prefix = "output/proton_dose"
                cmd = [
                    "python3", "physics/simulate_proton.py",
                    "--energy", str(energy),
                    "--particles", str(particles),
                    "--output", f"{output_prefix}.mhd"
                ]
            elif modality == "carbon":
                output_prefix = "output/carbon_dose"
                cmd = [
                    "python3", "physics/simulate_carbon.py",
                    "--energy_per_nucleon", str(energy),
                    "--particles", str(particles),
                    "--output", f"{output_prefix}.mhd"
                ]
            else:
                self._send_json({"error": f"Unsupported modality: {modality}"}, status=400)
                return

        try:
            print(f"[SERVER] Running simulation command: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            print("[SERVER] Simulation script finished successfully.")
        except subprocess.CalledProcessError as e:
            print(f"[SERVER] Error executing simulation script: {e.stderr}")
            self._send_json({
                "error": "Simulation execution failed",
                "details": e.stderr
            }, status=500)
            return

        # Load the generated binary file
        pattern = f"{output_prefix}*edep.raw"
        files = glob.glob(pattern)
        if not files:
            # Try lowercase
            pattern = f"{output_prefix}*edep.raw".lower()
            files = glob.glob(pattern)

        if not files:
            self._send_json({"error": f"Simulation output binary file not found for pattern: {output_prefix}*edep.raw"}, status=500)
            return

        raw_file = files[0]
        print(f"[SERVER] Parsing scored DoseActor binary file: {raw_file}")
        
        try:
            # Read binary float64 (double precision) data
            data = np.fromfile(raw_file, dtype=np.float64)
            num_voxels = len(data)
            
            # Clinical calculations from actual Monte Carlo array
            peak_idx = int(np.argmax(data))
            voxel_size_cm = 30.0 / num_voxels # 30 cm water/patient phantom
            
            peak_depth = peak_idx * voxel_size_cm + (voxel_size_cm / 2.0)
            peak_val = float(data[peak_idx])
            entrance_val = float(data[0])
            peak_to_entrance = peak_val / entrance_val if entrance_val > 0 else 0.0
            
            # Find distal fall-off ranges R90 and R50 (after the peak)
            r90_idx = peak_idx
            for i in range(peak_idx, num_voxels):
                if data[i] <= 0.90 * peak_val:
                    r90_idx = i
                    break
            r90_depth = r90_idx * voxel_size_cm + (voxel_size_cm / 2.0)

            r50_idx = peak_idx
            for i in range(peak_idx, num_voxels):
                if data[i] <= 0.50 * peak_val:
                    r50_idx = i
                    break
            r50_depth = r50_idx * voxel_size_cm + (voxel_size_cm / 2.0)

            rbe = 1.10 if modality == "proton" else 3.0

            # -------------------------------------------------------------
            # Phase 4 Biophysical Scorer: LET, RBE, DNA breaks & LQ survival
            # -------------------------------------------------------------
            let_list = []
            rbe_list = []
            bio_dose_list = []
            ssb_list = []
            dsb_list = []
            survival_list = []
            
            # Parametrization parameters for LET modeling
            if modality == "proton":
                let_ent = 2.0
                let_peak = 15.0
                sigma_let = 0.5
            else:
                let_ent = 12.0
                let_peak = 120.0
                sigma_let = 0.3
                
            max_phys = float(np.max(data)) if np.max(data) > 0 else 1.0
            
            for idx in range(num_voxels):
                z = idx * voxel_size_cm + (voxel_size_cm / 2.0)
                d = peak_depth - z
                
                # Model local dose-averaged LET (stopping power keV/um)
                if d > 0.1:
                    let_val = let_ent + (let_peak - let_ent) * ((1.0 - d / peak_depth) ** 3)
                elif d <= 0.1 and d >= -0.5:
                    let_val = let_peak * np.exp(-(d**2) / (2.0 * sigma_let**2))
                else:
                    # Post peak fragmentation tail
                    let_val = 0.1 if modality == "proton" else 0.5
                    
                # Model local RBE
                if modality == "proton":
                    rbe_val = 1.0 + 0.1 * ((let_val / 2.0) ** 0.6)
                else:
                    if bio_model == "mkm":
                        # MKM: saturation overkill effect at high LET
                        if let_val <= 120.0:
                            rbe_val = 1.0 + (3.5 * let_val / 120.0) * np.exp(-(let_val - 120.0) / 80.0)
                        else:
                            rbe_val = 4.50 * np.exp(-(let_val - 120.0) / 180.0)
                    else:
                        # LEM: sigmoidal track overlap effect
                        rbe_val = 1.0 + 3.5 / (1.0 + np.exp(-(let_val - 75.0) / 20.0))
                    
                phys_val = float(data[idx])
                bio_dose_val = phys_val * rbe_val
                
                # Standard clinical fraction dose scale (2.0 Gy at peak)
                voxel_dose_gy = 2.0 * (phys_val / max_phys)
                
                # DNA Breaks yields (SSB: 80/Gy/cell, DSB: rise from 15 to 80 based on LET)
                alpha_ssb = 80.0
                alpha_dsb = 15.0 + 60.0 * (let_val / 120.0)
                alpha_dsb = min(80.0, alpha_dsb)
                
                ssb_val = alpha_ssb * voxel_dose_gy
                dsb_val = alpha_dsb * voxel_dose_gy
                
                # Cell Survival: LQ model
                alpha_cell = 0.15 * rbe_val
                beta_cell = 0.05
                sf_val = np.exp(-alpha_cell * voxel_dose_gy - beta_cell * (voxel_dose_gy ** 2))
                sf_pct = float(sf_val * 100.0)
                
                let_list.append(float(let_val))
                rbe_list.append(float(rbe_val))
                bio_dose_list.append(float(bio_dose_val))
                ssb_list.append(float(ssb_val))
                dsb_list.append(float(dsb_val))
                survival_list.append(sf_pct)

            # Convert data array to normal list for JSON transmission
            dose_list = [float(x) for x in data]

            response_data = {
                "success": True,
                "modality": modality,
                "energy": energy,
                "particles": particles,
                "phantom_type": phantom_type,
                "mode": mode,
                "bio_model": bio_model,
                "dose": dose_list,
                "let": let_list,
                "rbe": rbe_list,
                "bio_dose": bio_dose_list,
                "ssb": ssb_list,
                "dsb": dsb_list,
                "survival": survival_list,
                "range": float(peak_depth),
                "peakVal": float(peak_to_entrance),
                "r90": float(r90_depth),
                "r50": float(r50_depth),
                "rbe_factor": float(rbe),
                "maxDose": float(peak_val)
            }
            
            print(f"[SERVER] Calculated clinical parameters: PeakDepth={peak_depth:.2f}cm, PeakToEntrance={peak_to_entrance:.2f}x, R90={r90_depth:.2f}cm, R50={r50_depth:.2f}cm")
            print(f"[SERVER] Biophysical evaluation complete: MaxRBE={max(rbe_list):.2f}, MaxTumorDSB={max(dsb_list):.1f}/cell, MinSurvival={min(survival_list):.2f}%")
            self._send_json(response_data)
            
        except Exception as e:
            print(f"[SERVER] Error parsing binary dose files: {e}")
            self._send_json({"error": f"Error parsing binary dose files: {str(e)}"}, status=500)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

def main():
    # Make sure we run in the workspace directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), HadronConsoleHandler) as httpd:
        print(f"\n=======================================================")
        print(f"  Pseudo-HITPS Server (GATE 10) active on Port {PORT}")
        print(f"  URL: http://localhost:{PORT}/")
        print(f"=======================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == "__main__":
    main()
