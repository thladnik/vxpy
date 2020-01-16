uniform mat2 u_mapcalib_aspectscale;
uniform vec2 u_mapcalib_scale;
uniform mat4 u_mapcalib_transform3d;
uniform mat4 u_mapcalib_rotate3d;
uniform vec2 u_mapcalib_translate2d;
uniform mat2 u_mapcalib_rotate2d;

uniform float u_stime;
uniform float u_ptime;

attribute vec3 a_position;   // Vertex position
attribute vec2 a_texcoord;   // texture coordinate
varying   vec2 v_texcoord;  // output

void main() {
    // Final position
    vec4 pos  = u_mapcalib_transform3d * u_mapcalib_rotate3d * vec4(a_position, 1.0);
    gl_Position = vec4(((u_mapcalib_rotate2d * pos.xy) * u_mapcalib_scale + u_mapcalib_translate2d * pos.w) * u_mapcalib_aspectscale, pos.z, pos.w);

    // Assign varying variables
    v_texcoord  = a_texcoord;
}