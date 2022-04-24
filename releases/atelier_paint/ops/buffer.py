import bpy
from bpy.types import Operator
from bpy.props import IntProperty
import gpu
from mathutils import Matrix


tmp_draw_callback = None


class DrawReadTmpBuffer(Operator):
    bl_idname = 'atelierpaint.draw_read_tmp_buffer'
    bl_label = "Draw Read Temporal Buffer"

    width: IntProperty(default=0, options={'HIDDEN', 'SKIP_SAVE'})
    height: IntProperty(default=0, options={'HIDDEN', 'SKIP_SAVE'})

    @staticmethod
    def generate(context, width: int, height: int, draw_callback: callable):
        if width <= 0 or height <= 0:
            return

        global tmp_draw_callback
        tmp_draw_callback = draw_callback

        bpy.ops.wm.window_new(False)

        window = context.window_manager.windows[-1]
        area = window.screen.areas[0]
        area.type = 'VIEW_3D'
        region = None
        for reg in area.regions:
            if reg.type != 'WINDOW':
                continue
            region = reg
        ctx = {'window': window, 'area': area, 'region': region}

        bpy.ops.atelierpaint.draw_read_tmp_buffer(ctx, False, width=width, height=height)

        #bpy.ops.wm.window_close(ctx, False)

        return bpy.data.images.get('.tmp_offscreen_image', None)

    def execute(self, context):
        print("Start")
        #context.area.type = 'VIEW_3D'
        space = context.space_data
        overlay = space.overlay
        overlay.show_overlays = False
        width, height = self.width, self.height

        offscreen = gpu.types.GPUOffScreen(width, height)

        with offscreen.bind():
            fb = gpu.state.active_framebuffer_get()
            viewport_info = fb.viewport_get()
            print(viewport_info)
            with fb.bind():
                fb.clear(color=(0.0, 0.0, 0.0, 0.0))
                #with gpu.matrix.push_pop():
                    # reset matrices -> use normalized dvice coordinates [-1, 1]
                #    gpu.matrix.load_matrix(Matrix.Identity(4))
                #    gpu.matrix.load_projection_matrix(Matrix.Identity(4))y(4))

                global tmp_draw_callback
                tmp_draw_callback(width, height)

                buffer = fb.read_color(0, 0, width, height, 4, 0, 'FLOAT')
                buffer.dimensions = width * height * 4

            fb.clear()

        offscreen.free()

        image = bpy.data.images.get('.tmp_offscreen_image', None)
        if not image:
            image = bpy.data.images.new('.tmp_offscreen_image', width, height)
        else:
            image.scale(width, height)

        image.pixels.foreach_set(buffer)

        overlay.show_overlays = True

        bpy.ops.wm.window_close(False)

        print("End")
        return {'FINISHED'}
