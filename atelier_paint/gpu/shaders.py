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
  gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0, 1.0);
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
frag_grid = """
in vec2 uv;
out vec4 fragColor;
uniform vec4 u_color;
//uniform float u_zoom;
uniform vec2 u_dimensions;

void main()
{
  //vec2 grid_uv = uv * u_dimensions;
  //vec2 grid = fract(grid_uv);
  //if ( (grid.x < 0.98 && grid.y < 0.98) && (grid.x > 0.02 && grid.y > 0.02) )
  //  discard;
  //fragColor = u_color;

  float uTileSize = 1/u_dimensions.x;
  float uGridBorderSize = uTileSize * 0.1; //max(uTileSize * 0.05, uTileSize * 0.1 * u_zoom);
  
  float uBigTileSize = uTileSize * 4;
  float uBigGridBorderSize = uGridBorderSize * 2.0; // * u_zoom;

  vec2 grid_uv = mod(uv.xy - vec2(uGridBorderSize*0.5), vec2(uTileSize));
  vec2 big_grid_uv = mod(uv.xy - vec2(uGridBorderSize*0.5), vec2(uBigTileSize));

  if(max(grid_uv.x, grid_uv.y) > (uTileSize-uGridBorderSize))
    fragColor = u_color;
  else
    discard;
  //if(max(big_grid_uv.x, big_grid_uv.y) > (uBigTileSize-uGridBorderSize))
  //  fragColor = vec4(u_color.rgb*vec3(0.75), u_color.a);
}
"""
'''
if (mod(gl_FragCoord.x, u_dimensions.x) < 1.0 ||
    mod(gl_FragCoord.y, u_dimensions.y) < 1.0) {
    fragColor = u_color;
  } else {
    fragColor.a = coords.x * coords.y;
    discard;
  }
'''
frag_grid_multi = """
out vec4 fragColor;
in vec2 uv;
//uniform vec4 u_color;
uniform vec2 u_dimensions;

float grid(vec2 co, float res){
  vec2 grid = fract(co*res);
  return 1.-(step(res,grid.x) * step(res,grid.y));
}

float box(in vec2 co, in vec2 size){
  size = vec2(0.5) - size*0.5;
  vec2 uv = smoothstep(size,
                      size+vec2(0.001),
                      co);
  uv *= smoothstep(size,
                  size+vec2(0.001),
                  vec2(1.0)-co);
  return uv.x*uv.y;
}

float cross(in vec2 co, vec2 size){
  return  clamp(box(co, vec2(size.x*0.5,size.y*0.125)) +
          box(co, vec2(size.y*0.125,size.x*0.5)),0.,1.);
}

void main(){
  vec2 coords = uv/u_dimensions.xy;//gl_FragCoord.xy
  coords.x *= u_dimensions.x/u_dimensions.y;

  vec3 color = vec3(0.0);

  vec2 grid_co = coords; //*300.;
  color += vec3(0.5,0.,0.)*grid(grid_co,0.01);
  color += vec3(0.2,0.,0.)*grid(grid_co,0.02);
  color += vec3(0.2)*grid(grid_co,0.1);

  vec2 crosses_co = coords + .5;
  crosses_co *= 3.;
  vec2 crosses_co_f = fract(crosses_co);
  color *= 1.-cross(crosses_co_f,vec2(.3,.3));
  color += vec3(.9)*cross(crosses_co_f,vec2(.2,.2));

  fragColor = vec4( color , 1.0);
  fragColor = blender_srgb_to_framebuffer_space(fragColor);
}
"""

frag_grid_tiles_4x4_marked = """
in vec2 uv;
out vec4 fragColor;
uniform vec4 u_color;
uniform vec2 u_dimensions;

void main()
{
  //vec2 grid_uv = uv * u_dimensions;
  //vec2 grid = fract(grid_uv);
  //if ( (grid.x < 0.98 && grid.y < 0.98) && (grid.x > 0.02 && grid.y > 0.02) )
  //  discard;
  //fragColor = u_color;

  float uTileSize = 1/u_dimensions.x;
  float uGridBorderSize = uTileSize * 0.1;
  
  float uBigTileSize = uTileSize * 4;
  float uBigGridBorderSize = uBigTileSize * 0.1;

  vec2 grid_uv = mod(uv.xy - vec2(uGridBorderSize*0.5), vec2(uTileSize));
  vec2 big_grid_uv = mod(uv.xy - vec2(uBigGridBorderSize*0.5), vec2(uBigTileSize));

  if(max(big_grid_uv.x, big_grid_uv.y) < (uBigTileSize-uBigGridBorderSize))
    fragColor = vec4(pow(u_color.rgb, vec3(.5)), u_color.a);
  else if(max(grid_uv.x, grid_uv.y) < (uTileSize-uGridBorderSize))
    fragColor = u_color;
  else
    fragColor = vec4(0.0);
}
"""