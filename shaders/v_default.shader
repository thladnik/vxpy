

void main() {
  v_cart_pos = a_cart_pos;
  v_sph_pos = a_sph_pos;
  v_cart_pos_transformed = channelTransform();

  // Final position
  gl_Position = v_cart_pos_transformed;

  //<viewport.transform>;
}