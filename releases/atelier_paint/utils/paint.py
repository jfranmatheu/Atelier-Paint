from ctypes import cast
from os import stat
from atelier_paint.utils.color import random_color
import bpy
from mathutils import Color


class PaintUtils():
    ''' POLL FUNCTIONS. '''
    @staticmethod
    def poll_texture_paint(ctx):
        return ctx.active_object and ctx.mode == 'PAINT_TEXTURE'

    @staticmethod
    def poll_texture_paint_paint_slots(ctx):
        return ctx.active_object and ctx.active_object.active_material and ctx.mode == 'PAINT_TEXTURE'

    ''' UTILS. '''
    @staticmethod
    def switch_colors():
        bpy.ops.paint.brush_colors_flip()
    
    @staticmethod
    def get_paint_settings(ctx):
        if ctx.mode == 'PAINT_TEXTURE':
            return ctx.tool_settings.image_paint
        elif ctx.mode == 'PAINT_VERTEX':
            return ctx.tool_settings.vertex_paint
        elif ctx.mode == 'SCULPT':
            return ctx.tool_settings.sculpt

    @staticmethod
    def get_unified_paint_settings(ctx):
        return ctx.tool_settings.unified_paint_settings

    @staticmethod
    def toggle_brush_cursor(state: bool, context = None):
        if context:
            PaintUtils.get_paint_settings(context).show_brush = state
        else:
            PaintUtils.get_paint_settings(bpy.context).show_brush = state     

    @staticmethod
    def get_paint_color(ctx, secondary: bool = False):
        ups = PaintUtils.get_unified_paint_settings(ctx)
        if ups.use_unified_color:
            return ups.color if not secondary else ups.secondary_color
        ps = PaintUtils.get_paint_settings(ctx)
        if not ps or not ps.brush:
            return None
        return ps.brush.color if not secondary else ps.brush.secondary_color

    @staticmethod
    def set_color(ctx, color: Color = Color((0, 0, 0)), secondary: bool = False, random: bool = False):
        color_host = PaintUtils.get_paint_color_data_host(ctx)
        if not color_host:
            return
        if random:
            color = random_color()
        setattr(color_host, 'secondary_color' if secondary else 'color', color)

    @staticmethod
    def get_paint_color_data_host(ctx, secondary: bool = False):
        ups = PaintUtils.get_unified_paint_settings(ctx)
        if ups.use_unified_color:
            return ups
        ps = PaintUtils.get_paint_settings(ctx)
        if not ps or not ps.brush:
            return None
        return ps.brush

    #@staticmethod
    #def get_sculptpaint_color_data_host(ctx):
    #    if UnifiedPaintPanel.paint_settings(ctx):
    #        ups = PaintUtils.get_unified_paint_settings(ctx)
    #        if ups.use_unified_color:
    #            return ups
    #    return ctx.tool_settings.sculpt.brush
    
    @staticmethod
    def use_unified(ctx, setting: str = 'color') -> bool:
        ups = PaintUtils.get_unified_paint_settings(ctx)
        return getattr(ups, 'use_unified_'+setting, False)

    @staticmethod
    def get_brush_setting(ctx, setting: str = 'size', return_data: bool = False, cast=None, default=None):
        if setting not in {'size', 'strength', 'color', 'weight'}:
            return None
        ups = PaintUtils.get_unified_paint_settings(ctx)
        if getattr(ups, 'use_unified_'+setting):
            if return_data:
                return ups
            if cast:
                return cast(getattr(ups, setting))
            return getattr(ups, setting)
        ps = PaintUtils.get_paint_settings(ctx)
        if not ps or not ps.brush:
            return default
        if return_data:
            return ps.brush
        if cast:
            return cast(getattr(ps.brush, setting))
        return getattr(ps.brush, setting)

    @staticmethod
    def get_active_brush(ctx):
        paint_settings = PaintUtils.get_paint_settings(ctx)
        if not paint_settings:
            return None
        return paint_settings.brush

    @staticmethod
    def get_texture_paint_images(ctx):
        if not PaintUtils.poll_texture_paint_paint_slots(ctx):
            return None
        return ctx.active_object.active_material.texture_paint_images

    @staticmethod
    def get_active_paint_slot(ctx = None):
        if not ctx:
            ctx = bpy.context
        if not PaintUtils.poll_texture_paint_paint_slots(ctx):
            return None
        return ctx.active_object.active_material.paint_active_slot # This is an index.

    @staticmethod
    def get_active_texture_paint_image(ctx = None):
        if not ctx:
            ctx = bpy.context
        index = PaintUtils.get_active_paint_slot(ctx)
        if index == None:
            return None
        return PaintUtils.get_texture_paint_images(ctx)[index]

    @staticmethod
    def new_paint_slot(ctx = None):
        if not ctx:
            ctx = bpy.context
        if not PaintUtils.poll_texture_paint(ctx):
            return
        bpy.ops.paint.add_texture_paint_slot('INVOKE_DEFAULT')
