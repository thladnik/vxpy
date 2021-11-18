
attribute vec3 a_position;
attribute float a_azimuth;
attribute float a_elevation;

varying float v_azimuth;
varying float v_elevation;
varying vec3 v_position;

void main() {

    gl_Position = transform_position(a_position);

    v_azimuth = a_azimuth;
    v_elevation = a_elevation;
    v_position = a_position; // a_position declared in mapped_position() include
}
