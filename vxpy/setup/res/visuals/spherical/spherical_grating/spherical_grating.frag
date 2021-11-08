// Constants
const float PI = 3.14159265359;

// Uniform input
uniform int p_shape;
uniform int p_type;
uniform float u_spat_period;
uniform float u_ang_velocity;
uniform float u_time;

// Input
varying float v_azimuth;
varying float v_elevation;

// Main
void main() {

    // Set position to be used
    float p;
    if (p_type == 1) {
        p = v_elevation;
    } else {
        p = v_azimuth;
    }

    // Calculate brightness using position
    float c = sin(1.0/(u_spat_period/360.0) * p + u_time * u_ang_velocity/u_spat_period *  2.0 * PI);

    // If waveform is rectangular (1): apply threshold to brightness
    if (p_shape == 1) {
        c = step(c, 0.);
    }

    // Set final color
    gl_FragColor = vec4(c, c, c, 1.0);

}