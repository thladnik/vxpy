

// f_grating.shader

uniform int u_shape;
uniform int u_stripes_num;
uniform float u_velocity;
uniform int u_orientation;

void main()
{
    //<viewport.clipping>;

    // Checkerboard
    float c = 1.0;
    if (u_orientation == 1) {
        c = sin(float(u_stripes_num) * v_sph_pos.x + u_time * u_velocity);
    } else {
        c = sin(float(u_stripes_num) * v_sph_pos.y + u_time * u_velocity);
    }

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