import cadquery as cq


def _require_positive(name, value):
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")


def build(config):
    """Build a vertical cylinder with a tapered top and stepped center bore."""

    nose_cone = config.get("nose_cone")
    if not isinstance(nose_cone, dict):
        raise KeyError("missing required key 'nose_cone'")

    cylinder_height = float(nose_cone["cylinder_height"])
    cylinder_outside_diameter = float(nose_cone["cylinder_outside_diameter"])
    frustum_height = float(nose_cone["frustum_height"])
    frustum_top_diameter = float(nose_cone["frustum_top_diameter"])
    frustum_bottom_diameter = float(nose_cone["frustum_bottom_diameter"])
    top_hole_diameter = float(nose_cone["top_hole_diameter"])
    bottom_hole_diameter = float(nose_cone["bottom_hole_diameter"])
    top_hole_height = float(nose_cone["top_hole_height"])

    _require_positive("cylinder_height", cylinder_height)
    _require_positive("cylinder_outside_diameter", cylinder_outside_diameter)
    if frustum_height < 0:
        raise ValueError(f"frustum_height must be >= 0, got {frustum_height}")
    _require_positive("frustum_top_diameter", frustum_top_diameter)
    _require_positive("frustum_bottom_diameter", frustum_bottom_diameter)
    _require_positive("top_hole_diameter", top_hole_diameter)
    _require_positive("bottom_hole_diameter", bottom_hole_diameter)

    total_height = cylinder_height + frustum_height
    if top_hole_height < 0 or top_hole_height > total_height:
        raise ValueError(
            f"top_hole_height must be between 0 and total height ({total_height}), got {top_hole_height}"
        )

    bottom_hole_height = total_height - top_hole_height
    end_cap_thickness = 2
    fillet_radius = 1

    def origin ():
        return cq.Workplane("XY")

    nose_cone = (
        origin()
        .circle(cylinder_outside_diameter / 2)
        .extrude(cylinder_height)
        .faces(">Z")
        .workplane()
        .circle(frustum_bottom_diameter / 2)
        .workplane(offset=frustum_height)
        .circle(frustum_top_diameter / 2)
        .loft(combine=True)
    )

    cut_solid = (
        origin()
        .circle(bottom_hole_diameter/ 2)
        .extrude(bottom_hole_height)
        .faces(">Z")
        .circle(top_hole_diameter / 2)
        .extrude(top_hole_height)
        )

    nose_cone = (
        nose_cone
        .edges(">Z or <Z")
        .fillet(fillet_radius)
    )

    nose_cone = nose_cone.cut(cut_solid).translate((20, 0, 0))


    end_cap = (
        origin()
        .circle(frustum_bottom_diameter / 2)
        .extrude(end_cap_thickness)
        .faces(">Z")
        .circle(cylinder_outside_diameter / 2)
        .extrude(cylinder_height)
    )

    end_cap = (
        end_cap
        .edges(">Z or <Z")
        .fillet(fillet_radius)
    )

    result = nose_cone.union(end_cap)

    return result
