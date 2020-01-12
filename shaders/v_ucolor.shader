uniform mat4 u_transformation;// Model matrix
uniform vec2 u_scale;         // scale factor
uniform vec2 u_shift;       // 2D translation vector
uniform mat2 u_rotate;         // scale factor
uniform vec4 u_color;    // Vertex position
attribute vec3 position;   // Vertex positions

varying vec4   v_color;    // Interpolated fragment color (out)

void main()
{
    // Assign varying variables
    v_color = u_color;

    // Final position
    vec4 t_pos  = u_transformation * vec4(position,1.0);
    vec2 pregl_pos_xy = u_rotate * t_pos.xy;
    gl_Position = vec4(pregl_pos_xy,t_pos.z,t_pos.w);
    gl_Position.xy *= u_scale;
    gl_Position.xy += u_shift*gl_Position.w;
}
