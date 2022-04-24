vert_basic = """
uniform mat4 ModelViewProjectionMatrix;
in vec2 pos;
void main()
{
  gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""
frag_basic = """
uniform vec4 color;
out vec4 fragColor;
void main()
{
  fragColor = color;
  //fragColor = blender_srgb_to_framebuffer_space(fragColor);
}
"""
frag_unif_corr = """
uniform vec4 color;
out vec4 fragColor;
void main()
{
  fragColor.rgb = color.rgb; //pow(color.rgb, vec3(2.2));
  fragColor.a = color.a;
  fragColor = blender_srgb_to_framebuffer_space(fragColor);
}
"""
vert_uv = """
uniform mat4 ModelViewProjectionMatrix;
in vec2 pos;
in vec2 texco;
out vec2 uv;
void main()
{
  uv = texco;
  gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""
frag_uv_rnd_corr = """
in vec2 uv;
out vec4 fragColor;
uniform vec2 u_dimensions;
uniform vec4 u_color;
uniform float u_radius;
void main()
{
  vec2 cir_top_left = (vec2(0, u_dimensions.y) + vec2(u_radius, -u_radius));
  vec2 cir_top_right = (vec2(u_dimensions.x, u_dimensions.y) + vec2(-u_radius, -u_radius));
  vec2 cir_bot_left = vec2(u_radius);
  vec2 cir_bot_right = (vec2(u_dimensions.x, 0) + vec2(-u_radius, u_radius));
  vec2 coords = uv * u_dimensions;
  float amp_radius = u_radius + 0.2;
  float alpha = 1.0;
  float len = 0.0;
  if (coords.x < cir_top_left.x && coords.y > cir_top_left.y)// && length(coords - cir_top_left) > u_radius)
  {
    len = length(coords - cir_top_left);
  }
  else if (coords.x > cir_top_right.x && coords.y > cir_top_right.y)// && length(coords - cir_top_right) > u_radius)
  {
    len = length(coords - cir_top_right);
  }
  else if (coords.x < cir_bot_left.x && coords.y < cir_bot_left.y)
  {
    len = length(coords - cir_bot_left);
  }
  else if (coords.x > cir_bot_right.x && coords.y < cir_bot_right.y)
  {
    len = length(coords - cir_bot_right);
  }
  if (len > amp_radius)
    discard;
  else
    alpha = smoothstep(amp_radius, u_radius-0.6, len);
  //fragColor.rgb = pow(u_color.rgb, vec3(2.2));
  fragColor.rgb = u_color.rgb;
  fragColor.a = alpha * u_color.a;
  fragColor = blender_srgb_to_framebuffer_space(fragColor);
}
"""
vert_img = """
uniform mat4 ModelViewProjectionMatrix;
in vec2 texco;
in vec2 p;
out vec2 texco_interp;
void main()
{
 gl_Position = ModelViewProjectionMatrix * vec4(p, 0.0, 1.0);
 texco_interp = texco;
}
"""
frag_img_corr = """
in vec2 texco_interp;
out vec4 fragColor;
uniform sampler2D image;
void main()
{
 vec4 texColor = texture(image, texco_interp);
 if(texColor.a < 0.05)
  discard;
 //fragColor.rgb = pow(texColor.rgb, vec3(.4545));
 fragColor.rgb = to_srgb(texColor.rgb);
 fragColor.a = texColor.a;
}
"""