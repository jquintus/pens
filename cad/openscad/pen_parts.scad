// Pen nose cone and end cap. All dimensions are millimeters.
// Rounded ends are drawn into the revolved profile; no edge selection is needed.
// This file is a module library. Call pen_parts(...) to create the printable pair.
function _pen_unit(v) = v / norm(v);
function _pen_cross(a, b) = a.x * b.y - a.y * b.x;
function _pen_rotate(v, a) = [v.x*cos(a)-v.y*sin(a), v.x*sin(a)+v.y*cos(a)];
function _pen_arc(previous, corner, next, radius, segments=24) =
    let(incoming=_pen_unit(corner-previous), outgoing=_pen_unit(next-corner),
        turn=atan2(_pen_cross(incoming,outgoing), incoming*outgoing),
        tangent=radius*tan(abs(turn)/2),
        entry=corner-incoming*tangent,
        center=entry+[-incoming.y,incoming.x]*radius*sign(turn),
        initial=entry-center)
    [for(i=[0:segments]) center+_pen_rotate(initial,turn*i/segments)];
function _pen_round_profile(points, corners, radius=1) =
    [for(i=[0:len(points)-1])
        each len(search(i,corners))>0
            ? _pen_arc(points[(i+len(points)-1)%len(points)],points[i],
                       points[(i+1)%len(points)],radius)
            : [points[i]]];
module pen_parts(cylinder_height=5.9, cylinder_outside_diameter=7.57,
                 frustum_height=11, frustum_top_diameter=5,
                 frustum_bottom_diameter=10.2, top_hole_diameter=3,
                 bottom_hole_diameter=4.9, top_hole_height=7) {
    assert(cylinder_height>0 && cylinder_outside_diameter>0,
           "Cylinder dimensions must be positive");
    assert(frustum_height>=0 && frustum_top_diameter>0 && frustum_bottom_diameter>0,
           "Frustum height must be nonnegative and diameters positive");
    assert(top_hole_diameter>0 && bottom_hole_diameter>0,
           "Bore diameters must be positive");
    total_height=cylinder_height+frustum_height;
    assert(top_hole_height>=0 && top_hole_height<=total_height,
           "Top bore height must lie within the part");
    rc=cylinder_outside_diameter/2;
    rb=frustum_bottom_diameter/2;
    rt=frustum_top_diameter/2;
    fillet_radius=1;
    // Preserve the original cylinder-to-cone shoulder; only end edges are filleted.
    nose_profile=frustum_height>0
        ? (rc==rb
            ? [[0,0],[rc,0],[rc,cylinder_height],[rt,total_height],[0,total_height]]
            : [[0,0],[rc,0],[rc,cylinder_height],[rb,cylinder_height],
               [rt,total_height],[0,total_height]])
        : [[0,0],[rc,0],[rc,total_height],[0,total_height]];
    translate([20,0,0]) difference() {
        rotate_extrude(convexity=10)
            polygon(_pen_round_profile(nose_profile,[1,len(nose_profile)-2],fillet_radius));
        bottom_hole_height=total_height-top_hole_height;
        if(bottom_hole_height>0)
            translate([0,0,-0.01])
                cylinder(d=bottom_hole_diameter,h=bottom_hole_height+0.01);
        if(top_hole_height>0)
            translate([0,0,bottom_hole_height])
                cylinder(d=top_hole_diameter,h=top_hole_height+0.01);
    }
    end_cap_height=2+cylinder_height;
    cap_profile=rc==rb
        ? [[0,0],[rb,0],[rc,end_cap_height],[0,end_cap_height]]
        : [[0,0],[rb,0],[rb,2],[rc,2],[rc,end_cap_height],[0,end_cap_height]];
    rotate_extrude(convexity=10)
        polygon(_pen_round_profile(cap_profile,[1,len(cap_profile)-2],fillet_radius));
}
