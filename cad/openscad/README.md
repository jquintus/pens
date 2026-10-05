# OpenSCAD models

`pen_parts.scad` implements the original nose cone and end cap. The C-bracket
module lives in [`models/c_bracket/model.scad`](../../models/c_bracket/model.scad).
The build script combines each module with editable parameters from the existing
Pages CMS YAML into a self-contained `.scad` download, then renders its STL.
There are no external OpenSCAD library dependencies.

## Rounding

The pen keeps the original dimensions, stepped bore, 20 mm spacing, and 2 mm
end-cap flange. Its 1 mm top and bottom fillets are circular arcs in a revolved
profile. Cylinder-to-cone and flange shoulders retain their original sharp edges.
Changing dimensions requires no edge or face selectors.

The bracket retains the 1/32-inch (0.79375 mm) fillets on every edge. Analytic
rounded cross sections form a closed polyhedron with shared vertex indices. The
side profiles shrink through a circular arc to round the extrusion edges. This
avoids the tiny overlapping facets produced by Minkowski sums in older CGAL
exports. The original #8 countersink has a 4.3 mm bore, 8.6 mm mouth, and 82°
included angle. Its center is at `z = (thickness + back_height)/2 +
back_height*0.15`, matching the original CadQuery inside-face workplane.

## Verification

All nine pen configurations and the bracket were rendered and compared with
CadQuery 2.8.0. Every OpenSCAD STL is watertight; each pen export contains two
separate parts and the bracket contains one. Bounding boxes match the CadQuery
dimensions to mesh export precision.
Volume differences are below 0.045% for the pens and 0.001% for the bracket.
These comparisons check dimensions, volume, and topology rather than proving
point-by-point equivalence of every surface.

OpenSCAD approximates curved surfaces with mesh facets. Pen circumferences use
128 segments and fillet profiles use 24 segments per arc. The bracket uses 24
samples per profile corner and 12 per side rounding arc;
increasing those values improves mesh accuracy but increases rendering time.
The bracket rendered successfully with both Manifold and the older CGAL backend.
The CGAL STL also remains watertight when exported at six significant digits,
matching older ASCII STL exporters, and when reimported as binary STL. Neither
path requires mesh repair. Local CGAL rendering took about two seconds.
