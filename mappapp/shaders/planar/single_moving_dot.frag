// planar/grating.frag

uniform float u_dot_lateral_offset;
uniform float u_dot_ang_dia;
uniform float u_dot_ang_velocity;
//uniform float u_start_delay;
uniform float u_time;
uniform float u_vertical_offset;
uniform float u_mapcalib_yextent;
uniform float u_small_side_size;

const float c_pi = 3.14159265359;

varying vec2 v_position;
varying vec2 v_nposition;

void main() {

    gl_FragColor = vec4(1.0);

    float dist_to_origin = length(vec2(u_dot_lateral_offset, u_vertical_offset));
    float dot_lin_vel = 2.0 * dist_to_origin * c_pi * u_dot_ang_velocity / 360.0; //u_dot_lateral_offset * tan(u_dot_ang_velocity/ 360.0 * 2 * c_pi);
    float dot_lin_dia = 2.0 * dist_to_origin * tan(u_dot_ang_dia / 2.0 / 360.0 * 2 * c_pi);

    vec2 dot_center = vec2(u_dot_lateral_offset,
                            u_time * dot_lin_vel - u_mapcalib_yextent * u_small_side_size / 2.0 - dot_lin_dia / 2.0);

    float dist_to_dotcenter = distance(dot_center, v_position.xy);
    float ndist = 2.0 * dist_to_dotcenter / dot_lin_dia;

    // Draw dot color
    if(ndist < 0.999999) {
        gl_FragColor = vec4(vec3(0.0), 1.0);
        //gl_FragColor = vec4(vec3(ndist), 1.0);
    }

    // Draw center indicator
    float dp = 0.005;
    if((v_nposition.x < 0.5+dp && v_nposition.x > 0.5-dp) && (v_nposition.y < 0.5+dp && v_nposition.y > 0.5-dp)) {
        gl_FragColor = vec4(vec3(1.0) - step(0.5, gl_FragColor.xyz), 1.0);
    }

}
