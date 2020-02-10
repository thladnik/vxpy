// plane/f_checkerboard.glsl

const float c_pi = 3.14159265359;

varying vec3 v_position;

void main() {
    // Construct checkerboard
    float c = sin(c_pi * float(4) * v_position.x) * sin(c_pi * float(4) * v_position.y);

    // Thresholding
    if (c > 0) {
       c = 1.0;
    } else {
         c = 0.0;
    }

    // Final color
    gl_FragColor = vec4(c, c, c, 1.0);;
}
