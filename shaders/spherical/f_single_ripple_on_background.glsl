// f_tex.glsl

const float c_pi = 3.14159265359;

//uniform sampler2D u_texture;
uniform float u_mod_sign;
uniform float u_mod_depth;
uniform int u_mod_shape;
uniform float u_mod_vel;
uniform float u_mod_time;
uniform float u_mod_start_time;
uniform float u_mod_width;
uniform float u_mod_min_elev;
uniform float u_mod_max_elev;
uniform int u_upper_field_flash;

varying float v_azimuth;
varying float v_elevation;
varying vec3 v_position;

float normDistr(float x, float mu, float sigma) {
    return 1 / sqrt(2 * c_pi * pow(sigma, 2)) * exp(-pow((x-mu), 2) / (2.0 * pow(sigma, 2)));
}

float rectDistr(float x, float center, float width) {
    if(abs(x) < width) {
        return 1.0;
    } else {
        return 0.0;
    }
}

void main()
{
    vec4 color;
    if(u_mod_sign < 0.0) {
        color = vec4(0.0, 0.0, 0.0, 0.0);
    } else {
        color = vec4(1.0, 1.0, 1.0, 0.0);
    }

    float pos = u_mod_vel * (u_mod_time - u_mod_start_time) / 20.0 - 1;


    if(u_mod_shape == 1) {
        color.w = u_mod_depth * normDistr(v_position.x-pos, 0.0, u_mod_width) / normDistr(0.0, 0.0, u_mod_width);
    } else {
        color.w = u_mod_depth * rectDistr(v_position.x-pos, 0.0, u_mod_width);
    }

    // Cut off at min/max elevation (and soften edges)
    if(v_elevation < u_mod_min_elev ) {
        color.w *= normDistr(v_elevation, u_mod_min_elev, 0.1) / normDistr(0.0, 0.0, 0.1);
    }
    if(v_elevation > u_mod_max_elev) {
        color.w *= normDistr(v_elevation, u_mod_max_elev, 0.1) / normDistr(0.0, 0.0, 0.1);
    }

    // Try: flash in upper field
    if(v_elevation > 0.0 && u_mod_sign > 0.0 && u_upper_field_flash == 1) {
        color.w += normDistr(pos, 0.0, 0.03) * normDistr(v_elevation, c_pi/2.0, 0.45);
    }

    //color.w = (v_elevation + c_pi/2) / c_pi ;

    gl_FragColor = color;
}