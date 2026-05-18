#!/usr/bin/env python3
import numpy as np

def main():
    print("Generating inhomogeneous patient CT phantom with frontal/rear bone plates...")
    
    # Grid dimensions: 60 x 60 x 300 voxels
    # Z: 300 voxels (spacing 1.0 mm, total 30.0 cm, from z = -15.0 cm to +15.0 cm)
    # Y: 60 voxels (spacing 2.0 mm, total 12.0 cm, from y = -6.0 cm to +6.0 cm)
    # X: 60 voxels (spacing 2.0 mm, total 12.0 cm, from x = -6.0 cm to +6.0 cm)
    num_x, num_y, num_z = 60, 60, 300
    
    # Initialize with Air (-1000 HU)
    grid = np.full((num_z, num_y, num_x), -1000, dtype=np.int16)
    
    # Define coordinate space in millimeters relative to the center
    zs = np.linspace(-150.0 + 0.5, 150.0 - 0.5, num_z)
    ys = np.linspace(-60.0 + 1.0, 60.0 - 1.0, num_y)
    xs = np.linspace(-60.0 + 1.0, 60.0 - 1.0, num_x)
    
    # Z-axis goes from index 0 to 299, representing entering from z = -15 cm to z = +15 cm
    Z, Y, X = np.meshgrid(zs, ys, xs, indexing='ij')
    
    # 1. Main Head Cylinder (Soft Tissue: 0 HU, represents brain)
    # Radius = 50 mm, extending from z = -120 mm to z = 120 mm
    head_mask = (X**2 + Y**2 <= 50.0**2) & (Z >= -120.0) & (Z <= 120.0)
    grid[head_mask] = 0
    
    # 2. Skull Bone (Cortical Bone: +1000 HU)
    # Radial outer shell (radius 45 mm to 50 mm)
    radial_bone = (X**2 + Y**2 <= 50.0**2) & (X**2 + Y**2 > 45.0**2) & (Z >= -120.0) & (Z <= 120.0)
    grid[radial_bone] = 1000
    
    # Frontal Bone Plate (Z = -120 mm to -115 mm) across the full head radius
    frontal_bone = (X**2 + Y**2 <= 50.0**2) & (Z >= -120.0) & (Z <= -115.0)
    grid[frontal_bone] = 1000
    
    # Rear Bone Plate (Z = 115 mm to 120 mm) across the full head radius
    rear_bone = (X**2 + Y**2 <= 50.0**2) & (Z >= 115.0) & (Z <= 120.0)
    grid[rear_bone] = 1000
    
    # 3. Sinus Air Cavity (Air: -1000 HU)
    # Located in front of the head at z = -80 mm, y = 0, x = 0 (radius = 16 mm sphere)
    # This sits behind the frontal bone plate (which ends at Z = -115 mm). Perfect!
    sinus_mask = (X**2 + Y**2 + (Z + 80.0)**2 <= 16.0**2)
    grid[sinus_mask] = -1000
    
    # 4. Deep-Seated Brain Tumor (Tumor soft tissue: +50 HU)
    # Center of head is z = 0, let's put the target tumor at z = +20 mm, y = 0, x = 0 (radius = 12 mm sphere)
    tumor_mask = (X**2 + Y**2 + (Z - 20.0)**2 <= 12.0**2)
    grid[tumor_mask] = 50
    
    import os
    os.makedirs("data", exist_ok=True)
    
    # Save the 3D voxel array as a signed 16-bit short binary file
    grid.tofile("data/patient_ct.raw")
    
    # Create the MHD header file
    mhd_content = """ObjectType = Image
NDims = 3
BinaryData = True
BinaryDataByteOrderMSB = False
CompressedData = False
TransformMatrix = 1 0 0 0 1 0 0 0 1
Offset = -60.0 -60.0 -150.0
CenterOfRotation = 0 0 0
AnatomicalOrientation = RAI
ElementSpacing = 2.0 2.0 1.0
DimSize = 60 60 300
ElementType = MET_SHORT
ElementDataFile = patient_ct.raw
"""
    with open("data/patient_ct.mhd", "w") as f:
        f.write(mhd_content)
        
    print("Patient CT phantom generated successfully with frontal/rear bone plates!")

if __name__ == "__main__":
    main()
