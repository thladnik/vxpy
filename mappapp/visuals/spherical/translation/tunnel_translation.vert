
// spherical/tunnel_translation.vert

attribute vec3 a_position;

uniform mat4 u_rotate;

varying vec3 v_position;

void main() {

    gl_Position = gl_position(a_position);

    v_position = (u_rotate * vec4(a_position, 1.0)).xyz;
}





