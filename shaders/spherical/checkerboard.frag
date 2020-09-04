// checkerboard.frag

const float c_pi = 3.14159265359;

uniform int u_rows;
uniform int u_cols;

varying float v_azimuth;
varying float v_elevation;

void main()
{

    // Construct checkerboard
    float c = sin(float(u_cols) / 2.0 * v_azimuth) * sin(float(u_rows) * v_elevation);

    // Thresholding
    if (c > 0) {
       c = 1.0;
    } else {
         c = 0.0;
    }

    // Final color
    gl_FragColor = vec4(c, c, c, 1.0);;

}