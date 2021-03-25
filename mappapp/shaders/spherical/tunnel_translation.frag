// spherical/tunnel_translation.frag

const float c_pi = 3.14159265359;

uniform float u_time;
uniform int u_waveform;
uniform float u_spat_period;
uniform float u_lin_velocity;

varying vec3 v_position;

void main() {

    // Calculate distance on tunnel wall
    float hzy =  sqrt(pow(v_position.z, 2) + pow(v_position.y, 2));
    float el = atan(v_position.x, hzy);
    float d = tan(el);

    // Calculate luminance for grating pattern
    float x = 1.0 / u_spat_period * d + u_time * u_lin_velocity / u_spat_period *  2.0 * c_pi;
    float c = (1.0 + sin(x)) / 2.0;

    // If waveform is rectangular: threshold sine wave
    if (u_waveform == 1) {
        c = step(0.5, c);
    }

    // Fade to distance
    float fade_fraction = 0.20;
    if(abs(v_position.x) > 1.0 - fade_fraction) { c *= (1.0 - abs(v_position.x)) / fade_fraction; }

    // Blank high SF regions at front/back
    float blank_fraction = 0.02;
    if(abs(v_position.x) > 1.0 - blank_fraction) { c = 0.0; }

    // Final fragment color
    gl_FragColor = vec4(c, c, c, 1.0);

}




