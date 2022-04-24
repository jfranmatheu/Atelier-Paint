from math import hypot


def clamp(value, min_value: float or int = 0, max_value: float or int = 1):
    return max(min_value, min(max_value, value))

def map_value(val, src, dst):
    """
    Scale the given value from the scale of src to the scale of dst.
    """
    return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]

def mix(x, y, a):
    return x*(1-a)+y*a

def distance_between(_p1, _p2):
    return hypot(_p1[0] - _p2[0], _p1[1] - _p2[1])
    #return math.sqrt((_p1[1] - _p1[0])**2 + (_p2[1] - _p2[0])**2)

def sign(p1, p2, p3) -> float:
    return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y)

def point_inside_tri(pt, v1, v2, v3) -> bool:
    d1: float = sign(pt, v1, v2)
    d2: float = sign(pt, v2, v3)
    d3: float = sign(pt, v3, v1)

    has_neg: bool = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos: bool = (d1 > 0) or (d2 > 0) or (d3 > 0)

    return not (has_neg and has_pos)
