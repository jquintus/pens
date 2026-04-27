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

    # --- Build geometry ---
    result = (
        cq.Workplane("XY")

        # Back plate (origin at bottom center)
        .box(w, t, back_h, centered=(True, False, False))

        # Base plate
        .faces(">Y").workplane()
        .transformed(offset=(0, (base_l - t)/2, -back_h/2 + t/2))
        .box(w, base_l - t, t, centered=(True, True, True))

        # Lip
        .faces(">Y").workplane()
        .transformed(offset=(0, t/2, lip_h/2))
        .box(w, t, lip_h, centered=(True, True, False))
    )

    # --- Fillet edges ---
    result = result.edges().fillet(r)

    # --- Hole placement ---
    hole_z = back_h * (5.0 / 6.0)  # top-ish, not blocked

    result = (
        result
        .faces(">Y")  # inside face of back plate
        .workplane(centerOption="CenterOfMass")
        .center(0, hole_z)
        .cskHole(4.5, 8.5, 82)
    )

    return result