uniform sampler2D texture;    // Texture
varying vec2      v_texcoord; // Interpolated fragment texture coordinates (in)
void main()
{
    // Final color
    gl_FragColor = texture2D(texture, v_texcoord);
}