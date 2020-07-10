attribute vec3 a_position;

uniform float u_mapcalib_xscale;
uniform float u_mapcalib_yscale;

varying vec3 v_position;

void main() {
    gl_Position = vec4(a_position.x * u_mapcalib_xscale, a_position.y * u_mapcalib_yscale, a_position.z, 1.0);
    v_position = a_position;
}
