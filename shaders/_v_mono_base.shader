// TO//DO: finish base shader writing, discuss with Tim: 2D shift and rotation.

const float pi = 3.14159265359;

// Transforms SOUTH WEST
uniform mat4   u_rot;
uniform mat4   u_trans;
uniform mat4   u_projection;
uniform float  u_radial_offset;
uniform float  u_tangent_offset;


// Vertex attributes
attribute vec3 a_pos;      // Cartesian vertex position

// Variables
varying vec4   v_pos;

vec4 channelTransform() {

    // Set position
    vec4 pos = vec4(a_pos, 1.0);
    pos =  u_projection * u_trans * u_rot * pos;
    pos.xy -= u_radial_offset * pos.w;
    pos.x += u_tangent_offset * pos.w;
    pos.y -= u_tangent_offset * pos.w;

    return pos;
}