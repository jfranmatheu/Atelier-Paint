from math import ceil, floor
from atelier_paint.gpu.draw import Grid, Rct
from atelier_paint.ops.base import BasePaintToolOperator
from atelier_paint.utils.image import ImageUtils
from atelier_paint.utils.math import clamp
from atelier_paint.utils.paint import PaintUtils
import bpy
from bpy.types import GizmoGroup, Gizmo, WorkSpaceTool, Operator
from mathutils import Vector
from bpy.props import FloatVectorProperty

global pixel_slot
global pixel_size
global img_reg_origin
pixel_slot = (-1, -1)
pixel_size = 1
img_reg_origin = Vector((0, 0))

class ATELIERPAINT_OT_px_paint(BasePaintToolOperator, Operator):
    bl_idname = 'atelierpaint.px_paint'
    bl_label = "Fill Shape"

    use_undo_hack = False
    use_gizmo = True

    color: FloatVectorProperty(name='Color', default=(1.0, 1.0, 1.0, 1.0), size=4, subtype='COLOR', min=0.0, max=1.0)

    def init(self, context) -> None:
        self.pixel_slots = set()

    def on_mouse_move(self, context, event, mouse) -> None:
        self.paint(context)

    def on_shift_hold(self, context) -> None:
        pass

    def on_ctrl_hold(self, context) -> None:
        pass

    def on_ctrl_shift_hold(self, context) -> None:
        pass

    def on_mouse_press(self, context, mouse) -> None:
        self.paint(context)

    def paint(self, context) -> None:
        global pixel_slot
        if pixel_slot in self.pixel_slots:
            return
        self.pixel_slots.add(pixel_slot)
        context.area.tag_redraw()

    def on_mouse_release(self, context, mouse) -> None:
        for slot in self.pixel_slots:
            ImageUtils.fill(
            self.image,
            (*slot, slot[0]+1, slot[1]+1),
            self.color,
            #context
        )
        ImageUtils.refresh(self.image, context)

    def overlay(self, context) -> None:
        global pixel_size
        global img_reg_origin
        origin = img_reg_origin
        size = pixel_size*2
        for slot in self.pixel_slots:
            x = origin.x + slot[0] * size
            y = origin.y + slot[1] * size
            Rct(
                [
                    x, y,
                    x+size, y+size
                ],
                self.color
            )


class PixelPaintWidget(Gizmo):
    bl_idname = "IMAGE_GT_pixel_paint"
    instances = {}

    @staticmethod
    def get(context):
        return PixelPaintWidget.instances.get(str(id(context.region)), None)

    def setup(self):
        #self.ratio = 1
        self.pixel_size = 1
        self.pos = (0, 0)
        self.px_indices = (0, 0)
        self.img_reg_size = Vector((0, 0))
        self.line_width = 1.0
        self.zoom = 1.0
        self.mp = (0, 0)
        bpy.context.space_data.zoom[0]

    def test_select(self, ctx, mp):
        if not ImageUtils.has_image(ctx):
            return -1
        self.mp = mp
        self.update_pixel_pos(ctx, mp)
        return -1

    def update_pixel_pos(self, ctx, pos):
        #region_size = Vector((ctx.region.width, ctx.region.height))
        image_size = Vector(ImageUtils.get_image_size(ctx))
        zoom = ctx.space_data.zoom[0]

        pos = Vector(pos)
        reg_origin = Vector(ImageUtils.project_to_region(ctx, (0, 0), clip=False, round_to_int=False))
        rel_pos = pos - reg_origin

        reg_image_size = Vector((image_size.x * zoom, image_size.y * zoom))
        image_ratio_x = reg_image_size.x / image_size.x
        image_ratio_y = reg_image_size.y / image_size.y

        px_indices = Vector((
            floor(rel_pos.x / image_ratio_x),
            floor(rel_pos.y / image_ratio_y)
        ))
        self.px_indices = px_indices
        global pixel_slot
        pixel_slot = (int(px_indices.x), int(px_indices.y))
        global img_reg_origin
        img_reg_origin = reg_origin

        pixel_size = self.pixel_size
        fixed_mp = (
            ceil(reg_origin[0] + (image_ratio_x * px_indices.x) + pixel_size),
            ceil(reg_origin[1] + (image_ratio_y * px_indices.y) + pixel_size)# + 1
        )

        self.pos = fixed_mp
        self.matrix_basis[0][3], self.matrix_basis[1][3] = fixed_mp[0], fixed_mp[1] # p_reg_origin[0], p_reg_origin[1]

    def update_pixel_size(self, ctx):
        #region_size = Vector((ctx.region.width, ctx.region.height))
        image_size = Vector(ImageUtils.get_image_size(ctx))
        zoom = ctx.space_data.zoom[0]

        if zoom == self.zoom:
            return

        view_width  = image_size.x * zoom
        #view_height = image_size.y * zoom
        reg_x0   = ImageUtils.project_to_region(ctx, (0, 0),           clip=False)[0]
        reg_x1   = ImageUtils.project_to_region(ctx, (1, 0),           clip=False)[0]

        # Calc pixel size.
        px_size = (reg_x1 - reg_x0) / view_width * zoom
        self.pixel_size = px_size/2
        global pixel_size
        pixel_size = self.pixel_size

        self.matrix_basis[0][0], self.matrix_basis[1][1] = self.pixel_size, self.pixel_size

        # Update Pixel Pos as zoom changed...
        self.zoom = zoom
        self.update_pixel_pos(ctx, self.mp)

    def draw(self, context):
        ups = PaintUtils.get_unified_paint_settings(context)
        #if ups.use_unified_color:
        self.color = ups.color
        self.update_pixel_size(context)
        image_size = ImageUtils.get_image_size(context)
        reg_origin = ImageUtils.project_to_region(context, (0, 0), clip=False)
        reg_max = ImageUtils.project_to_region(context, (1, 1), clip=False)

        self.draw_preset_box(self.matrix_basis, select_id=0)
        Grid([*reg_origin, *reg_max], (.1, .1, .1, .85), dimensions=image_size)



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
        self.widget.use_draw_modal = False
        self.widget.use_grab_cursor = False
        PixelPaintWidget.instances[str(id(context.region))] = self.widget

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
        props = tool.operator_properties(ATELIERPAINT_OT_px_paint.bl_idname)

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
