const float pi = 3.14159265359;

// Transforms SOUTH WEST
uniform mat4   u_rot_sw;
uniform mat4   u_trans_sw;
uniform mat4   u_projection_sw;
uniform float  u_radial_offset_sw;
uniform float  u_tangent_offset_sw;

// Transforms SOUTH EAST
uniform mat4   u_rot_se;
uniform mat4   u_trans_se;
uniform mat4   u_projection_se;
uniform float  u_radial_offset_se;
uniform float  u_tangent_offset_se;

// Transforms NORTH EAST
uniform mat4   u_rot_ne;
uniform mat4   u_trans_ne;
uniform mat4   u_projection_ne;
uniform float  u_radial_offset_ne;
uniform float  u_tangent_offset_ne;

// Transforms NORTH WEST
uniform mat4   u_rot_nw;
uniform mat4   u_trans_nw;
uniform mat4   u_projection_nw;
uniform float  u_radial_offset_nw;
uniform float  u_tangent_offset_nw;

// Vertex attributes
attribute vec3 a_cart_pos;      // Cartesian vertex position
attribute vec2 a_sph_pos;       // Spherical vertex position
attribute vec2 a_channel;       // Image channel id (1: SW, 2: SE, 3: NE, 4: NW)

// Variables
varying vec4   v_cart_pos_transformed;
varying vec3   v_cart_pos;      // Cartesian vertex position
varying vec2   v_sph_pos;       // Spherical vertex position

vec4 channelTransform() {

    // Set position
    vec4 pos = vec4(a_cart_pos, 1.0);

    //// Apply appropriate transforms
    // SOUTH WEST
    if (a_channel == 1) {
        // First: 3d transformations and projection
        pos =  u_projection_sw * u_trans_sw * u_rot_sw * pos;
        //// Second: linear transformations in image plane (shifting/scaling/rotating 2d image)
        // Radial offset
        pos.xy -= u_radial_offset_sw * pos.w;
        // Rangential offset
        pos.x += u_tangent_offset_sw * pos.w;
        pos.y -= u_tangent_offset_sw * pos.w;
        // Last: return position for vertex
    }
    // SOUTH EAST
    else if (a_channel == 2) {
        // First: 3d transformations and projection
        pos = u_projection_se * u_trans_se * u_rot_se * pos;
        //// Second: linear transformations in image plane (shifting/scaling/rotating 2d image)
        // Radial offset
        pos.x += u_radial_offset_se * pos.w;
        pos.y -= u_radial_offset_se * pos.w;
        // Tangential offset
        pos.xy += u_tangent_offset_se * pos.w;
        // Last: return position for vertex
    }
    // NORTH EAST
    else if (a_channel == 3) {
        // First: 3d transformations and projection
        pos = u_projection_ne * u_trans_ne * u_rot_ne * pos;
        //// Second: linear transformations in image plane (shifting/scaling/rotating 2d image)
        // Radial offset
        pos.xy += u_radial_offset_ne * pos.w;
        // Tangential offset
        pos.x -= u_tangent_offset_ne * pos.w;
        pos.y += u_tangent_offset_ne * pos.w;
        // Last: return position for vertex
    }
    // NORTH WEST
    else if (a_channel == 4) {
        // First: 3d transformations and projection
        pos = u_projection_nw * u_trans_nw * u_rot_nw * pos;
        //// Second: linear transformations in image plane (shifting/scaling/rotating 2d image)
        // Radial offset
        pos.x -= u_radial_offset_nw * pos.w;
        pos.y += u_radial_offset_nw * pos.w;
        // Tangential offset
        pos.xy -= u_tangent_offset_nw * pos.w;
        // Last: return position for vertex
    }

    return pos;
}