attribute vec4 a_color;         // Vertex color
uniform vec4   u_color;         // Global color
varying vec4   v_color;         // Interpolated fragment color (out)

void main() {
  v_pos = channelTransform();
  v_color     = u_color * a_color;
  gl_Position = v_pos();
}
