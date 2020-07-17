// planar/f_grating.glsl

uniform float u_stime;
uniform int u_shape;
uniform int u_stripes_num;
uniform float u_velocity;
uniform int u_orientation;

const float c_pi = 3.14159265359;

varying vec2 v_position;

void main() {

    // Color
    float c;

    // Sinewave
    if (u_orientation == 1) {
        c = sin(float(u_stripes_num) * v_position.x + u_stime * u_velocity);
    } else {
        c = sin(float(u_stripes_num) * v_position.x + u_stime * u_velocity);
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
