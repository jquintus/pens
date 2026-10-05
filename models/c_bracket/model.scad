// C-bracket: dimensions in inches, with the original 1/32-inch edge fillets.
// No face selectors: the countersink position follows the original inside face.
function _cb_unit(v)=v/norm(v);
function _cb_rotate(v,a)=[v.x*cos(a)-v.y*sin(a),v.x*sin(a)+v.y*cos(a)];
function _cb_corner(previous,corner,next,radius,segments=48)=
    let(a=_cb_unit(corner-previous),b=_cb_unit(next-corner),
        turn=atan2(a.x*b.y-a.y*b.x,a*b),
        entry=corner-a*radius*tan(abs(turn)/2),
        center=entry+[-a.y,a.x]*radius*sign(turn))
    [for(i=[0:segments]) center+_cb_rotate(entry-center,turn*i/segments)];
module c_bracket(width_in=0.5, thickness_in=0.125, length_in=1,
                 back_height_in=2, lip_height_in=0.5) {
    inch=25.4;
    w=width_in*inch;
    t=thickness_in*inch;
    length=length_in*inch;
    back_h=back_height_in*inch;
    lip_h=lip_height_in*inch;
    r=inch/32;
    assert(w>2*r && t>2*r && length>2*t+4*r && back_h>t+4*r && lip_h>t+4*r,
           "Bracket dimensions are too small for the original edge fillets");
    // An inset core has sharp outside corners and radius-2r inside corners.
    // A spherical Minkowski sum gives radius-r fillets on every final edge.
    // This construction also rounds the edges along the extrusion direction.
    core=[[r,r],[length-r,r],[length-r,lip_h-r],
          [length-t+r,lip_h-r],[length-t+r,t-r],
          [t-r,t-r],[t-r,back_h-r],[r,back_h-r]];
    core_profile=[for(i=[0:len(core)-1]) each (i==4 || i==5)
        ? _cb_corner(core[(i+len(core)-1)%len(core)],core[i],
                     core[(i+1)%len(core)],2*r)
        : [core[i]]];
    // Inside-face center is halfway between the base top and back top.
    // CadQuery then shifts the workplane upward by back_h * 0.5 * 0.3.
    hole_z=(t+back_h)/2+back_h*0.15;
    difference() {
        minkowski() {
            translate([-w/2+r,0,0])
                multmatrix([[0,0,1,0],[1,0,0,0],[0,1,0,0],[0,0,0,1]])
                    linear_extrude(height=w-2*r,convexity=10)
                        polygon(core_profile);
            sphere(r=r,$fn=64);
        }
        translate([0,t+0.01,hole_z]) rotate([90,0,0]) {
            cylinder(d=4.3,h=t+0.02,$fn=96);
            cylinder(d1=8.6,d2=4.3,h=(8.6-4.3)/2/tan(82/2),$fn=96);
        }
    }
}
