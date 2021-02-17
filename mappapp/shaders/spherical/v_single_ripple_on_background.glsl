// v_sphere_map.glsl

uniform mat2 u_mapcalib_aspectscale;
uniform vec2 u_mapcalib_scale;
uniform mat4 u_mapcalib_transform3d;
uniform mat4 u_mapcalib_rotate3d;
uniform vec2 u_mapcalib_translate2d;
uniform mat2 u_mapcalib_rotate2d;

uniform float u_mod_zlayer;

attribute vec3 a_position;
attribute float a_azimuth;
attribute float a_elevation;

varying float v_azimuth;
varying float v_elevation;
varying vec3 v_position;

// TODO: try to make use of manual blending / discarding fragments in order to GET RID OF THE Z-LAYER
void main()
{
    // Final position
    float zlayer = 1.0 + 0.0001 * u_mod_zlayer;
    vec4 pos = u_mapcalib_transform3d * u_mapcalib_rotate3d * vec4(a_position.x*zlayer, a_position.y*zlayer, a_position.z*zlayer, 1.0);
    gl_Position = vec4(((u_mapcalib_rotate2d * pos.xy) * u_mapcalib_scale + u_mapcalib_translate2d * pos.w) * u_mapcalib_aspectscale, pos.z, pos.w);

    v_azimuth = a_azimuth;
    v_elevation = a_elevation;
    v_position = a_position;

}
