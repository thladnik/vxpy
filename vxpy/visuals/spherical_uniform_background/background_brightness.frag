
uniform float brightness;

void main() {


    // Final color
    gl_FragColor = vec4(vec3(brightness), 1.0);

}