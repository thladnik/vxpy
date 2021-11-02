// v_glider.glsl

uniform mat2 u_mapcalib_aspectscale;
uniform vec2 u_mapcalib_scale;
uniform mat4 u_mapcalib_transform3d;
uniform mat4 u_mapcalib_rotate3d;
uniform vec2 u_mapcalib_translate2d;
uniform mat2 u_mapcalib_rotate2d;


attribute vec3 a_position;
attribute float a_azimuth;
attribute float a_elevation;

varying float v_azimuth;
varying float v_elevation;

void main() {
    v_azimuth = a_azimuth;
    v_elevation = a_elevation;

    // Final position
    vec4 pos = u_mapcalib_transform3d * u_mapcalib_rotate3d * vec4(a_position,1.0);
    gl_Position = vec4(((u_mapcalib_rotate2d * pos.xy) * u_mapcalib_scale + u_mapcalib_translate2d * pos.w) * u_mapcalib_aspectscale, pos.z, pos.w);

}
