attribute vec3 a_position;

varying vec2 v_position;
varying vec2 v_nposition;

void main() {
    gl_Position = gl_position(a_position);
    v_position = real_position(a_position);
    v_nposition = norm_position(a_position);
}
