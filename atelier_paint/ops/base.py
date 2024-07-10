from math import ceil
from random import randint
from typing import Set, Tuple
import numpy as np
from atelier_paint.utils.image import ImageUtils
from atelier_paint.utils.paint import PaintUtils

import bpy
from bpy.types import Event, SpaceView3D, SpaceImageEditor
from mathutils import Vector

from atelier_paint.utils import math


class BasePaintToolOperator:
    bl_label = "Paint Tool"

    use_gizmo = False
    use_undo_hack = True
    use_overlay = True
    use_modal = True
    finish_on_mouse_release = True
    confirm_events = set()
    #bl_options = {'UNDO', 'UNDO_GROUPED'}

    @classmethod
    def poll(cls, context):
        return context.space_data.image is not None and context.space_data.ui_mode == 'PAINT'

    def get_mouse_region(self, event):
        return (event.mouse_region_x, event.mouse_region_y)

    def get_mouse_image(self, context, mouse, relative_input: bool = False, normalized: bool = False, clamp: bool = True, round_int: bool = True):
        if isinstance(mouse, Event):
            mouse = self.get_mouse_region(mouse)
        elif relative_input:
            #print(mouse)
            mouse = (mouse[0]*context.region.width, mouse[1]*context.region.height)
            #print(mouse)
        mp = context.region.view2d.region_to_view(*mouse)
        #print(mp)
        if clamp:
            mp = (math.clamp(mp[0]), math.clamp(mp[1]))
        if normalized:
            return mp
        if round_int:
            #print((int(mp[0]*self.image.size[0]), int(mp[1]*self.image.size[1])))
            return (int(mp[0]*self.image.size[0]), int(mp[1]*self.image.size[1]))
        return (mp[0]*self.image.size[0], mp[1]*self.image.size[1])

    def invoke(self, context, event) -> Set[str]:
        #print(event.type, event.value)
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.image = context.space_data.image
            self.init(context)
            if hasattr(self, 'color'):
                if PaintUtils.use_unified(context, 'color'):
                    color = PaintUtils.get_brush_setting(context, 'color')
                    # Use RGBA?
                    if len(self.color) == 4:
                        self.color = (*color, 1.0)
                    else:
                        self.color = color
                # Color Correction.
                #self.color = (*[pow(v, .454545) for v in self.color[:3]], self.color[3])
            self._on_mouse_press(context, event)
            if self.use_modal:
                if self.use_overlay:
                    self.start_draw(context)
                self.start_modal(context, event)
                return {'RUNNING_MODAL'}
        return {'FINISHED'}

    def modal(self, context, event) -> Set[str]:
        #print(event.type, event.value)
        #print(context.space_data.cursor_location)
        if self.finished:
            self.stop_draw(context)
            return {'FINISHED'}
        context.region.tag_redraw()

        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'MOUSEMOVE':
            if self.displacing:
                self._on_displace(context, event)
            else:
                self._on_mouse_move(context, event)
        elif event.type == 'SPACE':
            if event.value == 'PRESS':
                self.displacing = True
                self.mouse_displace = Vector(self.get_mouse_region(event))
            elif event.value == 'RELEASE':
                self.displacing = False
        elif event.type == 'X' and event.value == 'PRESS':
            self.on_x_press(context)
            return {'RUNNING_MODAL'}

        if event.shift and event.ctrl:
            self.on_ctrl_shift_hold(context)
        if event.shift:
            self.on_shift_hold(context)
        elif event.ctrl:
            self.on_ctrl_hold(context)
        elif event.alt:
            self.on_alt_hold(context)

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and not self.finish_on_mouse_release:
                self._on_mouse_press(context, event)
                return {'RUNNING_MODAL'}
            if event.value == 'RELEASE':
                if self.finish_on_mouse_release:
                    self.finish(context)
                    if self.use_undo_hack:
                        self.push_undo_hack(context)
                    self._on_mouse_release(context, event)
                    bpy.ops.ed.undo_push(message='Paint Tool')
                    return {'FINISHED'}
                else:
                    self._on_mouse_release(context, event)

        if self.fake_confirm or (event.type in self.confirm_events and event.value == 'RELEASE'):
            self.finish(context)
            if self.use_undo_hack:
                self.push_undo_hack(context)
            self.confirm(context, self.get_mouse_region(event))
            bpy.ops.ed.undo_push(message='Paint Tool')
            self.finished = True
            #return {'FINISHED'}
            return {'RUNNING_MODAL'}

        if self.use_gizmo and self.mouse_pressed and event.type == 'MOUSEMOVE':
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}

    def init(self, context) -> None:
        pass

    def confirm(self, context, event) -> None:
        pass
    
    def on_x_press(self, context) -> None:
        pass

    def _on_mouse_press(self, context, event) -> None:
        if self.use_gizmo:
            self.mouse_pressed = True
        context.region.tag_redraw()
        self.on_mouse_press(context, self.get_mouse_region(event))

    def _on_mouse_move(self, context, event) -> None:
        context.region.tag_redraw()
        self.mouse_current = self.get_mouse_region(event)
        self.on_mouse_move(context, event, self.mouse_current)

    def _on_mouse_release(self, context, _event) -> None:
        if self.use_gizmo:
            self.mouse_pressed = False
        #undo_image = bpy.data.images.get('.undo_image', None)
        #if not undo_image:
        #    undo_image = bpy.data.images.new('.undo_image', *self.image.size)
        #ImageUtils.copy(self.image, undo_image)
        #bpy.ops.ed.undo_push('INVOKE_DEFAULT', False, message='Paint Tool: ' + self.bl_label + str(randint(0, 1000000)))
        context.region.tag_redraw()
        self.on_mouse_release(context, self.mouse_current)

    def push_undo_hack(self, context):
        PaintUtils.set_color(context, random=True)
        mp = context.region.view2d.view_to_region(0,0)
        strokes = [
        {
            'name' : "Stroke_0",
            'is_start' : True,
            'location' : (0,0,0),
            'mouse' : mp,
            'mouse_event' : mp,
            'pen_flip' : False,
            'pressure' : 1.0,
            'size' : 1,
            'time' : 0,
            'x_tilt' : 0,
            'y_tilt' : 0
        },{
            'name' : "Stroke_1",
            'is_start' : False,
            'location' : (0,0,0),
            'mouse' : mp,
            'mouse_event' : mp,
            'pen_flip' : False,
            'pressure' : 1.0,
            'size' : 2,
            'time' : 0.5,
            'x_tilt' : 0,
            'y_tilt' : 0
        },{
            'name' : "Stroke_2",
            'is_start' : False,
            'location' : (0,0,0),
            'mouse' : mp,
            'mouse_event' : mp,
            'pen_flip' : False,
            'pressure' : 1.0,
            'size' : 1,
            'time' : 1.0,
            'x_tilt' : 0,
            'y_tilt' : 0
        }
        ]
        ctx = {'window': context.window, 'area': context.area, 'region': context.region}
        with context.temp_override(**ctx):
            bpy.ops.paint.image_paint('EXEC_DEFAULT', True, stroke=strokes, mode='NORMAL')
        PaintUtils.set_color(context, self.color[:3])


    def _on_displace(self, context, event) -> None:
        threshold = 1 # 1px.
        context.region.tag_redraw()
        current_mouse = Vector(self.get_mouse_region(event))
        self.displace_offset = current_mouse - self.mouse_displace
        mp = self.displace_offset
        self.displace_offset = Vector((int(mp[0]), int(mp[1])))
        if abs(self.displace_offset[0]) < threshold:
            self.displace_offset[0] = 0
        elif abs(self.displace_offset[1]) < threshold:
            self.displace_offset[1] = 0
        if self.displace_offset[0] == 0 and self.displace_offset[1] == 0:
            return
        self.mouse_displace = current_mouse
        self.mouse_init = self.get_mouse_displace(self.mouse_init)
        self.mouse_current = self.get_mouse_displace(self.mouse_current)
        self.on_displace(context, self.get_mouse_displace)

    def on_displace(self, context, displace_point: callable) -> None:
        pass

    def get_mouse_displace(self, mouse) -> Tuple[int, int]:
        mp = Vector(mouse) + self.displace_offset
        return (int(mp[0]), int(mp[1]))

    def on_mouse_press(self, context, mouse) -> None:
        pass

    def on_mouse_release(self, context, mouse) -> None:
        pass

    def on_mouse_move(self, context, event, mouse) -> None:
        pass

    def on_shift_hold(self, context) -> None:
        pass

    def on_alt_hold(self, context) -> None:
        pass

    def on_ctrl_hold(self, context) -> None:
        pass

    def on_ctrl_shift_hold(self, context) -> None:
        pass

    def get_offset(self, from_mouse, to_mouse, as_vector: bool = False) -> Tuple[int, int]:
        if not isinstance(from_mouse, Vector):
            from_mouse = Vector(from_mouse)
        if not isinstance(to_mouse, Vector):
            to_mouse = Vector(to_mouse)
        offset = to_mouse - from_mouse
        if as_vector:
            return offset
        return (int(offset[0]), int(offset[1]))

    def get_distance(self, from_mouse, to_mouse, per_axis: bool = False) -> Tuple[int, int] or float:
        offset = self.get_offset(from_mouse, to_mouse, as_vector=True)
        if not per_axis:
            return offset.length
        return (abs(int(offset[0])), abs(int(offset[1])))

    def finish(self, context) -> None:
        self.stop_draw(context)

    def cancel(self, context) -> None:
        self.stop_draw(context)

    def start_modal(self, context, event) -> Set[str]:
        print('use_realtime_update:', context.space_data.use_realtime_update)
        self._shift = False
        self._alt = False
        self._ctrl = False
        self.fake_confirm = False
        self.finished = False
        # Unchanged initial pos.
        self._mouse_init = self.get_mouse_region(event)
        self.mouse_init = self._mouse_init
        self.mouse_current = self._mouse_init
        self.displacing = False
        context.window_manager.modal_handler_add(self)

    def start_draw(self, context) -> None:
        context.area.tag_redraw()
        self.ctx_area = context.area
        self._draw_handler = context.space_data.draw_handler_add(self._draw, (context,), 'WINDOW', 'POST_PIXEL')

    def stop_draw(self, context) -> None:
        if hasattr(self, '_draw_handler') and self._draw_handler:
            context.area.tag_redraw()
            context.space_data.draw_handler_remove(self._draw_handler, 'WINDOW')
            # Blender BUG.
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.type = 'INFO'
                    area.type = 'VIEW_3D'
            self._draw_handler = None

    def _draw(self, context) -> None:
        if context.area != self.ctx_area:
            return
        self.overlay(context)

    def overlay(self, context) -> None:
        pass
