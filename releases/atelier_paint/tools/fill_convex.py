from atelier_paint.utils.math import distance_between
import bpy
from bpy.types import WorkSpaceTool
from bpy.types import Operator
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, EnumProperty
from mathutils.geometry import convex_hull_2d, delaunay_2d_cdt
from mathutils import Vector, Matrix

from atelier_paint.gpu.draw import *
from atelier_paint.utils import ImageUtils
from atelier_paint.ops import BasePaintToolOperator
from atelier_paint.utils.paint import PaintUtils


COL_BLUE = (11/255, 64/255, 238/255, 1)
COL_YELLOW = (255/255, 144/255, 0/255, 1)
COL_RED = (245/255, 50/255, 10/255, 1)

class ATELIERPAINT_OT_fill_convex(BasePaintToolOperator, Operator):
    bl_idname = 'atelierpaint.fill_convex'
    bl_label = "Fill Poly Shape"

    finish_on_mouse_release = False
    confirm_events = {'RET', 'LINE_FEED'}

    roundness: FloatProperty(name='Roundness', default=0.0, min=0.0, max=1.0, precision=2)
    color: FloatVectorProperty(name='Color', default=(1.0, 1.0, 1.0, 1.0), size=4, subtype='COLOR', min=0.0, max=1.0)

    def init(self, context) -> None:
        #self.color = PaintUtils.get_brush_setting(context, setting='color', default=(0.0, 0.0, 0.0, 1.0))
        #self.color = (*self.color, 1.0)
        ups = PaintUtils.get_unified_paint_settings(context)
        if ups.use_unified_color:
            self.color = (*ups.color, 1.0)
        #self.draw_args = {'color': self.color, 'shader': shader_2d_unif_corr}

        self.points = []
        self.verts = []
        self.indices = []
        self._ch_indices = set()
        #self.edges = []
        self.hovered_point = -1
        self.discard_point = False
        self.moving_point = False

    def on_shift_hold(self, context) -> None:
        pass

    def on_ctrl_hold(self, context) -> None:
        pass

    def on_ctrl_shift_hold(self, context) -> None:
        pass
    
    def on_x_press(self, context) -> None:
        if self.hovered_point == -1:
            return
        self.moving_point = False
        self.hovered_point = -1
        self.points.pop(self.hovered_point)
        self.update_geometry()

    def on_mouse_move(self, context, event, mouse) -> None:
        if self.moving_point and self.hovered_point != -1:
            self.points[self.hovered_point] = mouse
            self.update_geometry()

            if self.hovered_point not in self._ch_indices:
                self.discard_point = True
                return
            rel_point_co = self.get_mouse_image(context, self.points[self.hovered_point], normalized=True, clamp=False)
            #print(rel_point_co)
            if rel_point_co[0] < 0 or rel_point_co[0] > 1 or rel_point_co[1] < 0 or rel_point_co[1] > 1:
                self.discard_point = True
                return
            self.discard_point = False
            return

        for i, point in enumerate(self.points):
            if distance_between(point, mouse) < 10:
                self.hovered_point = i
                return
        self.hovered_point = -1

    def on_mouse_press(self, context, mouse) -> None:
        if self.hovered_point != -1:
            #print("Start moving point...")
            self.moving_point = True
        else:
            # Apply shape?
            # If mouse not returned from convex hull.
            # means it is not part of the convex shape.
            '''
            mouse_index = len(self.points)
            point_list = [*self.points, mouse]
            ch_indices = convex_hull_2d(point_list)
            if mouse_index not in ch_indices:
                self.fake_confirm = True

            else:
            '''
            # Add new point and start moving it.
            self.hovered_point = len(self.points)
            self.points.append(mouse)
            self.update_geometry()
            self.moving_point = True

    def on_mouse_release(self, context, mouse) -> None:
        if self.moving_point:
            #print("Stop moving point...")
            self.moving_point = False
            
            # Remove point if it is inside the convex shape.
            if self.hovered_point != -1 and self.discard_point:
                self.points.pop(self.hovered_point)
                self.update_geometry()
                self.discard_point = False

    def update_geometry(self):
        #print("Updating Geometry...")
        convex_hull_indices = convex_hull_2d(self.points)
        self.verts = [Vector(self.points[idx]) for idx in convex_hull_indices]
        self._ch_indices = set(convex_hull_indices)

        # Edges. (now it is not needed but maybe in future for outline drawing)
        '''
        loop_indices = [*self.indices, self.indices[0]]
        self.edges = []
        prev_loop_index = loop_indices[0]
        for idx in range(1, len(loop_indices)):
            self.edges.append((prev_loop_index, loop_indices[idx]))
            prev_loop_index = loop_indices[idx]
        '''

        '''
        :arg output_type: What output looks like. 0 => triangles with convex hull. "
        "1 => triangles inside constraints. "
        "2 => the input constraints, intersected. "
        "3 => like 2 but detect holes and omit them from output. "
        "4 => like 2 but with extra edges to make valid BMesh faces. "
        "5 => like 4 but detect holes and omit them from output.\n"
        '''
        delaunay = delaunay_2d_cdt(self.verts, [], [], 0, 0.01, False)
        if len(delaunay) < 3:
            self.indices = None
            return
        # verts, edges, faces, _ = delaunay
        self.indices = delaunay[2]

        #print(self.indices)
        #self.point_root = sum(self.points) / len(self.points)

    def confirm(self, context, mouse) -> None:
        min_x, min_y = 9999, 9999
        max_x, max_y = 0, 0
        for vert in self.verts:
            #vert = self.get_mouse_image()
            if vert.x <  min_x:
                min_x = vert.x
            if vert.x > max_x:
                max_x = vert.x
            if vert.y <  min_y:
                min_y = vert.y
            if vert.y > max_y:
                max_y = vert.y

        #print(
        #    ((min_x, min_y), self.get_mouse_image(context, (min_x, min_y))),
        #    ((max_x, max_y), self.get_mouse_image(context, (max_x, max_y)))
        #)

        # Avoid drawing the control points.
        if self.indices:
            self.points.clear()
            self.hovered_point = -1

        def draw_shape(rct, dim):
            #self.overlay(context)
            rel_verts = [Vector(self.get_mouse_image(context, vert_co)) for vert_co in self.verts]
            min_x = min(rel_verts, key = lambda co: co.x).x
            min_y = min(rel_verts, key = lambda co: co.y).y
            offset = Vector((min_x, min_y))
            rel_verts = [vert_co-offset for vert_co in rel_verts]
            Poly(rel_verts, self.indices, self.color, shader=shader_2d_unif_corr)

        ImageUtils.fill_from_offscreen(
            self.image,
            [
                *self.get_mouse_image(context, (min_x, min_y)),
                *self.get_mouse_image(context, (max_x, max_y))
            ],
            draw_callback=draw_shape,
            include_image=True,
            context=context,
            projection_matrix=Matrix((
                (0.00195, 0.0, 0.0, -0.9996),
                (0.0, 0.00195, 0.0, -0.9996),
                (0.0, 0.0, -0.01, -0.0),
                (0.0, 0.0, 0.0, 1.0)
            ))
        )

    def get_hovered_point(self):
        if self.hovered_point == -1 or self.hovered_point >= len(self.points):
            return None
        return self.points[self.hovered_point]

    def overlay(self, context) -> None:
        if self.indices:
            Poly(self.verts, self.indices, self.color, shader=shader_2d_unif_corr)
        else:
            Line(self.points, lt=2.0, color=self.color, shader=shader_2d_unif_corr)
        for idx, point in enumerate(self.points):
            #col = (1, .6, .2, 1) if idx in self._ch_indices else (0.2, 0.9, 0.6, .8)
            Text(point, 32, '•', (0.5, 1.5), color=COL_YELLOW)
        hov_point = self.get_hovered_point()
        if hov_point:
            color = COL_RED if self.discard_point else COL_BLUE
            Text(hov_point, 36, '•', (0.5, 1.5), color=color)


class FillConvexShapeTool(WorkSpaceTool):
    bl_space_type = 'IMAGE_EDITOR'
    bl_context_mode = 'PAINT' # default: 'All'

    # The prefix of the idname should be your add-on name.
    bl_idname = "atelier_paint.fill_convex_shape"
    bl_label = "Fill Convex Shape via points"
    bl_description = ("Place points to define a convex shape to fill that area with color")
    bl_icon = "ops.mesh.polybuild_hover"
    bl_cursor = 'DOT'
    #bl_data_block = 'BRUSH' # ('DEFAULT', 'NONE', 'WAIT', 'CROSSHAIR', 'MOVE_X', 'MOVE_Y', 'KNIFE', 'TEXT', 'PAINT_BRUSH', 'PAINT_CROSS', 'DOT', 'ERASER', 'HAND', 'SCROLL_X', 'SCROLL_Y', 'SCROLL_XY', 'EYEDROPPER', 'PICK_AREA', 'STOP', 'COPY', 'CROSS', 'MUTE', 'ZOOM_IN', 'ZOOM_OUT')'''
    bl_widget = None
    bl_operator = ATELIERPAINT_OT_fill_convex.bl_idname
    bl_keymap = (
        (ATELIERPAINT_OT_fill_convex.bl_idname, {"type": 'LEFTMOUSE', "value": 'PRESS'}, {}),
        (ATELIERPAINT_OT_fill_convex.bl_idname, {"type": 'LEFTMOUSE', "value": 'PRESS', "ctrl": True}, {}),
        (ATELIERPAINT_OT_fill_convex.bl_idname, {"type": 'LEFTMOUSE', "value": 'PRESS', "shift": True}, {}),
    )

    def draw_settings(context, layout, tool):
        props = tool.operator_properties(ATELIERPAINT_OT_fill_convex.bl_idname)
        
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
