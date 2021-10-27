
uniform vec2 u_mov_direction;
uniform vec2 u_start_position;
uniform float u_dot_ang_dia;
uniform float u_dot_ang_velocity;
uniform float u_time;
uniform float u_vertical_offset;
uniform float u_mapcalib_yextent;
uniform float u_mapcalib_small_side_size;

const float c_pi = 3.14159265359;

varying vec2 v_position;
varying vec2 v_nposition;

void main() {

//    float dist_dot_to_origin = length(vec2(u_dot_lateral_offset, u_vertical_offset));
    vec2 perp_to_mov_dir = vec2(u_mov_direction.x, -u_mov_direction.y);
    float dist_dot_to_origin = abs(dot(u_start_position, perp_to_mov_dir));
    float dot_lin_vel = 2.0 * dist_dot_to_origin * c_pi * u_dot_ang_velocity / 360.0; //u_dot_lateral_offset * tan(u_dot_ang_velocity/ 360.0 * 2 * c_pi);

    vec2 dot_center = u_start_position + u_time * dot_lin_vel * u_mov_direction;
    //    vec2 dot_center = vec2(u_dot_lateral_offset,
    //                            u_time * dot_lin_vel - u_mapcalib_yextent * u_mapcalib_small_side_size / 2.0 - dot_lin_dia / 2.0);

    float dist_to_dotcenter = distance(dot_center, v_position.xy);
    float dot_lin_dia = 2.0 * dist_dot_to_origin * tan(u_dot_ang_dia / 2.0 / 360.0 * 2 * c_pi);
    float ndist = 2.0 * dist_to_dotcenter / dot_lin_dia;

    // Draw dot color
    if(ndist < 0.99) {
        gl_FragColor = vec4(1., 0., 0., 1.);
    } else {
        discard;
    }
}
