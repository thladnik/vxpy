// checkerboard.frag

const float c_pi = 3.14159265359;

uniform float u_elevation_sf; // in 1/deg
uniform float u_azimuth_sf; // in 1/deg

varying float v_azimuth; // in rad
varying float v_elevation; // in rad

void main()
{

    // Construct checkerboard
    float c = sin(u_azimuth_sf * 360.0 * v_azimuth) * sin(u_elevation_sf * 360.0 * v_elevation);

    // Thresholding
    c = step(c, 0.0);
//    if (c > 0) {
//       c = 1.0;
//    } else {
//         c = 0.0;
//    }

    // Final color
    gl_FragColor = vec4(c, c, c, 1.0);

}