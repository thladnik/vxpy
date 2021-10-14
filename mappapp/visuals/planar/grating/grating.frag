// planar/grating.frag

uniform float u_spat_period;
uniform float u_lin_velocity;
uniform int u_shape;
uniform int u_direction;
uniform float u_time;

const float c_pi = 3.14159265359;

varying vec2 v_position;

void main() {

    // Color
    float c;

    // Sinewave
    if (u_direction == 1) {
        c = sin((v_position.y + u_time * u_lin_velocity)/u_spat_period * 2.0 * c_pi);
    } else {
        c = sin((v_position.x + u_time * u_lin_velocity)/u_spat_period * 2.0 * c_pi);
    }

    // If shape is rectangular: threshold sinewave
    if (u_shape == 1) {
        if (c > 0) {
           c = 1.0;
        } else {
             c = 0.0;
        }
    }

    // Final color
    gl_FragColor = vec4(c, c, c, 1.0);
}
