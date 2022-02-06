attribute vec3 a_position;

void main() {
    gl_Position = transform_position(a_position);
}
