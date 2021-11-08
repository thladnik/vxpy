// Input
attribute vec3 a_position;

// Output
varying vec2 v_position;
varying vec2 v_nposition;

// Main
void main() {
    gl_Position = transform_position(a_position);
    v_position = real_position(a_position);
    v_nposition = norm_position(a_position);
}
