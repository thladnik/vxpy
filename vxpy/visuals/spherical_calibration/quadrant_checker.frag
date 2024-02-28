const float c_pi = 3.14159265359;

varying float v_azimuth; // in rad
varying float v_elevation; // in rad
varying vec3 v_position;

void main() {

    vec3 green = vec3(68.0/255.0, 150.0/255.0, 71.0/255.0);
    vec3 blue = vec3(48.0/255.0, 59.0/255.0, 150.0/255.0);
    vec3 red = vec3(195./255.0, 52.0/255.0, 38.0/255.0);
    vec3 yellow = vec3(232.0/255.0, 173.0/255.0, 35.0/255.0);

    vec3 color = vec3(0.0, 0.0, 0.0);

    // Left side negative
    if(v_azimuth < c_pi) {
        if(v_azimuth < c_pi/2) {
            color = blue;
        } else {
            color = red;
        }

    // Right side positive
    } else {

        if(v_azimuth < 3*c_pi/2) {
            color = yellow;
        } else {
            color = green;
        }
    }

    // Final color
    gl_FragColor = vec4(color, 0.0);

}