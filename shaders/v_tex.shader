uniform mat2 u_map_aspect;

uniform mat4 u_transformation;// Model matrix
uniform vec2 u_map_scale;         // scale factor
uniform vec2 u_shift;       // 2D translation vector
uniform mat2 u_rotate;         // scale factor

attribute vec3 a_position;   // Vertex position
attribute vec2 a_texcoord;   // texture coordinate
varying   vec2 v_texcoord;  // output

void main()
{
    // Assign varying variables v_color     = vec4(a_color,1.0);
    v_texcoord  = a_texcoord;

    // Final position
    vec4 t_pos  = u_transformation * vec4(a_position,1.0);
    vec2 pregl_pos_xy = u_rotate * t_pos.xy;
    gl_Position = vec4(pregl_pos_xy, t_pos.z, t_pos.w);
    gl_Position.xy *= u_map_scale;
    gl_Position.xy += u_shift*gl_Position.w;
    gl_Position.xy = gl_Position.xy * u_map_aspect;
}