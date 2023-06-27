
const float c_pi = 3.14159265359;

uniform float u_elevation_sp; // in 1/deg
uniform float u_azimuth_sp; // in 1/deg
uniform float u_line_threshold; // normalized

varying float v_azimuth; // in rad
varying float v_elevation; // in rad

void main() {

    float c1 = cos(1.0 / u_azimuth_sp * 360.0 * v_azimuth);
    float c2 = cos(1.0 / u_elevation_sp * 360.0 * v_elevation);

    float c;
    if (c1 > u_line_threshold || c2 > u_line_threshold) {
        c = 1.0;
    } else {
        c = 0.0;
    }

    // Final color
    // White
     gl_FragColor = vec4(c, c, c, 1.0);
    // Az/el colored
//    gl_FragColor = vec4(c * v_azimuth / (2.0 * c_pi), 0.0, c * (c_pi / 2.0 + v_elevation) / c_pi, 1.0);
}