import cadquery as cq

def build(model_config):
    # Units in inches from config, converted to mm
    inch = 25.4
    w = model_config.get("width_in", 0.5) * inch
    t = model_config.get("thickness_in", 0.125) * inch
    base_l = model_config.get("length_in", 1.0) * inch
    back_h = model_config.get("back_height_in", 2.0) * inch
    lip_h = model_config.get("lip_height_in", 0.5) * inch

    # Profile in YZ plane: Back vertical, Base horizontal, Lip vertical
    # We use a polyline and offset it to create thickness.
    # Kind='intersection' ensures sharp corners.
    path = [
        (0, back_h),
        (0, 0),
        (base_l, 0),
        (base_l, lip_h)
    ]
    
    # Create the base shape
    result = (
        cq.Workplane("YZ")
        .polyline(path)
        .offset2D(t, kind="intersection")
        .extrude(w)
    )
    
    # Center the hole in the top 1/3 of the back plate.
    # The polyline's vertical segment is at Y=0.
    # After extrusion and centering, we need to locate the correct face.
    # #8 wood screw: ~4.2mm shank, ~8.2mm head diameter.
    
    # We target the top 1/3 of the back plate
    hole_z = back_h * (5/6) # Center of the top 1/3 area (2/3 to 1.0)
    
    # Drill into the back face
    result = (
        result.faces("<Y")
        .workplane()
        .center(0, hole_z - back_h/2)
        .cskHole(4.5, 8.5, 82)
    )
    
    return result
