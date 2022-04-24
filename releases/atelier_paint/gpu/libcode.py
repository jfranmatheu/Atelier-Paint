libcode="""
vec3 RGB2Lab(in vec3 rgb){
    float R = rgb.x;
    float G = rgb.y;
    float B = rgb.z;
    // threshold
    float T = 0.008856;

    float X = R * 0.412453 + G * 0.357580 + B * 0.180423;
    float Y = R * 0.212671 + G * 0.715160 + B * 0.072169;
    float Z = R * 0.019334 + G * 0.119193 + B * 0.950227;

    // Normalize for D65 white point
    X = X / 0.950456;
    Y = Y;
    Z = Z / 1.088754;

    bool XT, YT, ZT;
    XT = false; YT=false; ZT=false;
    if(X > T) XT = true;
    if(Y > T) YT = true;
    if(Z > T) ZT = true;

    float Y3 = pow(Y,1.0/3.0);
    float fX, fY, fZ;
    if(XT){ fX = pow(X, 1.0/3.0);} else{ fX = 7.787 * X + 16.0/116.0; }
    if(YT){ fY = Y3; } else{ fY = 7.787 * Y + 16.0/116.0 ; }
    if(ZT){ fZ = pow(Z,1.0/3.0); } else{ fZ = 7.787 * Z + 16.0/116.0; }

    float L; if(YT){ L = (116.0 * Y3) - 16.0; }else { L = 903.3 * Y; }
    float a = 500.0 * ( fX - fY );
    float b = 200.0 * ( fY - fZ );

    return vec3(L,a,b);
}

varying vec2 uv;
uniform sampler2D texture;

void main(void){
	vec4 c = texture2D(texture, uv);
	
	vec3 lab = RGB2Lab(c.rgb);
	
	lab.z -= lab.y;
	lab.y += -lab.x*0.4;
	
	gl_FragColor = vec4(lab/255.0, 1.0);
    //gl_FragColor = vec4(uv.x, uv.y, 1.0, 1.0);
}
"""
lib_gammify="""
vec3 gammify(vec3 co, float f){
    return pow(co, vec3(f));
}
vec3 gammify22(vec3 co){
    return gammify(co, 2.2);
}
vec3 gammify24(vec3 co){
    return gammify(co, 2.4);
}
vec3 gammify26(vec3 co){
    return gammify(co, 2.6);
}
"""
lib_colorcor="""
vec3 gammify(vec3 co, float f){
    return pow(co, vec3(f));
}
vec3 gammify22(vec3 co){
    return gammify(co, 2.2);
}
vec3 gammify24(vec3 co){
    return gammify(co, 2.4);
}
vec3 gammify26(vec3 co){
    return gammify(co, 2.6);
}

const vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);

vec3 hsv2rgb(vec3 c)
{
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

vec3 hsv_to_rgb(in vec3 c)
{
    vec3 rgb = clamp(abs(mod(c.x*6.0+vec3(0.0,4.0,2.0),6.0)-3.0)
                        -1.0,
                        0.0,
                        1.0 );
    rgb = rgb*rgb*(3.0-2.0*rgb);
    return c.z * mix( vec3(1.0), rgb, c.y);
}

float linear_to_sRGB(float theLinearValue) {
    return theLinearValue <= 0.0031308
        ? theLinearValue * 12.92
        : pow(theLinearValue, 1.0/2.4) * 1.055 - 0.055;
}

float sRGB_to_linear(float thesRGBValue) {
    return thesRGBValue <= 0.04045
        ? thesRGBValue / 12.92
        : pow((thesRGBValue + 0.055) / 1.055, 2.4);
}

vec3 to_srgb(vec3 co) {
    co.r = linear_to_sRGB(co.r);
    co.g = linear_to_sRGB(co.g);
    co.b = linear_to_sRGB(co.b);
    return co;
}

vec3 corrected(vec3 co){
    co.r = sRGB_to_linear(co.r);
    co.g = sRGB_to_linear(co.g);
    co.b = sRGB_to_linear(co.b);
    return co;
}

vec3 bcorrected(vec3 co){
    co.r = sRGB_to_linear(co.r);
    co.g = sRGB_to_linear(co.g);
    co.b = sRGB_to_linear(co.b);
    return gammify(co, 1.055); // 1.1
}

// Converts a color from linear light gamma to sRGB gamma
vec4 fromLinear(vec4 linearRGB)
{
    bvec3 cutoff = lessThan(linearRGB.rgb, vec3(0.0031308));
    vec3 higher = vec3(1.055)*pow(linearRGB.rgb, vec3(1.0/2.4)) - vec3(0.055);
    vec3 lower = linearRGB.rgb * vec3(12.92);

    return vec4(mix(higher, lower, cutoff), linearRGB.a);
}

// Converts a color from sRGB gamma to linear light gamma
vec4 toLinear(vec4 sRGB)
{
    bvec3 cutoff = lessThan(sRGB.rgb, vec3(0.04045));
    vec3 higher = pow((sRGB.rgb + vec3(0.055))/vec3(1.055), vec3(2.4));
    vec3 lower = sRGB.rgb/vec3(12.92);

    return vec4(mix(higher, lower, cutoff), sRGB.a);
}

/*
vec3 hsv_to_rgb_bcorrected(vec co){
    return bcorrected(hsv2rgb(co));
}
*/
"""

def linear_to_srgb(r, g, b):
    def linear(c):
        a = .055
        if c <= .0031308:
            return 12.92 * c
        else:
            return (1+a) * c**(1/2.4) - a
    return tuple(linear(c) for c in (r, g, b))

def srgb_to_linear(r, g, b):
    def srgb(c):
        a = .055
        if c <= .04045:
            return c / 12.92
        else:
            return ((c+a) / (1+a)) ** 2.4
    return tuple(srgb(c) for c in (r, g, b))
