// spherical/grating.frag

const float c_pi = 3.14159265359;

uniform float u_stime;
uniform int u_waveform;
uniform float u_spat_period;
uniform float u_ang_velocity;
uniform int u_direction;

varying float v_azimuth;
varying float v_elevation;


void main()
{

    // Checkerboard
    float c;
    //
    if (u_direction == 1) {
        c = sin(1.0/(u_spat_period/360.0) * v_elevation + u_stime * u_ang_velocity/u_spat_period *  2.0 * c_pi);
    } else {
        c = sin(1.0/(u_spat_period/360.0) * v_azimuth + u_stime * u_ang_velocity/u_spat_period * 2.0 * c_pi);
    }

    // If shape is rectangular: threshold sine wave
    if (u_waveform == 1) {
        if (c > 0) {
           c = 1.0;
        } else {
             c = 0.0;
        }
    }

    // Final color
    gl_FragColor = vec4(c, c, c, 1.0);

}