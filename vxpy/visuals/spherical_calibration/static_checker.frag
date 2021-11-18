
const float c_pi = 3.14159265359;

uniform float u_elevation_sp; // in 1/deg
uniform float u_azimuth_sp; // in 1/deg

varying float v_azimuth; // in rad
varying float v_elevation; // in rad

void main() {

    float c1 = sin(1.0 / u_azimuth_sp * 360.0 * v_azimuth);
    float c2 = sin(1.0 / u_elevation_sp * 360.0 * v_elevation);

    // Thresholding
    float c = step(c1 * c2, 0.0);

    // Final color
    gl_FragColor = vec4(c, c, c, 1.0);

}