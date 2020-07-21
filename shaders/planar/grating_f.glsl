// planar/f_grating.glsl

uniform float u_stime;
uniform float u_spat_period;
uniform float u_lin_velocity;
uniform int u_shape;
uniform int u_direction;

const float c_pi = 3.14159265359;

varying vec2 v_position;

void main() {

    // Color
    float c;

    // Sinewave
    if (u_direction == 1) {
        c = sin((u_spat_period * v_position.y + u_stime * u_lin_velocity) * 2.0 * c_pi);
    } else {
        c = sin((u_spat_period * v_position.x + u_stime * u_lin_velocity) * 2.0 * c_pi);
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
