#!/usr/bin/env python3
import opengate as gate
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Run OpenGATE 10 Proton Beam Simulation")
    parser.add_argument("--energy", type=float, default=150.0, help="Proton energy in MeV (default: 150.0)")
    parser.add_argument("--particles", type=int, default=10000, help="Number of primary particles (default: 10000)")
    parser.add_argument("--output", type=str, default="output/proton_dose.mhd", help="Output MHD file path (default: output/proton_dose.mhd)")
    args = parser.parse_args()

    # Create simulation
    sim = gate.Simulation()
    sim.output_dir = Path(args.output).parent
    sim.output_dir.mkdir(parents=True, exist_ok=True)

    # Units
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    # Geometry
    # Water Phantom: 10x10x30 cm
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 30 * cm]
    phantom.material = "G4_WATER"
    phantom.translation = [0, 0, 0] # Centered at origin, spans z = -15 cm to +15 cm
    phantom.color = [0, 0, 1, 1] # Blue

    # Physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_HP"
    
    # Source: pencil beam
    source = sim.add_source("GenericSource", "pencil_beam")
    source.particle = "proton"
    source.activity = args.particles * Bq # Number of particles is represented by activity for 1 second run
    
    # Beam position: 1 cm outside the phantom (entrance is at z = -15 cm)
    source.position.type = "point"
    source.position.translation = [0, 0, -16 * cm]
    
    # Beam direction: straight along Z
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    
    # Beam energy
    source.energy.type = "mono"
    source.energy.mono = args.energy * MeV

    # Scoring: DoseActor
    dose = sim.add_actor("DoseActor", "dose_actor")
    dose.attached_to = "phantom"
    dose.size = [1, 1, 300] # 300 voxels along Z
    dose.spacing = [10 * cm, 10 * cm, 1 * mm] # 1 mm spacing along Z to span the 30 cm length
    dose.output_filename = Path(args.output).name
    
    # Enable dose and energy deposition (edep) scoring
    dose.dose.active = True
    dose.edep.active = True

    # Stats Actor (to record execution details)
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "proton_stats.txt"

    # Run
    print(f"Starting Proton Simulation...")
    print(f"Energy: {args.energy} MeV")
    print(f"Number of primary particles: {args.particles}")
    print(f"Output will be saved to: {args.output}")
    sim.run()
    print("Proton Simulation finished successfully!")

if __name__ == "__main__":
    main()
