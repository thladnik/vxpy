attribute vec3 a_position;

varying vec2 v_position; // in mm

void main() {
    gl_Position = transform_position(a_position);
    v_position = real_position(a_position);
}
