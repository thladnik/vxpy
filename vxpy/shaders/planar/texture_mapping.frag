uniform sampler2D u_texture;    // Texture
varying   vec2 v_texcoord;  // output

void main() {
    gl_FragColor = texture2D(u_texture, v_texcoord);
}
