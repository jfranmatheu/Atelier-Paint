from math import floor
from atelier_paint.ops.base import BasePaintToolOperator
from atelier_paint.utils.image import ImageUtils
from atelier_paint.utils.math import clamp
import bpy
from bpy.types import GizmoGroup, Gizmo, WorkSpaceTool, Operator
from mathutils import Vector
from bpy.props import FloatVectorProperty


class ATELIERPAINT_OT_px_paint(BasePaintToolOperator, Operator):
    bl_idname = 'atelierpaint.px_paint'
    bl_label = "Fill Shape"

    color: FloatVectorProperty(name='Color', default=(1.0, 1.0, 1.0, 1.0), size=4, subtype='COLOR', min=0.0, max=1.0)

    def init(self, context) -> None:
        pass

    def on_mouse_move(self, context, event, mouse) -> None:
        pass

    def on_shift_hold(self, context) -> None:
        pass

    def on_ctrl_hold(self, context) -> None:
        pass

    def on_ctrl_shift_hold(self, context) -> None:
        pass

    def on_mouse_release(self, context, mouse) -> None:
        pass

    def overlay(self, context) -> None:
        pass


class PixelPaintWidget(Gizmo):
    bl_idname = "IMAGE_GT_pixel_paint"

    def setup(self):
        self.ratio = 1
        self.size = 1
        self.pos = (0, 0)
        self.line_width = 1.0

    def test_select(self, ctx, mp):
        if not ImageUtils.has_image(ctx):
            return -1

        # Divide space per number of slots/pixels availables.
        region = ctx.region
        region_size = Vector((region.width, region.height))
        image_size = Vector(ImageUtils.get_image_size(ctx))
        zoom = ctx.space_data.zoom[0]

        cur_pos = Vector(mp)
        origin = Vector(ImageUtils.project_point(ctx, (0, 0), invert=True))
        rel_cur_pos = cur_pos - origin

        reg_image_size = Vector((image_size.x * zoom, image_size.y * zoom))
        
        print("Reg Image Size:", reg_image_size)

        image_ratio_x = reg_image_size.x / image_size.x
        image_ratio_y = reg_image_size.y / image_size.y

        print("Origin:", origin)
        print("Image Ratio:", image_ratio_x, image_ratio_y)

        pixel_size = self.size # reg_image_size.x * self.ratio * zoom
        print("Pixel Size:", pixel_size)
        print(floor(rel_cur_pos[0]/image_ratio_x))
        px_indices = (
            floor(rel_cur_pos[0]/image_ratio_x),
            floor(rel_cur_pos[1]/image_ratio_y)
        )
        
        mp = (
            origin[0] + floor(image_ratio_x * px_indices[0]) + pixel_size,
            origin[1] + floor(image_ratio_y * px_indices[1]) + pixel_size
        )

        print("Mouse:", rel_cur_pos)
        print("Fixed Pos:", mp)
        self.matrix_basis[0][3], self.matrix_basis[1][3] = floor(mp[0]), floor(mp[1]) # p_reg_origin[0], p_reg_origin[1]
        return -1

    def update_pixel_size(self, ctx):
        region = ctx.region
        region_size = Vector((region.width, region.height))
        image_size = Vector(ImageUtils.get_image_size(ctx))
        zoom = ctx.space_data.zoom[0]

        p_view_origin = Vector(ImageUtils.project_point(ctx, (0, 0))) #, return_relative=True)) #, invert=True)
        p_view_origin_plus = Vector(ImageUtils.project_point(ctx, (1, 0)))#, return_relative=True)) #, invert=True)
        p_view_max_x = Vector(ImageUtils.project_point(ctx, (image_size.x, 0)))#, return_relative=True))

        # Image is left-outside the region.x if view_origin.x is > 0:
        x_holdout = p_view_origin.x > 0
        # Image is Downwards the region.y if view_origin.y is > 0:
        y_holdout = p_view_origin.y > 0

        p_reg_origin = p_view_origin #* zoom #* 1000
        p_reg_origin_plus = p_view_origin_plus #* zoom #* 1000
        p_reg_max_x = p_view_max_x #* zoom

        image_reg_unit = abs(p_reg_origin_plus.x) - abs(p_reg_origin.x)
        image_reg_width = abs(p_reg_max_x.x) - abs(p_reg_origin.x)
        #p_reg_origin = (int(abs(p_reg_origin[0])), int(abs(p_reg_origin[1])))

        ratio = image_reg_unit / image_reg_width
        pixel_size = max(1, ratio * (image_size.x * zoom/2))

        self.ratio = ratio
        self.size = pixel_size

        #print(p_reg_origin, p_reg_origin_plus, p_reg_max_x)
        #print(image_reg_unit)
        #print(image_reg_width)
        print(ratio)
        print(pixel_size)
        self.matrix_basis[0][0], self.matrix_basis[1][1] = pixel_size, pixel_size

    def draw(self, context):
        #zoom = context.space_data.zoom[0]
        #self.matrix_basis[0][0], self.matrix_basis[1][1] = zoom*1.5, zoom*1.5
        self.update_pixel_size(context)

        self.draw_preset_box(self.matrix_basis, select_id=0)


class PixelPaintWidgetGroup(GizmoGroup):
    bl_idname = "IMAGE_GGT_pixel_paint"
    bl_label = "Pixel Paint Widget"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'WINDOW'
    #bl_options = {'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        return context.space_data.image is not None and context.space_data.ui_mode == 'PAINT'

    def setup(self, context):
        self.widget = self.gizmos.new(PixelPaintWidget.bl_idname)

    def refresh(self, context):
        pass


class PixelPaintTool(WorkSpaceTool):
    bl_space_type = 'IMAGE_EDITOR'
    bl_context_mode = 'PAINT' # default: 'All'

    # The prefix of the idname should be your add-on name.
    bl_idname = "atelier_paint.px_paint"
    bl_label = "Pixel Paint"
    bl_description = "Paint a pixel"
    bl_icon = "ops.gpencil.draw"
    bl_cursor = 'DOT'
    #bl_data_block = 'BRUSH' # ('DEFAULT', 'NONE', 'WAIT', 'CROSSHAIR', 'MOVE_X', 'MOVE_Y', 'KNIFE', 'TEXT', 'PAINT_BRUSH', 'PAINT_CROSS', 'DOT', 'ERASER', 'HAND', 'SCROLL_X', 'SCROLL_Y', 'SCROLL_XY', 'EYEDROPPER', 'PICK_AREA', 'STOP', 'COPY', 'CROSS', 'MUTE', 'ZOOM_IN', 'ZOOM_OUT')'''
    bl_widget = PixelPaintWidgetGroup.bl_idname
    bl_operator = ATELIERPAINT_OT_px_paint.bl_idname
    bl_keymap = (
        (ATELIERPAINT_OT_px_paint.bl_idname, {"type": 'LEFTMOUSE', "value": 'PRESS'}, {}),
    )

    def draw_settings(context, layout, tool):
        pass
