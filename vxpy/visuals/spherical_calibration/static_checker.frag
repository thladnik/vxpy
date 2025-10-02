
const float c_pi = 3.14159265359;

uniform float u_elevation_sp; // in deg
uniform float u_azimuth_sp; // in deg
uniform float u_elevation_phase; // in deg
uniform float u_azimuth_phase; // in deg
uniform float brightness; // Rel. from 0.0 to 1.0

varying float v_azimuth; // in rad
varying float v_elevation; // in rad
varying vec3 v_position;

void main() {

    float az_freq = 360.0 / u_azimuth_sp;
    float az_shift = 2.0 * c_pi * u_azimuth_phase / 360.0;
    float c1 = sin(az_freq * v_azimuth + az_shift);

    float el_freq = 360.0 / u_elevation_sp;
    float el_shift = 2.0 * c_pi * u_elevation_phase / 360.0;
    float c2 = sin(el_freq * v_elevation + el_shift);

    // Thresholding
    float c = step(c1 * c2, 0.0);
    c = c * brightness;

    // Final color
    gl_FragColor = vec4(c, c, c, 1.0);

}