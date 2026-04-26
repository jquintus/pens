import cadquery as cq

def build(model_config):
    # Units in inches from config, converted to mm
    inch = 25.4
    w = model_config.get("width_in", 0.5) * inch
    t = model_config.get("thickness_in", 0.125) * inch
    base_l = model_config.get("length_in", 1.0) * inch
    back_h = model_config.get("back_height_in", 2.0) * inch
    lip_h = model_config.get("lip_height_in", 0.5) * inch
    
    r = (1/32) * inch 

    # 1. Build the geometry using union
    # We build everything relative to the origin
    # Back plate: X centered, Y from 0 to t, Z from 0 to back_h
    back_plate = cq.Workplane("XY").box(w, t, back_h, centered=(True, False, False))
    
    # Base plate: X centered, Y from t to base_l, Z from 0 to t
    base = (
        cq.Workplane("XY")
        .workplane(offset=0)
        .center(0, t)
        .box(w, base_l - t, t, centered=(True, False, False))
    )
    
    # Lip: X centered, Y from base_l-t to base_l, Z from t to lip_h
    lip = (
        cq.Workplane("XY")
        .workplane(offset=t)
        .center(0, base_l - t)
        .box(w, t, lip_h - t, centered=(True, False, False))
    )
    
    result = back_plate.union(base).union(lip)
    
    # 2. Apply fillets to all edges
    # We do this BEFORE drilling the hole
    result = result.edges().fillet(r)
    
    # 3. Add the countersunk hole
    # Position: X=0, Z = top 1/3 of the back_h
    hole_z = back_h - (back_h / 6.0)
    
    # Select the "inside" face of the back plate.
    # This face is at Y=t, and it faces the +Y direction.
    # We look for a face that is vertical (Normal is (0, 1, 0)) and is at Y=t.
    # We use a tolerance because of the fillets.
    target_face = result.faces("+Y").filter(lambda f: abs(f.Center().y - t) < r*2 and f.Center().z > t)
    
    # Drill the hole. 
    # Workplane center for a box at Y=0..t, Z=0..back_h is at Y=t/2, Z=back_h/2 (if Y is normal)
    # But since we selected the face at Y=t, the local origin is at the center of that face.
    # The face center is at X=0, Z=back_h/2 (approximately, minus the thickness of the base)
    
    # Actually, let's just use the back face and drill through.
    # Outer face is at Y=0, normal is (0, -1, 0).
    back_face = result.faces("-Y").filter(lambda f: abs(f.Center().y - 0) < r*2)
    
    # #8 wood screw: ~4.5mm shank, ~8.5mm head, 82 deg
    # We drill from the OUTSIDE in so the countersink is on the outside.
    # Wait, the user said "The countersink is on the wrong face" and then 
    # "I can manually print it myself from the model files but not if the model is wrong"
    # Usually, a C-bracket hanging a picture has the screw going through the back plate into the wall.
    # So the countersink should be on the INSIDE face so the screw head is flush with the bracket?
    # NO, the screw head should be flush with the BACK of the bracket if it's going into the wall?
    # Actually, if the bracket is between the wall and the picture, 
    # the screw goes through the bracket into the wall. The head should be flush with the INSIDE face
    # so the picture can sit flat against it.
    
    # User said: "The countersink is on the wrong face" previously when I put it on the outside.
    # So it should be on the INSIDE face (Y=t, facing +Y).
    
    result = (
        target_face.workplane()
        .center(0, hole_z - (back_h / 2.0))
        .cskHole(4.5, 8.5, 82)
    )
    
    return result
