// f_glider.glsl

const float c_pi = 3.14;

uniform float u_stime;
uniform sampler2D u_texture;

varying float v_azimuth;
varying float v_elevation;

void main() {
    float c = (v_azimuth) / (2.0 * c_pi);
    gl_FragColor = texture2D(u_texture, vec2(c, 0.0));
}