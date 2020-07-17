attribute vec3 a_position;

uniform float u_mapcalib_xscale;
uniform float u_mapcalib_yscale;
uniform float u_small_side_size;
uniform float u_glob_x_position;
uniform float u_glob_y_position;

varying vec2 v_position; // in mm

void main() {
    gl_Position = vec4(a_position.x * u_mapcalib_xscale + u_glob_x_position, a_position.y * u_mapcalib_yscale + u_glob_y_position, a_position.z, 1.0);
    v_position = vec2((1.0 + a_position.x) / 2.0 * u_small_side_size, (1 + a_position.y) / 2.0 * u_small_side_size);
    //v_position = a_position;
}
