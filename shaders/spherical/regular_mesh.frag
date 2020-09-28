// spherical/regular_mesh.frag

const float c_pi = 3.14159265359;

uniform int u_rows;
uniform int u_cols;

varying float v_azimuth;
varying float v_elevation;

void main() {

    // Construct checkerboard
    float c1 = cos(float(u_cols) * v_azimuth);
    float c2 = cos(float(u_rows) * v_elevation);

    // Thresholding
    float c;
    if (c1 > 0.95 || c2 > 0.95) {
        c = 1.0;
    } else {
        c = 0.0;
    }

    // Final color
    gl_FragColor = vec4(c, c, c, 1.0);
}