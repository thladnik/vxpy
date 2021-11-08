// Input
attribute vec3 a_position;
attribute float a_azimuth;
attribute float a_elevation;

// Output
varying float v_azimuth;
varying float v_elevation;
varying vec3 v_position;

// Main
void main() {
    gl_Position = transform_position(a_position);
    v_azimuth = a_azimuth;
    v_elevation = a_elevation;
    v_position = a_position;
}
