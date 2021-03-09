uniform float u_mapcalib_xscale;
uniform float u_mapcalib_yscale;
uniform float u_mapcalib_xextent;
uniform float u_mapcalib_yextent;
uniform float u_small_side_size;
uniform float u_glob_x_position;
uniform float u_glob_y_position;

attribute vec2   a_position;         // Screen position
attribute vec2   a_texcoord;    // Texture coordinate
varying   vec2   v_texcoord;   // Interpolated fragment color (out)

void main() {
    v_texcoord = a_texcoord;
    gl_Position = vec4 (
                    a_position.x * u_mapcalib_xscale * u_mapcalib_xextent + u_glob_x_position,
                    a_position.y * u_mapcalib_yscale * u_mapcalib_yextent + u_glob_y_position,
                    0., 1.);
}

