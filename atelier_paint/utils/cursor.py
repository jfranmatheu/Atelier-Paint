from enum import Enum
import bpy


class CursorIcon(Enum):
    DEFAULT       =      'DEFAULT'
    NONE          =         'NONE'
    WAIT          =         'WAIT'
    CROSSHAIR     =    'CROSSHAIR'
    MOVE_X        =       'MOVE_X'
    MOVE_Y        =       'MOVE_Y'
    KNIFE         =        'KNIFE'
    TEXT          =         'TEXT'
    PAINT_BRUSH   =  'PAINT_BRUSH'
    PAINT_CROSS   =  'PAINT_CROSS'
    HAND          =         'HAND'
    SCROLL_X      =     'SCROLL_X'
    SCROLL_Y      =     'SCROLL_Y'
    SCROLL_XY     =    'SCROLL_XY'
    EYEDROPPER    =   'EYEDROPPER'
    DOT           =          'DOT'
    ERASER        =       'ERASER'


class Cursor:
    @staticmethod
    def set_icon(context=None, cursor = CursorIcon.DEFAULT):
        if not context: context = bpy.context
        context.window.cursor_modal_set(cursor.value)

    @staticmethod
    def wrap(x, y, context=bpy.context):
        context.window.cursor_warp(x, y)

    @staticmethod
    def restore(context=None):
        if not context: context = bpy.context
        context.window.cursor_modal_restore()
