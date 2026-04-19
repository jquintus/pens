import cadquery as cq


def build_pen(geometry):
    outer = geometry["outer_diameter"] / 2
    inner = geometry["inner_diameter"] / 2
    length = geometry["length"]
    fillet = geometry.get("fillet", 0)

    result = (
        cq.Workplane("XY")
        .circle(outer)
        .circle(inner)
        .extrude(length)
    )

    if fillet > 0:
        result = result.edges("|Z").fillet(fillet)

    return result