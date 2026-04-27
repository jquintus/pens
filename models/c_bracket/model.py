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

    # --- Build parts (clear + explicit) ---
    back = cq.Workplane("XY").box(w, t, back_h, centered=(True, False, False))

    base = (
        cq.Workplane("XY")
        .center(0, t)
        .box(w, base_l - t, t, centered=(True, False, False))
    )

    lip = (
        cq.Workplane("XY")
        .workplane(offset=t)
        .center(0, base_l - t)
        .box(w, t, lip_h - t, centered=(True, False, False))
    )

    # Combine into single solid
    result = back.union(base).union(lip)

    # --- Fillets ---
    result = result.edges().fillet(r)

    # --- Hole (FIXED) ---
    hole_z = back_h * (5.0 / 6.0)

    result = (
        result
        .faces(">Y")  # inside face of back plate
        .workplane(centerOption="CenterOfMass")
        .center(0, hole_z)  # <-- FIX: no subtraction
        .cskHole(4.5, 8.5, 82)
    )

    return result