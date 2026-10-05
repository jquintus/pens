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
    // Sample the analytic rounded extrusion, sharing vertices between faces.
    arc_segments=24;
    edge_segments=12;
    side_angles=[for(i=[0:edge_segments]) 90*i/edge_segments];
    xs=concat([for(a=side_angles) -w/2+r*(1-cos(a))],
              [for(i=[edge_segments:-1:0]) w/2-r*(1-cos(side_angles[i]))]);
    deltas=concat([for(a=side_angles) r*(1-sin(a))],
                  [for(i=[edge_segments:-1:0]) r*(1-sin(side_angles[i]))]);
    function is_inside(c)=c==4 || c==5;
    function is_end(k)=k==0 || k==len(xs)-1;
    function corner_count(k,c)=is_end(k) && !is_inside(c) ? 1 : arc_segments+1;
    function ring_count(k)=is_end(k) ? 6+2*(arc_segments+1) : 8*(arc_segments+1);
    function prefix(values,n)=n==0 ? 0 : sum_values(values,n-1);
    function sum_values(values,n)=n<0 ? 0 : values[n]+sum_values(values,n-1);
    function vertex_index(k,j)=
        let(c=floor(j/(arc_segments+1)),a=j%(arc_segments+1))
        prefix([for(q=[0:len(xs)-1]) ring_count(q)],k)
        +prefix([for(q=[0:7]) corner_count(k,q)],c)
        +(is_end(k) && !is_inside(c) ? 0 : a);
    function profile(delta,k)=
        let(p=[[delta,delta],[length-delta,delta],[length-delta,lip_h-delta],
               [length-t+delta,lip_h-delta],[length-t+delta,t-delta],
               [t-delta,t-delta],[t-delta,back_h-delta],[delta,back_h-delta]])
        [for(c=[0:7]) each is_end(k) && !is_inside(c) ? [p[c]] :
            _cb_corner(p[(c+7)%8],p[c],p[(c+1)%8],
                       is_inside(c) ? r+delta : r-delta,arc_segments)];
    points=[for(k=[0:len(xs)-1]) for(p=profile(deltas[k],k)) [xs[k],p.x,p.y]];
    function valid_triangle(a,b,c)=a!=b && b!=c && c!=a;
    ring_steps=8*(arc_segments+1);
    side_faces=[for(k=[0:len(xs)-2]) for(j=[0:ring_steps-1])
        let(a=vertex_index(k,j),b=vertex_index(k+1,j),
            c=vertex_index(k+1,(j+1)%ring_steps),d=vertex_index(k,(j+1)%ring_steps))
        each concat(valid_triangle(a,b,c) ? [[a,b,c]] : [],
                    valid_triangle(a,c,d) ? [[a,c,d]] : [])];
    left_cap=[for(j=[0:ring_count(0)-1]) j];
    right_offset=prefix([for(k=[0:len(xs)-1]) ring_count(k)],len(xs)-1);
    right_cap=[for(j=[ring_count(len(xs)-1)-1:-1:0]) right_offset+j];
    // Inside-face center is halfway between the base top and back top.
    // CadQuery then shifts the workplane upward by back_h * 0.5 * 0.3.
    hole_z=(t+back_h)/2+back_h*0.15;
    difference() {
        polyhedron(points=points,faces=concat(side_faces,[left_cap,right_cap]),convexity=10);
        translate([0,t+0.01,hole_z]) rotate([90,0,0]) {
            cylinder(d=4.3,h=t+0.02,$fn=96);
            cylinder(d1=8.6,d2=4.3,h=(8.6-4.3)/2/tan(82/2),$fn=96);
        }
    }
}
