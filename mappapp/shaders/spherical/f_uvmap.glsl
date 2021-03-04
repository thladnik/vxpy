// f_uvmap.glsl

varying vec2 v_texcoord;

void main() {
    float u = a_cart_pos.x / sqrt(square(a_cart_pos.x) + square(a_cart_pos.y) + square(a_cart_pos.z));
    float v = a_cart_pos.y / sqrt(square(a_cart_pos.x) + square(a_cart_pos.y) + square(a_cart_pos.z));

    v_texcoord = vec2(u, v);
}
