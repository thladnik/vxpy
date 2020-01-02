uniform mat4   model;      // Model matrix
uniform mat4   view;       // View matrix
uniform mat4   projection; // Projection matrix
attribute vec2 position;   // Vertex position
attribute vec2 texcoord;   // Vertex texture coordinates red
varying vec2   v_texcoord;   // Interpolated fragment texture coordinates (out)

void main()
{
    // Assign varying variables
    v_texcoord  = texcoord;

    // Final position
    gl_Position = projection * view * model * vec4(position,0.0,1.0);
}