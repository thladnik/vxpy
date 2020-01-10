uniform sampler2D u_texture;

void main() {
    float xcoord = (pi + v_sph_pos.x) / (2.0*pi);
    float ycoord = (pi/2.0 + v_sph_pos.y) / pi;
    vec2 tex_coords = vec2(xcoord, ycoord);
    gl_FragColor = texture2D(u_texture, tex_coords);
    //gl_FragColor = vec4(xcoord, ycoord, 0.0, 1.0);
}
