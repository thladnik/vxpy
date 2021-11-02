uniform float u_sf_vertical;
uniform float u_sf_horizontal;
uniform bool u_checker_pattern;

uniform float u_stime;
uniform float u_spfreq;
uniform float u_speed;
uniform float u_dir;

varying vec2 v_nposition;
# define PI 3.1415926
void main() {
    vec2 st = v_nposition;
    st -= 0.5;
    float spatial_period = 41.632;
    float g_base = st.x*cos(u_dir)*u_spfreq*PI+st.y*sin(u_dir)*u_spfreq*PI;
    float g_circ_mask = step(distance(st,vec2(0.)),0.5);
    gl_FragColor = vec4(vec3(sin(g_base+u_speed*u_stime)*g_circ_mask),1.);
}