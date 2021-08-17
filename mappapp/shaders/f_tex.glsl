// f_tex.glsl

uniform sampler2D u_texture;    // Texture

varying vec2 v_texcoord;  // output

void main()
{
    // Final color
    gl_FragColor = texture2D(u_texture, v_texcoord);
}