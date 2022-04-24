import numpy as np

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

class ATELIERPAINT_OT_fill_draw(BasePaintToolOperator, Operator):
    bl_idname = 'atelierpaint.fill_draw'
    bl_label = "Fill Draw Shape"
    
    finish_on_mouse_release = False

    color: FloatVectorProperty(name='Color', default=(1.0, 6.0, 2.0, 1.0), size=4, subtype='COLOR', min=0.0, max=1.0)

    def init(self, context) -> None:
        self.first_press = True
        self.first_release = True
        
        # WHAT.
        # context.space_data.use_realtime_update = True
        context.space_data.show_annotation = True
        self.verts = []
        self.faces = []

    def on_shift_hold(self, context) -> None:
        pass

    def on_ctrl_hold(self, context) -> None:
        pass

    def on_ctrl_shift_hold(self, context) -> None:
        pass

    def on_mouse_move(self, context, event, mouse) -> None:
        pass

    def on_mouse_press(self, context, mouse) -> None:
        print("Press")
        if self.first_press:
            self.first_press = False
            self.cleanup_gp(context)

    def on_mouse_release(self, context, mouse) -> None:
        if self.first_release:
            print("Release")
            #bpy.ops.gpencil.annotation_active_frame_delete(False)
            self.first_release = False
            
            print("Note start")
            bpy.ops.gpencil.annotate('INVOKE_DEFAULT', mode='DRAW', use_stabilizer=True, wait_for_input=False)
            print("Note end")
        else:
            print("DONE!")
            context.area.tag_redraw()
            self.fake_confirm = True

    def confirm(self, context, event) -> None:
        context.area.tag_redraw()

        verts, faces = self.get_verts_faces_from_gp_stroke(context, use_projected_coords=True)
        if not verts or not faces:
            return
        if len(verts) < 3 or len(faces) < 1:
            return
        min_x = min(verts, key = lambda co: co[0])[0]
        min_y = min(verts, key = lambda co: co[1])[1]
        max_x = max(verts, key = lambda co: co[0])[0]
        max_y = max(verts, key = lambda co: co[1])[1]

        def draw_shape(rct, dim):
            offset = (min_x, min_y)
            off_verts = [(co[0]-offset[0], co[1]-offset[1]) for co in verts]
            #self.overlay(context, use_projected_coords=True)
            Poly(off_verts, faces, self.color, shader=shader_2d_unif_corr)

        ImageUtils.fill_from_offscreen(
            self.image,
            [min_x, min_y, max_x, max_y],
            draw_shape,
            True,
            context,
            projection_matrix=Matrix((
                (0.00195, 0.0, 0.0, -0.9996),
                (0.0, 0.00195, 0.0, -0.9996),
                (0.0, 0.0, -0.01, -0.0),
                (0.0, 0.0, 0.0, 1.0)
            ))
        )
        self.cleanup_gp(context)

    def cleanup_gp(self, context):
        if not self.get_active_gp_stroke(context):
            return
        bpy.ops.gpencil.annotation_active_frame_delete(False)

    def get_active_gp_stroke(self, context):
        annotation = context.annotation_data
        if not annotation:
            return None
        layer = annotation.layers.active
        if not layer:
            return None
        frame = layer.active_frame
        if not frame:
            return None
        if not frame.strokes:
            return None
        for stroke in frame.strokes:
            if len(stroke.points) > 0:
                return stroke
        #if not frame.strokes[-1].points:
        #    return None
        return frame.strokes[-1]

    def get_verts_faces_from_gp_stroke(self, context, use_projected_coords: bool = False):
        stroke = self.get_active_gp_stroke(context)
        if not stroke:
            return None, None
        points, tris = stroke.points, stroke.triangles
        ori_verts = [p.co[:2] for p in points]
        loop_indices = [*range(0, len(ori_verts)), 0]
        ori_edges = []
        prev_loop_index = loop_indices[0]
        for idx in range(1, len(loop_indices)):
            ori_edges.append((prev_loop_index, loop_indices[idx]))
            prev_loop_index = loop_indices[idx]
        delaunay = delaunay_2d_cdt(ori_verts, ori_edges, [], 2, 0.001, False)
        if len(delaunay) < 3:
            return None, None
        view2d = context.region.view2d
        verts = delaunay[0]
        edges = delaunay[1]
        faces = delaunay[2] # [(t.v1, t.v2, t.v3) for t in tris]
        if len(faces) == 1:
            return None, None
            if len(faces[0]) % 3 == 0:
                faces = np.array(faces[0]).reshape((len(faces)/3, 3)).tolist()
        if use_projected_coords:
            verts = [self.get_mouse_image(context, view2d.view_to_region(*v, clip=True), clamp=True) for v in verts]
        else:
            verts = [view2d.view_to_region(*v, clip=True) for v in verts]
        return verts, faces

    def overlay(self, context, use_projected_coords: bool = False) -> None:
        verts, faces = self.get_verts_faces_from_gp_stroke(context)
        if not verts or not faces:
            return
        Poly(verts, faces, self.color, shader=shader_2d_unif_corr)


class FillDrawShapeTool(WorkSpaceTool):
    bl_space_type = 'IMAGE_EDITOR'
    bl_context_mode = 'PAINT' # default: 'All'

    # The prefix of the idname should be your add-on name.
    bl_idname = "atelier_paint.fill_draw_shape"
    bl_label = "Fill Your Drawing Shape"
    bl_description = ("Draw some shape and fill it with the chosen color")
    bl_icon = "brush.gpencil_draw.draw"
    bl_cursor = 'DOT'
    #bl_data_block = 'BRUSH' # ('DEFAULT', 'NONE', 'WAIT', 'CROSSHAIR', 'MOVE_X', 'MOVE_Y', 'KNIFE', 'TEXT', 'PAINT_BRUSH', 'PAINT_CROSS', 'DOT', 'ERASER', 'HAND', 'SCROLL_X', 'SCROLL_Y', 'SCROLL_XY', 'EYEDROPPER', 'PICK_AREA', 'STOP', 'COPY', 'CROSS', 'MUTE', 'ZOOM_IN', 'ZOOM_OUT')'''
    bl_widget = None
    bl_operator = ATELIERPAINT_OT_fill_draw.bl_idname
    bl_keymap = (
        (ATELIERPAINT_OT_fill_draw.bl_idname, {"type": 'LEFTMOUSE', "value": 'PRESS'}, {}),
        #(ATELIERPAINT_OT_fill_draw.bl_idname, {"type": 'LEFTMOUSE', "value": 'RELEASE'}, {}),
    )

    def draw_settings(context, layout, tool):
        props = tool.operator_properties(ATELIERPAINT_OT_fill_draw.bl_idname)

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
