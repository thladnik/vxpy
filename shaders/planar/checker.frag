// planar/checkerboard.frag

const float c_pi = 3.14159265359;

uniform float u_rows;
uniform float u_cols;

varying vec2 v_position;  // in mm

void main() {
    // Construct checkerboard
    float c = sin(u_cols * c_pi * v_position.x)
                * sin(u_rows * c_pi * v_position.y);

    // Thresholding
    if (c > 0) {
       c = 1.0;
    } else {
         c = 0.0;
    }

    // Final color
    gl_FragColor = vec4(c, c, c, 1.0);;
}
