// v_tex.glsl

attribute vec3 a_position;
attribute vec2 a_texcoord;

varying vec2 v_texcoord;

void main() {
    gl_Position = gl_position(a_position);

    // Assign varying variables
    v_texcoord  = a_texcoord;
}