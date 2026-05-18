# Pseudo-HITPS Simulator (GATE 10)

[![OpenGATE 10](https://img.shields.io/badge/OpenGATE-10.0-blueviolet.svg)](https://github.com/OpenGATE/opengate)
[![Geant4 Backend](https://img.shields.io/badge/Geant4-11.2-blue.svg)](https://geant4.web.cern.ch/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Antigravity](https://img.shields.io/badge/Designed%20with-Antigravity%20%E2%9C%A8-orange.svg?style=flat-square)](#-developed-with-antigravity)

An advanced, interactive **Pseudo-HITPS Simulator (GATE 10)** and Monte Carlo simulation suite built on top of **OpenGATE 10** (the next-generation Python-native Geant4-driven particle transport engine). 

This platform bridges the gap between macroscopic particle transport (Physical Absorbed Dose) and microscopic cellular radiobiology (Relative Biological Effectiveness, Cell Survival Fraction, and DNA Double-Strand Breaks) using two clinical world-standards: the Japanese **MKM** (Microdosimetric Kinetic Model) and the European **LEM** (Local Effect Model).

---

## 🧭 Project Roadmap & Architecture

```
[Monte Carlo Simulation (OpenGATE 10)]
    ├── Proton Pencil Beam (1H)
    └── Heavy Carbon-12 Ion (12C)
             │
             ▼ [3D Scored edep.raw MetaImage Volume]
[Biophysical LET-RBE Server (Python 3)]
    ├── Inhomogeneous HU-to-Material mapping
    ├── Dose-Averaged stopping power (LETd)
    ├── MKM (Domain Saturation / Overkill Model) vs. LEM (Sigmoidal Track Overlap Model)
    └── Microscopic DNA Breaks (SSB vs. fatal clustered DSB) & LQ survival (SF%)
             │
             ▼ [JSON over REST APIs]
[Clinical TPS Console UI (HTML5 / Vanilla CSS / Chart.js)]
    ├── Sagittal Patient CT Slice / Water Phantom Viewports
    ├── Dual Nozzle Co-planar sweep & Modulation animations
    ├── Chart.js Biophysical Curve toggles (Physical, Biological, DNA Breaks)
    ├── Microscopic 3D Spinning DNA Helix snap-break canvas
    └── Dynamic Biophysical Telemetry Grid & Treatment Plan Report Exporter
```

---

## 🛠 Prerequisites & Installation

### 1. System Requirements
- **Operating System**: Linux (Ubuntu 20.04 LTS or newer recommended) or macOS.
- **Python**: Version 3.10 or 3.11 (native pip-installable opengate).
- **RAM**: Minimum 8GB (16GB recommended for 3D patient CT transport tracking).

### 2. Environment Setup
Create a Python virtual environment and install OpenGATE 10 and scientific dependencies:
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install OpenGATE 10 and scientific libraries
pip install --upgrade pip
pip install opengate numpy matplotlib astropy scipy
```

### 3. Geant4 Core Datasets Bootstrapping
Geant4 requires physics database files (cross-sections, range tables, etc.) to run. Use our automated, robust downloader utility to safely download and extract the required datasets:
```bash
python3 bootstrap_g4.py
```
This utility automatically configures all environment variables (such as `G4LEDATA`, `G4LEVELGAMMADATA`, etc.) and unpacks the physics libraries locally to prevent CERN download timeouts.

### 4. Patient CT Inhomogeneous Phantom Generation
To run patient-specific simulations, programmatically construct the 3D voxelized head phantom:
```bash
python3 physics/generate_ct_phantom.py
```
This script constructs a compliant 3D Hounsfield Unit (HU) MetaImage voxel phantom volume generating two files in your `data/` directory:
- `data/patient_ct.mhd` (MetaImage header detailing voxel spacing, dimensions `60x60x300`, and offsets)
- `data/patient_ct.raw` (Double-precision binary voxel HU file containing skull bones, sinuses, brain tissue, and tumor PTV).

---

## 🚀 How to Run & Use

### 1. Launch the Biophysical API Server
The server hosts the HTML5 clinical console dashboard and manages the background execution of the Geant4 Monte Carlo simulation subprocesses.
```bash
# Start the server (hosts on Port 8080)
python3 server.py
```
*Console output will display:*
```text
=======================================================
  Hadron Therapy Full-Stack Server active on Port 8080
  URL: http://localhost:8080/
=======================================================
```
Leave this process active.

### 2. Access the Treatment Planning Console
1. Open your web browser and navigate to:
   ```http
   http://localhost:8080/
   ```
2. **Force reload** the page (`Ctrl + F5` on Windows/Linux or `Cmd + Shift + R` on macOS) to ensure you bypass any cached local assets.

### 3. Interactive Web Console Guide
1. **Target Geometry**: Toggle between **"水ファントム"** (homogeneous water) and **"患者CT (頭部)"** (voxelized sagittal head CT).
2. **Treatment Technique**: Select:
   - **単一門 (Single Port)**: Single anterior scanning pencil beam.
   - **多門照射 (Multi-Field)**: Coplanar Anterior + Lateral cross-firing ports intersecting at the brain tumor target to spare normal bone/sinus tissue.
   - **SOBP (Spread-Out Bragg Peak)**: Multi-energy stacked scanning raster pulses.
3. **Beam Modality**: Select **陽子線 (Proton)** or **重粒子 (Carbon-12)**.
4. **Radiobiology Model**: Select between the **MKM** (Japanese clinical overkill-saturation standard) and the **LEM** (European clinical track-overlap standard).
5. Click **"Simulate Irradiation"**:
   - Watch the active scanning nozzleSweep sweep the viewport.
   - Observe the **microscopic DNA helix animation snap in two** inside the tumor peak, flashing a neon red `FATAL DSB` alarm.
   - Toggle the 1D chart curves between **物理線量 (Physical)**, **生物線量 (Biological)**, and **DNA鎖切断 (SSB/DSB curves)**.
6. Click **"Export Plan Summary"** to generate the biophysically-validated clinical treatment planning summary report.

---

## 💻 Standalone Command-Line Simulations

You can also run independent, high-statistics Monte Carlo simulations directly inside your terminal:

### A. Patient CT Carbon-12 SOBP Plan (10,000 Particles)
```bash
python3 simulate_patient.py --modality carbon --energy 290 --particles 10000 --mode sobp --output output/patient_dose.mhd
```

### B. Patient CT Proton Multi-Field Plan (20,000 Particles)
```bash
python3 simulate_patient.py --modality proton --energy 150 --particles 20000 --mode multifield --output output/patient_dose.mhd
```

### C. Extract & Plot Scored Binary Dose Profiles
```bash
python3 plot_results.py
```

---

## ⚠️ Disclaimer / 免責事項

> [!IMPORTANT]
> ### 🚨 Clinical Disclaimer (English)
> **THIS SOFTWARE IS FOR HIGHLY SIMPLIFIED DEMONSTRATION AND ILLUSTRATIVE PURPOSES ONLY.**
> - This software is **INCOMPLETE AND UNRELIABLE**. It is **COMPLETELY UNFIT FOR ANY PRACTICAL USE**, including serious educational or academic research, and may contain significant physical, biological, or scientific errors.
> - It is **NOT** clinically certified, and is **NOT** a medical device under any regulatory standard (e.g., US FDA 510(k), European CE mark, or Japanese PMDA).
> - Do **NOT** use this software for making clinical decisions, calculating actual patient radiotherapy doses, or planning human radiation treatments.
> - The biophysical equations, Hounsfield Unit mapping ranges, and analytical LET/RBE formulations (MKM & LEM) implemented represent simplified illustrative models. Real clinical patient plans require certified commercial Treatment Planning Systems (TPS) running strictly calibrated absolute dose engines.
> - The authors and developers assume **NO liability or responsibility** for any scientific errors, physical inaccuracies, medical decisions, radiation misadministrations, or direct/indirect damages arising from any use of this software.

---

> [!IMPORTANT]
> ### 🚨 免責事項 (日本語)
> **本ソフトウェアは、極めて単純化された簡易デモンストレーションおよび視覚的解説のみを目的としています。**
> - 本ソフトウェアは**極めて不完全かつ不正確なものであり、教育や学術研究目的であっても全く実用に耐えません。** 物理的・生物物理学的な科学的誤りを多数含む可能性があり、その正確性、整合性、有用性に関して作者および開発者は一切の保証を行いません。
> - 本ソフトウェアは**臨床用としての認定を受けておらず**、いかなる薬事規制基準（例：日本PMDA、米国FDA 510(k)、欧州CEマーク）における「医療機器」でもありません。
> - 実際の患者の放射線治療計画の作成、実際の臨床線量計算、またはヒトに対する照射治療の設計には**絶対に使用しないでください**。
> - 本システムに実装されている生物物理方程式（SSB/DSB）、Hounsfield Unit（HU）材料マッピング、および LET/RBE 導出数理（MKM・LEMモデル）は、簡易的な説明用モデルに過ぎません。実際の治療計画には、厳密にキャリブレーションされた絶対線量エンジンを備えた認定済みの商業用治療計画装置（TPS）を使用する必要があります。
> - 本ソフトウェアの使用、または含まれる科学的誤りや不正確さに起因して発生した、医療判断上の誤り、過剰照射・誤照射、およびそれに起因する直接的・間接的な損害等について、開発者および著者は**一切の責任を負いません。**

---

## 📂 Directory Structure Overview

The repository has been structured for optimal simplicity and ease of local terminal execution:

```text
hello-opengate/
├── README.md               # Complete setup, execution manual, and clinical disclaimer
├── .gitignore              # Multi-layer standard Git exclusion manifest (ignores virtualenv, datasets)
├── server.py               # Biophysical API Server (LET-RBE, MKM/LEM, DNA damage equations)
├── index.html              # Premium dark-themed Clinical TPS Console UI (Chart.js & 3D DNA Canvas)
├── generate_ct_phantom.py  # Voxelized inhomogeneous patient head HU phantom compiler
├── simulate_patient.py     # Unified patient CT OpenGATE 10 simulator (Single, SOBP, Multi-field)
├── simulate_proton.py      # Water phantom Proton pencil beam setup
├── simulate_carbon.py      # Water phantom Carbon-12 pencil beam setup
├── bootstrap_g4.py         # Physics libraries automated bootstrap utility
├── plot_results.py         # Scored binary dose visualizer utility
├── patient_ct.mhd          # Generated MetaImage patient phantom header [GIT-IGNORED]
├── patient_ct.raw          # Generated MetaImage patient phantom binary [GIT-IGNORED]
├── output/                 # Geant4 raw scored binary outputs directory [GIT-IGNORED]
└── venv/                   # Local Python Virtual Environment folder [GIT-IGNORED]
```

---

## 🛠️ Developed with Antigravity / Antigravity による共同開発

### 🚀 English
This simulator was designed, implemented, and scientifically validated in partnership with **Antigravity**, Google DeepMind's powerful agentic AI coding assistant. Antigravity assisted in:
- Resolving complex Python-to-JavaScript data serialization gaps.
- Programmatically designing the dual-nozzle sweep animations and Chart.js biophysical curve switching.
- Formulating the clinical **MKM** saturation overkill equations and the **LEM** sigmoidal track overlap models.
- Building the real-time spinning 3D DNA double helix Canvas rendering and its lethal Bragg peak rupture animation.

### 🌸 日本語
本シミュレーターは、Google DeepMind が開発した自律型AIコーディングアシスタント **Antigravity** との共同ペアプログラミングによって設計、実装、および数学的・科学的検証が行われました。Antigravity は以下の開発段階において包括的な貢献を行いました：
- Python-JavaScript 間の高速データ連携における不具合原因の特定およびシームレスな解決。
- Sagittal CT 上を交差掃引するノズルスイープアニメーションと Chart.js による多角的な線量プロットの実装。
- 日本式臨床の **MKM**（飽和過剰死モデル）および欧州式臨床の **LEM**（飛跡重複モデル）の厳密な数理定式化。
- 腫瘍領域（高LET電離域）に到達した際に、DNAらせんが電撃火花と共に真っ二つに破断・崩壊するリアルタイム 3D Canvas アニメーションの設計。

---

## 📄 License
This project is licensed under the MIT License.
