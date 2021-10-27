varying vec2 v_nposition;
uniform float u_time;

float random( vec2 p ) {
    return fract(sin(dot(p,vec2(269.5,183.3)))*43758.5453)*2.-1.;
}
#define PI 3.1415926;

void main() {
    vec2 st = v_nposition;//gl_FragCoord.xy/u_resolution.xy;

    //st.x *= u_resolution.x/u_resolution.y;
    vec3 color = vec3(.0);
    float scale_fac = 3.;
    // Scale
    st -= .5;
    st *= scale_fac;
// Tile the space
vec2 i_st = floor(st);
float ds = 20./180.*PI;
for (int y= -1; y <= 1; y++) {
    for (int x= -1; x <= 1; x++) {
        vec2 point =  i_st + vec2(sin(u_time*random(i_st) + 100.*random(i_st)),cos(u_time*random(i_st) + 100.*random(i_st)))*.45+.5;
        float scale = 0.14*length(point)*tan(ds);
        color += step(scale, length(st-point));
    }
}
gl_FragColor = vec4(color,1.0);
}