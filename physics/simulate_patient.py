#!/usr/bin/env python3
import opengate as gate
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Run OpenGATE 10 Hadron Beam Simulation on Inhomogeneous Patient CT Phantom")
    parser.add_argument("--modality", type=str, default="proton", choices=["proton", "carbon"], help="Beam modality: proton or carbon (default: proton)")
    parser.add_argument("--energy", type=float, default=150.0, help="Beam energy in MeV (or MeV/u for Carbon, default: 150.0)")
    parser.add_argument("--particles", type=int, default=10000, help="Number of primary particles (default: 10000)")
    parser.add_argument("--mode", type=str, default="single", choices=["single", "sobp", "multifield"], help="Treatment plan mode: single, sobp, or multifield (default: single)")
    parser.add_argument("--output", type=str, default="output/patient_dose.mhd", help="Output MHD file path (default: output/patient_dose.mhd)")
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

    # Geometry: Inhomogeneous Patient CT Voxelized Volume
    patient = sim.add_volume("Image", "patient_ct")
    patient.image = "data/patient_ct.mhd"
    patient.material = "G4_AIR" # Default background material for voxels outside specified HU
    
    # Define HU-to-material ranges in-memory (no mapping text files needed!)
    # Air: -1500 HU to -500 HU -> G4_AIR
    # Soft Tissue (Brain/Tumor): -500 HU to 250 HU -> G4_WATER
    # Cortical Bone (Skull): 250 HU to 3000 HU -> G4_BONE_COMPACT_ICRU
    patient.voxel_materials = [
        [-1500.0, -500.0, "G4_AIR"],
        [-500.0, 250.0, "G4_WATER"],
        [250.0, 3000.0, "G4_BONE_COMPACT_ICRU"]
    ]
    
    patient.translation = [0, 0, 0] # Centered at origin, spans z = -15 cm to +15 cm

    # Physics list
    sim.physics_manager.physics_list_name = "QGSP_BIC_HP"
    
    # Sources Setup based on the selected Mode
    sources = []
    
    if args.mode == "single":
        # 1. Single Pencil Beam (Anterior)
        source = sim.add_source("GenericSource", "pencil_beam")
        source.activity = args.particles * Bq
        source.position.type = "point"
        source.position.translation = [0, 0, -16 * cm]
        source.direction.type = "momentum"
        source.direction.momentum = [0, 0, 1]
        
        # Apply modality specific settings
        if args.modality == "proton":
            source.particle = "proton"
            source.energy.type = "mono"
            source.energy.mono = args.energy * MeV
        else:
            source.particle = "ion 6 12"
            total_energy = args.energy * 12.0
            source.energy.type = "mono"
            source.energy.mono = total_energy * MeV
            
    elif args.mode == "sobp":
        # 2. Spread-Out Bragg Peak (SOBP): 3 energy-shifted sources
        # We shift energy shallowly to span the tumor volume
        energy_offsets = [0.0, -5.0, -10.0] if args.modality == "proton" else [0.0, -10.0, -20.0]
        weights = [1.0, 0.5, 0.3] # Deepest beam gets highest weight for flat sum
        total_weight = sum(weights)
        
        for i, (offset, weight) in enumerate(zip(energy_offsets, weights)):
            src_name = f"sobp_beam_{i}"
            source = sim.add_source("GenericSource", src_name)
            # Normalize activity by source weight
            source.activity = (args.particles * weight / total_weight) * Bq
            source.position.type = "point"
            source.position.translation = [0, 0, -16 * cm]
            source.direction.type = "momentum"
            source.direction.momentum = [0, 0, 1]
            
            src_energy = args.energy + offset
            if args.modality == "proton":
                source.particle = "proton"
                source.energy.type = "mono"
                source.energy.mono = src_energy * MeV
            else:
                source.particle = "ion 6 12"
                total_energy = src_energy * 12.0
                source.energy.type = "mono"
                source.energy.mono = total_energy * MeV
                
    elif args.mode == "multifield":
        # 3. Multi-Field / Multi-Port: 2 co-planar fields intersecting at tumor center
        half_particles = args.particles / 2.0
        
        # Field 1: Anterior Beam (along Z axis)
        source_ant = sim.add_source("GenericSource", "anterior_beam")
        source_ant.activity = half_particles * Bq
        source_ant.position.type = "point"
        source_ant.position.translation = [0, 0, -16 * cm]
        source_ant.direction.type = "momentum"
        source_ant.direction.momentum = [0, 0, 1]
        
        # Field 2: Lateral Beam (along X axis, targeting tumor center z = 2.0 cm)
        source_lat = sim.add_source("GenericSource", "lateral_beam")
        source_lat.activity = half_particles * Bq
        source_lat.position.type = "point"
        source_lat.position.translation = [-16 * cm, 0, 2.0 * cm]
        source_lat.direction.type = "momentum"
        source_lat.direction.momentum = [1, 0, 0]
        
        # Apply modality specific settings to both fields
        for source in [source_ant, source_lat]:
            if args.modality == "proton":
                source.particle = "proton"
                source.energy.type = "mono"
                source.energy.mono = args.energy * MeV
            else:
                source.particle = "ion 6 12"
                total_energy = args.energy * 12.0
                source.energy.type = "mono"
                source.energy.mono = total_energy * MeV

    # Scoring: Central Column DoseActor
    # We score a thin column (2.0mm x 2.0mm, matching a single CT voxel column) along the Z axis (300 voxels)
    dose = sim.add_actor("DoseActor", "dose_actor")
    dose.attached_to = "patient_ct"
    dose.size = [1, 1, 300]
    dose.spacing = [2 * mm, 2 * mm, 1 * mm] # central 1-voxel column
    dose.output_filename = Path(args.output).name
    
    dose.dose.active = True
    dose.edep.active = True

    # Stats Actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = f"{args.modality}_patient_{args.mode}_stats.txt"

    # Run
    print(f"Starting Patient CT Simulation...")
    print(f"Modality: {args.modality.upper()}")
    print(f"Mode: {args.mode.upper()}")
    print(f"Energy: {args.energy} MeV" + ("" if args.modality == "proton" else " / nucleon"))
    print(f"Particles: {args.particles}")
    print(f"Output saved to: {args.output}")
    sim.run()
    print("Patient CT Simulation finished successfully!")

if __name__ == "__main__":
    main()
