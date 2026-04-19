from cad.engine import build_pen


def build(config):
    geometry = config["geometry"]
    return build_pen(geometry)