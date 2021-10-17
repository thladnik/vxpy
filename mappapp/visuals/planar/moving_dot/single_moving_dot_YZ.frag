// planar/grating.frag

uniform float u_x_offset;
uniform float u_y_offset;
uniform float u_dot_lateral_offset;
uniform float u_dot_ang_dia;
uniform float u_dot_ang_velocity;
uniform float u_time;
uniform float u_vertical_offset;
uniform float u_mapcalib_yextent;
uniform float u_mapcalib_small_side_size;

const float c_pi = 3.14159265359;
varying vec2 v_nposition;

void main() {
    vec2 st = v_nposition*2.-1.;//Normalize the screen coordinate to [-1, 1]
    float dot_speed = u_dot_lateral_offset*tan(u_dot_ang_velocity/(360./c_pi))*2; //convert the angular speed to relative speed(% percent of the screen per second)
    vec2 dot_center = vec2(u_dot_lateral_offset,u_time * dot_speed - 1.)-vec2(u_x_offset,u_y_offset); // calculate the dot center in related with the fish position
    float dot_diameter = 2.0 * u_dot_lateral_offset * tan(u_dot_ang_dia / 2.0 / 360.0 * 2 * c_pi);// calculate the dot diameter in relative screen unit
    float ndist = smoothstep(dot_diameter-.005,dot_diameter,distance(dot_center, st)); // a bit of anti-aliasing
    gl_FragColor = vec4(vec3(ndist), 1.0);
}
