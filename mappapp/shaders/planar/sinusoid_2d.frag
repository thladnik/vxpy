// planar/checkerboard.frag

const float c_pi = 3.14159265359;

uniform float u_sf_vertical;
uniform float u_sf_horizontal;
uniform bool u_checker_pattern;

varying vec2 v_position;  // in mm

void main() {
    // Construct checkerboard

    float horizontal = sin(u_sf_horizontal * 2.0 * c_pi * v_position.x);
    float vertical = sin(u_sf_vertical * 2.0 * c_pi * v_position.y);

    float c;
    if(u_checker_pattern) {
        c = step(0.0, horizontal * vertical);
    } else {
        c = (1.0 + horizontal) / 2.0 * (1.0 + vertical) / 2.0;
    }

    // Final color
    gl_FragColor = vec4(c, c, c, 1.0);;
}
