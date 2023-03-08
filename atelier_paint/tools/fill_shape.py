from math import ceil
from random import randint
from time import time, sleep
import numpy as np

import bpy
from bpy.types import WorkSpaceTool
from bpy.types import Operator
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, EnumProperty
from mathutils import Matrix

from atelier_paint.gpu.draw import Rct, RctRnd, shader_2d_unif_corr, shader_2d_unif_uv_corr
from atelier_paint.utils import ImageUtils
from atelier_paint.ops import BasePaintToolOperator
from atelier_paint.utils.paint import PaintUtils

'''
# Currently this just checks the width,
# we could have different layouts as preferences too.
system = bpy.context.preferences.system
view2d = region.view2d
view2d_scale = (
    view2d.region_to_view(1.0, 0.0)[0] -
    view2d.region_to_view(0.0, 0.0)[0]
)
width_scale = region.width * view2d_scale / system.ui_scale
'''
'''
class ATELIERPAINT_OT_run_tool(Operator):
    bl_idname = 'atelierpaint.run_tool'
    bl_label = "Fill Shape"

    def invoke(self, context, event):
        bpy.ops.ed.undo_push('INVOKE_DEFAULT', message='Image Paint fill shape')
        bpy.ops.atelierpaint.fill_shape('INVOKE_DEFAULT', False)
        return {'FINISHED'}
'''

class ATELIERPAINT_OT_fill_shape(BasePaintToolOperator, Operator):
    bl_idname = 'atelierpaint.fill_shape'
    bl_label = "Fill Shape"

    #radius: IntProperty(name="Radius", default=50, min=1, soft_max=500)
    #strength: FloatProperty(name="Strength", default=1.0, min=0.01, max=1.0)
    shape: EnumProperty(
        name="Shape",
        items=(
            ('RECT', 'Rectangle', "Paints a rectangular shape"),
            ('CIRCLE', "Circle", "Paints a circular shape")
        )
    )
    roundness: IntProperty(name='Roundness', default=0, min=0, max=100, subtype='PERCENTAGE')# precision=2)
    color: FloatVectorProperty(name='Color', default=(1.0, 1.0, 1.0, 1.0), size=4, subtype='COLOR', min=0.0, max=1.0)

    def init(self, context) -> None:
        #self.color = PaintUtils.get_brush_setting(context, setting='color', default=(0.0, 0.0, 0.0, 1.0))
        #self.color = (*self.color, 1.0)
        ups = PaintUtils.get_unified_paint_settings(context)
        if ups.use_unified_color:
            self.color = (*ups.color, 1.0)
        #self.draw_args = {'color': self.color, 'shader': shader_2d_unif_uv_corr}
        #if self.roundness != 0.0:
        #    self.draw_args['radius'] = self.roundness
        if self.shape == 'CIRCLE':
            self.roundness = 100
    
    def on_mouse_move(self, context, event, mouse) -> None:
        # Simulate SHIFT so circle stay perfect.
        if not event.shift and self.shape == 'CIRCLE':
            self.on_shift_hold(context)

    def on_shift_hold(self, context) -> None:
        self.mouse_current = (self.mouse_current[0], self.mouse_init[1] + (self.mouse_current[0] - self.mouse_init[0]))

    def on_ctrl_hold(self, context) -> None:
        distances = self.get_distance(self._mouse_init, self.mouse_current, per_axis=True)
        # width, height = distances[0] * 2, distances[1] * 2
        self.mouse_init = (
            self._mouse_init[0] - distances[0],
            self._mouse_init[1] - distances[1],
        )
        self.mouse_current = (
            self._mouse_init[0] + distances[0],
            self._mouse_init[1] + distances[1],
        )

    def on_ctrl_shift_hold(self, context) -> None:
        distances = list(self.get_distance(self._mouse_init, self.mouse_current, per_axis=True))
        # width, height = distances[0] * 2, distances[1] * 2
        distances[1] = distances[0]
        self.mouse_init = (
            self._mouse_init[0] - distances[0],
            self._mouse_init[1] - distances[1],
        )
        self.mouse_current = (
            self._mouse_init[0] + distances[0],
            self._mouse_init[1] + distances[1],
        )

    def on_mouse_release(self, context, mouse) -> None:
        #if self.mouse_init == mouse:
        #    return
        if self.mouse_init[0] == mouse[0] or self.mouse_init[1] == mouse[1]:
            return
        if self.roundness == 0:
            ImageUtils.fill(
                self.image,
                [
                    *self.get_mouse_image(context, self.mouse_init),
                    *self.get_mouse_image(context, mouse)
                ],
                self.color,
                context=context
            )
        else:
            def draw_shape(rct, dim):
                RctRnd(rct, self.roundness/100, self.color, dim, shader=shader_2d_unif_uv_corr)

            ImageUtils.fill_from_offscreen(
                self.image,
                [
                    *self.get_mouse_image(context, self.mouse_init, round_int=False),
                    *self.get_mouse_image(context, mouse, round_int=False)
                ],
                draw_callback=draw_shape,
                include_image=True,
                context=context,
                projection_matrix=Matrix((
                        [0.00195, 0, 0, -0.9996],
                        [0, 0.00195, 0, -0.9996],
                        [0, 0, -0.01, -0.0],
                        [0, 0, 0, 1]
                    ))
            )

    def overlay(self, context) -> None:
        if self.roundness == 0:
            Rct([*self.mouse_init, *self.mouse_current], self.color, shader=shader_2d_unif_corr)
        else:
            RctRnd([*self.mouse_init, *self.mouse_current], self.roundness/100, self.color, shader=shader_2d_unif_uv_corr)



def draw_settings(context, layout, tool):
    props = tool.operator_properties(ATELIERPAINT_OT_fill_shape.bl_idname)
    #layout.prop(props, "mode")
    #layout.prop(props, "radius", slider=True)
    #layout.prop(props, "strength", slider=True)
    #layout.prop(props, "color")

    #ts = PaintUtils.get_brush_setting(context, setting='color', return_data=True)
    #layout.label(text='Fill Color:')
    #layout.prop(ts, "color", text="")

    ups = PaintUtils.get_unified_paint_settings(context)
    row = layout.row(align=True)
    row.label(text='Fill Color:')
    if ups.use_unified_color:
        row.prop(ups, "color", text="")
        row.prop(ups, "secondary_color", text="")
        _row = layout.row()
        _row.operator('paint.brush_colors_flip', text="", icon='FILE_REFRESH', emboss=False)
    else:
        row.prop(props, "color", text="")
    row.prop(ups, "use_unified_color", text="", icon='BRUSHES_ALL')
    
    #layout.prop(props, "roundness", slider=True)


class FillRectShapeTool(WorkSpaceTool):
    bl_space_type = 'IMAGE_EDITOR'
    bl_context_mode = 'PAINT' # default: 'All'

    # The prefix of the idname should be your add-on name.
    bl_idname = "atelier_paint.fill_rect_shape"
    bl_label = "Draw Rectangle"
    bl_description = (
        "Draw a rectangular shape\n"
        #"with or without rounded corners\n"
        "and fill it with color"
    )
    bl_icon = "ops.gpencil.primitive_box"
    bl_cursor = 'PICK_AREA'
    #bl_data_block = 'BRUSH' # ('DEFAULT', 'NONE', 'WAIT', 'CROSSHAIR', 'MOVE_X', 'MOVE_Y', 'KNIFE', 'TEXT', 'PAINT_BRUSH', 'PAINT_CROSS', 'DOT', 'ERASER', 'HAND', 'SCROLL_X', 'SCROLL_Y', 'SCROLL_XY', 'EYEDROPPER', 'PICK_AREA', 'STOP', 'COPY', 'CROSS', 'MUTE', 'ZOOM_IN', 'ZOOM_OUT')'''
    bl_widget = None
    bl_operator = ATELIERPAINT_OT_fill_shape.bl_idname
    bl_keymap = (
        (ATELIERPAINT_OT_fill_shape.bl_idname, {"type": 'LEFTMOUSE', "value": 'PRESS'}, {}),
        (ATELIERPAINT_OT_fill_shape.bl_idname, {"type": 'LEFTMOUSE', "value": 'PRESS', "ctrl": True}, {}),
        (ATELIERPAINT_OT_fill_shape.bl_idname, {"type": 'LEFTMOUSE', "value": 'PRESS', "shift": True}, {}),
    )

    def draw_settings(context, layout, tool):
        draw_settings(context, layout, tool)
