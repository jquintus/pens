import os
import yaml
import sys

sys.path.append(os.path.abspath("."))

import importlib.util
import cadquery as cq

PROJECTS_DIR = "projects"
OUTPUT_DIR = "outputs"


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def load_model(module_path):
    spec = importlib.util.spec_from_file_location("model", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_project(project_path):
    config_path = os.path.join(project_path, "config.yml")
    model_path = os.path.join(project_path, "model.py")

    config = load_config(config_path)
    model_module = load_model(model_path)

    result = model_module.build(config)

    name = config["output"]["name"]
    output_file = os.path.join(OUTPUT_DIR, f"{name}.step")

    cq.exporters.export(result, output_file)
    print(f"Built: {output_file}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for project in os.listdir(PROJECTS_DIR):
        project_path = os.path.join(PROJECTS_DIR, project)

        if os.path.isdir(project_path):
            build_project(project_path)


if __name__ == "__main__":
    main()