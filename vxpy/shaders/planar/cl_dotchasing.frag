uniform float u_sf_vertical;
uniform float u_sf_horizontal;
uniform bool u_checker_pattern;

uniform float u_stime;
uniform vec2 u_pos;
varying vec2 v_nposition;

# define PI 3.1415926
void main() {
    vec2 st = v_nposition;
//    st -= 0.5;
    float g_circ_mask = smoothstep(.02+sin(u_stime*2.)/50.,.025+sin(u_stime*2.)/50.,distance(st,u_pos));
    gl_FragColor = vec4(vec3(g_circ_mask)-.3, 1.);
}