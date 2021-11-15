// Constants
const float PI = 3.14159265359;

// Uniform input
uniform int p_shape;
uniform int p_direction;
uniform float u_lin_velocity;
uniform float u_spat_period;
uniform float u_time;

// Input
varying vec2 v_position;

void main() {

    // Set position to be used
    float p;
    if (p_direction == 1) {
        p = v_position.y;
    } else {
        p = v_position.x;
    }

    // Calculate brightness using position
    float c = sin((p + u_time * u_lin_velocity)/u_spat_period * 2.0 * PI);

    // If shape is rectangular (1): apply threshold to brightness
    if(p_shape == 1) {
        c = step(c, 0.);
    }

    // Set final color
    gl_FragColor = vec4(c, c, c, 1.0);
}
