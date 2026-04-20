import cadquery as cq


def build(config):
    """Build geometry from a loaded configuration dict.

    Required:
      config["metrics"] — numeric dimensions used by the model (see example YAMLs).
    """
    metrics = config["metrics"]
    outer = metrics["outer_diameter"] / 2
    inner = metrics["inner_diameter"] / 2
    length = metrics["length"]

    result = (
        cq.Workplane("XY")
        .circle(outer)
        .circle(inner)
        .extrude(length)
    )

    return result
