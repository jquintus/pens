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
    back_plate = cq.Workplane("XY").box(w, t, back_h, centered=(True, False, False))
    base = (
        cq.Workplane("XY")
        .workplane(offset=0)
        .center(0, t)
        .box(w, base_l - t, t, centered=(True, False, False))
    )
    lip = (
        cq.Workplane("XY")
        .workplane(offset=t)
        .center(0, base_l - t)
        .box(w, t, lip_h - t, centered=(True, False, False))
    )
    
    result = back_plate.union(base).union(lip)
    
    # 2. Apply fillets to all edges EXCEPT the ones where the hole will go
    # Actually, it's safer to fillet everything and then drill the hole
    result = result.edges().fillet(r)
    
    # 3. Add the countersunk hole
    # We position it at the horizontal center (X=0) and top 1/3 of the back plate
    hole_z = back_h - (back_h / 6.0)
    
    # Select the inside face of the back plate
    # This face is at Y=t, facing +Y. We select by looking for the face closest to the origin in Y
    # but excluding the bottom/top faces.
    target_face = result.faces(">Y").filter(lambda f: abs(f.Center().y - t) < 0.1)
    
    # The workplane center for this face is at Z = back_h/2
    # We want to place the hole relative to that center
    result = (
        target_face.workplane()
        .center(0, hole_z - (back_h / 2.0))
        .cskHole(4.5, 8.5, 82)
    )
    
    return result
