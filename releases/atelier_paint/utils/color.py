from colorsys import hls_to_rgb, hsv_to_rgb, rgb_to_hls, rgb_to_hsv
from random import random, randint

from mathutils import Color

from .math import mix as mix_val


def gammify(col: Color):
    if isinstance(col, tuple):
        return (pow(ch, 2.2) for ch in col)
    return Color((pow(col.r, 2.2), pow(col.g, 2.2), pow(col.b, 2.2)))


def mix(A, B, f) -> Color:
    return Color((mix_val(A.r, B.r, f), mix_val(A.g, B.g, f), mix_val(A.b, B.b, f)))

def random_color() -> Color:
    return Color(hsv_to_rgb(random(), randint(50, 100)/100, randint(50, 100)/100))
