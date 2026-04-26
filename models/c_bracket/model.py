import cadquery as cq

def build(model_config):
    # Units in inches from config, converted to mm
    inch = 25.4
    # Fetch dimensions from config or use defaults
    w = model_config.get("width_in", 0.5) * inch
    t = model_config.get("thickness_in", 0.125) * inch
    base_l = model_config.get("length_in", 1.0) * inch
    back_h = model_config.get("back_height_in", 2.0) * inch
    lip_h = model_config.get("lip_height_in", 0.5) * inch
    
    # Fillet radius - 1/32" (approx 0.8mm) is a nice small roundover
    r = (1/32) * inch 

    # Construct the C-bracket using boxes for precision and explicit centering
    # Back plate: centered on X (from -w/2 to w/2), starts at Y=0, Z=0
    back_plate = cq.Workplane("XY").box(w, t, back_h, centered=(True, False, False))
    
    # Base plate: centered on X, starts at Y=t (to avoid overlap with back plate), Z=0
    # Length is base_l - t to maintain the overall depth as base_l
    base = (
        cq.Workplane("XY")
        .workplane(offset=0)
        .center(0, t)
        .box(w, base_l - t, t, centered=(True, False, False))
    )
    
    # Lip: centered on X, starts at Y=base_l-t, Z=t
    # Height is lip_h - t to maintain the overall lip height as lip_h
    lip = (
        cq.Workplane("XY")
        .workplane(offset=t)
        .center(0, base_l - t)
        .box(w, t, lip_h - t, centered=(True, False, False))
    )
    
    # Combine all parts into one solid
    result = back_plate.union(base).union(lip)
    
    # Round over all edges using the specified radius
    # We do this before adding the hole so the hole edges stay sharp
    result = result.edges().fillet(r)
    
    # Add a countersunk hole for a #8 wood screw
    # Shank clearance: 4.5mm, Head diameter: 8.5mm, Angle: 82 degrees
    # Positioned at the horizontal center (X=0) and in the top 1/3 of the back plate
    hole_z = back_h - (back_h / 6.0)
    
    # Select the "inside" face of the back plate (the one facing the picture)
    # This face is at Y=t and faces the +Y direction.
    # We filter to ensure we don't accidentally pick the lip's face.
    target_face = result.faces(">Y").filter(lambda f: f.Center().y < base_l/2)
    
    # The vertical center of this face (above the base) is at Z = (t + back_h) / 2
    face_center_z = (t + back_h) / 2
    
    result = (
        target_face.workplane()
        .center(0, hole_z - face_center_z)
        .cskHole(4.5, 8.5, 82)
    )
    
    return result
