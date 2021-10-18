uniform float u_x_offset;
uniform float u_y_offset;
uniform float u_linewidth;

const float c_pi = 3.14159265359;
varying vec2 v_nposition;

void main() {
    float line_x = smoothstep(0.,0.+u_linewidth,abs(v_nposition.x*2.-1.-u_x_offset));
    float line_y = smoothstep(0.,0.+u_linewidth,abs(v_nposition.y*2.-1.-u_y_offset));
    gl_FragColor = vec4(vec3(1.0)*line_x*line_y, 1.0);
}
