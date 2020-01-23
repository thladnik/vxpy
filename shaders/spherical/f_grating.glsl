// f_grating.glsl

uniform float u_stime;
uniform int u_shape;
uniform int u_stripes_num;
uniform float u_velocity;
uniform int u_orientation;

varying float v_azimuth;
varying float v_elevation;

void main()
{

    // Checkerboard
    float c;
    //
    if (u_orientation == 1) {
        c = sin(float(u_stripes_num) * v_azimuth + u_stime * u_velocity);
    } else {
        c = sin(float(u_stripes_num) * v_elevation + u_stime * u_velocity);
    }

    // If shape is rectangular: threshold sine wave
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