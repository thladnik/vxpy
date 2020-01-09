attribute vec2 texcoord;   // texture coordinate
varying   vec2 v_texcoord;  // output

void main() {
  v_pos = channelTransform();
  v_texcoord = texcoord;
  gl_Position = v_pos();
}
