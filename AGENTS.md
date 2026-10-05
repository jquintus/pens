# Pens project preferences

- Keep both galleries driven by the same YAML configurations and Pages CMS fields. Do not duplicate configuration collections per CAD backend.
- The original CadQuery gallery supplies STEP exports. The parallel OpenSCAD gallery supplies self-contained SCAD and printable STL files.
- Rounded edges are essential. Construct rounded profiles explicitly instead of relying on fragile edge/face selection.
- Verify ports against the CadQuery originals: dimensions, bores, component counts, and rounded volume. Keep tessellation tolerances documented.
- Josh uses a Bambu Lab P1S with AMS and currently a 0.6 mm nozzle; a 0.4 mm nozzle is also available. Prefer PLA and avoid unnecessary nozzle swaps.
- Slice STL files with the actual installed nozzle and filament settings. Do not present fabricated printer headers or estimates as real slicer output.
- Keep the OpenSCAD CLI compatible with the Linux version installed in CI. Downloads must work without separately installing CAD libraries.
- New Git branches must start with jq/.
- Use current GitHub Action majors with Node 24; verify their action.yml runtimes before changing uses entries.
- Keep chat brief and checklists especially terse.
