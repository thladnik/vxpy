const float PI = 3.14159265359;

uniform float u_time;
uniform vec3 u_dot_location;
uniform float u_dot_diameter; // deg

varying vec3 v_position;

void main() {

    // Angle between dot center location and v_position
    float angle = acos(dot(normalize(v_position), normalize(u_dot_location)));

    // Threshold angle with u_dot_diameter
    float c = step(angle, u_dot_diameter / 180. * PI / 2.);

    if(c > .01) {
        gl_FragColor = vec4(vec3(1.), 1.);
    } else {
        discard;
    }
}