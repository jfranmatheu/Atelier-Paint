from enum import Enum
from typing import List, Tuple
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from blf import (
    enable as text_enable, disable as text_disable,
    SHADOW, shadow as set_text_shadow, shadow_offset as set_set_text_shadow_offset,
    color as set_text_color, position as set_text_position, size as set_text_size,
    dimensions as get_text_dim, draw as text_draw, ROTATION, rotation as set_text_rotation,
    clipping as text_clipping, CLIPPING, WORD_WRAP, aspect as set_text_aspect
)
from gpu.state import *
from gpu.types import *
from .shaders import *
from .libcode import *

VECTOR_2 = Tuple[int, int] | Tuple[float, float]
VECTOR_4 = Tuple[int, int, int, int] | Tuple[float, float, float, float]
RGBA = Tuple[float, float, float, float]
RGB = Tuple[float, float, float]

class ShaderType(Enum):
    POINTS = 'POINTS'
    LINES = 'LINES'
    TRIS = 'TRIS'
    LINE_STRIP = 'LINE_STRIP'
    LINE_LOOP = 'LINE_LOOP'
    TRI_STRIP = 'TRI_STRIP'
    TRI_FAN = 'TRI_FAN'
    LINES_ADJ = 'LINES_ADJ'
    LINE_STRIP_ADJ = 'LINE_STRIP_ADJ'

    def __call__(self) -> str:
        return self.value


rct_indices = ((0, 1, 2), (2, 1, 3))
img_indices = ((0, 1), (0, 0), (1, 0), (1, 1))
rct_verts = lambda ax,ay,bx,by: {"pos": [(ax,ay),(bx,ay),(ax,by),(bx,by)]}
rct_top_verts = lambda ax,ay,bx,by: [(ax,ay),(ax,by),(bx,by),(bx,ay)]
rct_top_rnd_verts = lambda ax,ay,bx,by: {"pos": [(ax,ay),(ax,by),(bx,by),(bx,ay)], 'texco': img_indices,}
poly_verts = lambda points: {"pos": points}
line_verts = lambda points: {"pos": points}

shader_2d_flat = gpu.shader.from_builtin('2D_FLAT_COLOR')
shader_2d_smooth = gpu.shader.from_builtin('2D_SMOOTH_COLOR')
shader_2d_unif = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
shader_2d_image = gpu.shader.from_builtin('2D_IMAGE')
shader_2d_basic = GPUShader(vert_basic,frag_basic)
shader_2d_unif_corr = GPUShader(vert_basic,frag_unif_corr,libcode=lib_colorcor)
shader_2d_unif_uv_corr = GPUShader(vert_uv,frag_uv_rnd_corr,libcode=lib_colorcor)
shader_2d_image_basic_corr = GPUShader(vert_img,frag_img_corr,libcode=lib_colorcor)


def Rct(rct: VECTOR_4, color: VECTOR_4, shader=shader_2d_unif):
    batch = batch_for_shader(shader, ShaderType.TRIS(), rct_verts(*rct), indices=rct_indices)
    shader.bind()
    shader.uniform_float("color", color)
    if color[3]!=1.0: blend_set('ALPHA')
    batch.draw(shader)
    if color[3]!=1.0: blend_set('NONE')


def Text(pos: VECTOR_2, size: int, text: str, pivot: VECTOR_2 = (0, 1), color: RGBA = (.92, .92, .92, 1.0), font_id: int = 0, dpi: int = 72, z: int = 0):
    set_text_size(font_id, size, dpi)
    dim = get_text_dim(font_id, text)
    p = [*pos]
    if pivot[0] != 0:
        p[0] = pos[0] - dim[0] * pivot[0]
    if pivot[1] != 0:
        p[1] = pos[1] - dim[1] * pivot[1]
    set_text_position(font_id, *p, z)
    set_text_color(font_id, *color)
    text_draw(font_id, text)

def RctRnd(rct: VECTOR_4, radius: float, color: VECTOR_4, dimensions: VECTOR_2 = None, shader=shader_2d_unif, offscreen: None or Tuple[float, float] = None):
    batch = batch_for_shader(shader, ShaderType.TRI_FAN(), rct_top_rnd_verts(*rct))
    shader.bind()
    if dimensions:
        w, h = dimensions
    else:
        w,h=abs(rct[2]-rct[0]), abs(rct[3]-rct[1])
        #if offscreen:
        #    w = w*1/offscreen[0]
        #    h = h*1/offscreen[1]
    shader.uniform_float("u_dimensions", (w,h))
    shader.uniform_float("u_color", color)
    shader.uniform_float("u_radius", min(w,h)/2*radius)
    blend_set('ALPHA')
    batch.draw(shader)
    blend_set('NONE')

def Poly(co: List or Tuple, indices: List or Tuple, color: VECTOR_4 = (1, 0, 0, 1), shader=shader_2d_unif):
    batch = batch_for_shader(shader, ShaderType.TRIS(), poly_verts(co), indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    if color[3]!=1.0: blend_set('ALPHA')
    batch.draw(shader)
    if color[3]!=1.0: blend_set('NONE')

def Line(co: List or Tuple, lt: float = 2.0, color: VECTOR_4 = (1, 0, 0, 1), shader=shader_2d_unif):
    batch = batch_for_shader(shader, ShaderType.LINES(), line_verts(co))
    shader.bind()
    shader.uniform_float("color", color)
    if color[3]!=1.0: blend_set('ALPHA')
    line_width_set(lt)
    batch.draw(shader)
    if color[3]!=1.0: blend_set('NONE')
    line_width_set(1.0)


def Image(texture, pos: VECTOR_2, size: VECTOR_2, shader=shader_2d_image_basic_corr):
    #co = ((pos[0], pos[1]), (pos[0]+size[0], pos[1]), (pos[0]+size[0], pos[1]+size[1]), (pos[0], pos[1]+size[1]))
    batch = batch_for_shader(
        shader, 'TRI_FAN',
        {
            "p": ((0, 0), (1, 0), (1, 1), (0, 1)),
            "texco": ((0, 0), (1, 0), (1, 1), (0, 1)),
        },
    )

    with gpu.matrix.push_pop():
        gpu.matrix.translate(pos)
        gpu.matrix.scale(size)

        shader.bind()
        shader.uniform_sampler("image", texture)

        batch.draw(shader)
