#!/usr/bin/env python3
import opengate as gate
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Run OpenGATE 10 Carbon Ion Beam Simulation")
    parser.add_argument("--energy_per_nucleon", type=float, default=290.0, help="Carbon ion energy per nucleon in MeV/u (default: 290.0)")
    parser.add_argument("--particles", type=int, default=10000, help="Number of primary particles (default: 10000)")
    parser.add_argument("--output", type=str, default="output/carbon_dose.mhd", help="Output MHD file path (default: output/carbon_dose.mhd)")
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
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 30 * cm]
    phantom.material = "G4_WATER"
    phantom.translation = [0, 0, 0] # Centered at origin, spans z = -15 cm to +15 cm
    phantom.color = [0, 0, 1, 1] # Blue

    # Physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_HP"
    
    # Source: pencil beam of Carbon ions (Z=6, A=12)
    source = sim.add_source("GenericSource", "pencil_beam")
    source.particle = "ion 6 12"
    source.activity = args.particles * Bq
    
    # Beam position: 1 cm outside the phantom (entrance is at z = -15 cm)
    source.position.type = "point"
    source.position.translation = [0, 0, -16 * cm]
    
    # Beam direction: straight along Z
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    
    # Beam energy: Carbon-12 has A=12 nucleons
    total_energy = args.energy_per_nucleon * 12.0
    source.energy.type = "mono"
    source.energy.mono = total_energy * MeV

    # Scoring: DoseActor
    dose = sim.add_actor("DoseActor", "dose_actor")
    dose.attached_to = "phantom"
    dose.size = [1, 1, 300] # 300 voxels along Z
    dose.spacing = [10 * cm, 10 * cm, 1 * mm] # 1 mm spacing along Z to span the 30 cm length
    dose.output_filename = Path(args.output).name
    
    # Enable dose and energy deposition (edep) scoring
    dose.dose.active = True
    dose.edep.active = True

    # Stats Actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "carbon_stats.txt"

    # Run
    print(f"Starting Carbon Ion Simulation...")
    print(f"Energy per nucleon: {args.energy_per_nucleon} MeV/u (Total energy: {total_energy:.1f} MeV)")
    print(f"Number of primary particles: {args.particles}")
    print(f"Output will be saved to: {args.output}")
    sim.run()
    print("Carbon Ion Simulation finished successfully!")

if __name__ == "__main__":
    main()
