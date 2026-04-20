import cadquery as cq


def _require_positive(name, value):
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")


def build(config):
    """Build a vertical cylinder with a tapered top and stepped center bore."""

    dimensions = config.get("dimensions") or config.get("metrics")
    if not isinstance(dimensions, dict):
        raise KeyError("missing required key 'dimensions'")

    cylinder_height = float(dimensions["cylinder_height"])
    cylinder_diameter = float(dimensions["cylinder_diameter"])
    frustum_height = float(dimensions["frustum_height"])
    frustum_top_diameter = float(dimensions["frustum_top_diameter"])
    frustum_bottom_diameter = float(dimensions["frustum_bottom_diameter"])
    top_hole_diameter = float(dimensions["top_hole_diameter"])
    bottom_hole_diameter = float(dimensions["bottom_hole_diameter"])
    top_hole_height = float(dimensions["top_hole_height"])

    _require_positive("cylinder_height", cylinder_height)
    _require_positive("cylinder_diameter", cylinder_diameter)
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

    result = cq.Workplane("XY").circle(cylinder_diameter / 2).extrude(cylinder_height)

    if frustum_height > 0:
        frustum = (
            cq.Workplane("XY")
            .workplane(offset=cylinder_height)
            .circle(frustum_bottom_diameter / 2)
            .workplane(offset=frustum_height)
            .circle(frustum_top_diameter / 2)
            .loft(combine=True)
        )
        result = result.union(frustum)

    bottom_hole_height = total_height - top_hole_height
    cut_solid = None

    if bottom_hole_height > 0:
        cut_solid = cq.Workplane("XY").circle(bottom_hole_diameter / 2).extrude(bottom_hole_height)

    if top_hole_height > 0:
        top_cut = (
            cq.Workplane("XY")
            .workplane(offset=bottom_hole_height)
            .circle(top_hole_diameter / 2)
            .extrude(top_hole_height)
        )
        cut_solid = top_cut if cut_solid is None else cut_solid.union(top_cut)

    if cut_solid is not None:
        result = result.cut(cut_solid)

    return result
