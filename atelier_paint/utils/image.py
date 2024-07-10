from math import ceil, floor
from typing import List, Tuple
import numpy as np

from gpu_extras.presets import draw_circle_2d, draw_texture_2d
import bpy
import gpu
from mathutils import Matrix
from bpy.types import Event, Image

from atelier_paint.gpu import draw
from atelier_paint.utils.math import clamp


class ImageUtils:
    @staticmethod
    def has_image(context) -> None:
        return context.space_data.image is not None

    @staticmethod
    def get_image(context) -> Image:
        return context.space_data.image

    @staticmethod
    def get_image_size(context) -> Tuple[int, int]:
        return context.space_data.image.size

    @staticmethod
    def project_to_view(context, point: Tuple[int, int] or Event, invert: bool = False, return_relative: bool = False, round_to_int: bool = True) -> Tuple[int, int]:
        if isinstance(point, Event):
            point = (point.mouse_region_x, point.mouse_region_y)
        # This value is in range [0, 1].
        view_point = context.region.view2d.region_to_view(*point)
        if return_relative:
            return view_point
        # Transform [0, 1] relative to image coordinates to absolute [0, image_size].
        img_width, img_height = ImageUtils.get_image_size(context)
        if round_to_int:
            return (int(view_point[0]*img_width), int(view_point[1]*img_height))
        return (view_point[0]*img_width, view_point[1]*img_height)

    @staticmethod
    def project_to_region(context, point: Tuple[int, int], clip: bool = False, return_relative: bool = False, round_to_int: bool = True) -> Tuple[int, int] or Tuple[float, float]:
        reg_point = context.region.view2d.view_to_region(*point, clip=clip)
        if return_relative:
            return (reg_point[0]/context.region.width, reg_point[1]/context.region.height)
        if round_to_int:
            return (int(reg_point[0]), int(reg_point[1]))
        return reg_point

    @staticmethod
    def absolute_point(context, point: Tuple[int, int], clip: bool = False) -> Tuple[int, int]:
        img_width, img_height = ImageUtils.get_image_size(context)
        if clip:
            point = (clamp(point[0], clamp(point[1])))
        return (point[0]*img_width, point[1]*img_height)

    @staticmethod
    def relative_point(context, point: Tuple[int, int], clip: bool = False) -> Tuple[int, int]:
        img_width, img_height = ImageUtils.get_image_size(context)
        if clip:
            point = (clamp(point[0], 0, img_width), clamp(point[1], 0, img_height))
        return (point[0]/img_width, point[1]/img_height)

    @staticmethod
    def copy(from_image, to_image, selection: None or Tuple[int, int, int, int] = None, channels: str = 'RGBA', context=None) -> None:
        if channels == 'RGBA':
            from_channel, to_channel = 0, 4 # Full Copy.
        elif channels == 'A':
            from_channel, to_channel = 3, 4 # Copy Alpha.
        elif channels == 'RGB':
            from_channel, to_channel = 0, 3 # Copy RGB.
        elif channels == 'R':
            from_channel, to_channel = 0, 1 # Copy Red channel.
        elif channels == 'G':
            from_channel, to_channel = 1, 2 # Copy Green channel.
        elif channels == 'B':
            from_channel, to_channel = 2, 3 # Copy Blue channel.

        pixels_from = np.empty(shape=len(from_image.pixels), dtype=np.float32)
        from_image.pixels.foreach_get(pixels_from)
        pixels_to = np.empty(shape=len(from_image.pixels), dtype=np.float32)
        to_image.pixels.foreach_get(pixels_to)

        # all_channels = (channels == 'RGBA')
        # if all_channels: pixels = np.empty(shape=(len(image.pixels)/4, 4), dtype=np.float32)

        if selection:
            pixels_width = from_image.size[0] * 4 # Multiply per 4 channels (RGBA).
            Ax, Ay, Bx, By = selection
            from_x = min(Ax, Bx) * 4 # RGBA.
            to_x = max(Ax, Bx) * 4 #+ 4  # RGBA. # Includes last column. (right one)
            from_y = min(Ay, By)
            to_y = max(Ay, By) #+ 1 # Includes last row. (upper one)
            offset = from_y * pixels_width
            from_x += offset
            to_x += offset
            for _row in range(from_y, to_y):
                #if all_channels:
                pixels_to[from_x:to_x] = pixels_from[from_x:to_x]
                #else: pixels_to[from_x:to_x, from_channel:to_channel] = pixels_from[from_x:to_x, from_channel:to_channel]
                from_x += pixels_width
                to_x += pixels_width
        else:
            pixels_to[:, from_channel:to_channel] = pixels_from[:, from_channel:to_channel]

        to_image.pixels.foreach_set(pixels_to)
        ImageUtils.refresh(to_image, context)


    @staticmethod
    def fill(image, selection: Tuple[int, int, int, int], color: Tuple[float, float, float, float], context=None) -> None:
        rgba_pixel_count = len(image.pixels)
        pixels = np.empty(shape=rgba_pixel_count, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        pixels = pixels.reshape((int(rgba_pixel_count/4), 4))

        pixels_width = image.size[0] #* 4 # Multiply per 4 channels (RGBA).
        Ax, Ay, Bx, By = selection
        from_x = min(Ax, Bx)
        to_x = max(Ax, Bx) #* + 1 # Includes last column. (right one)
        from_y = min(Ay, By)
        to_y = max(Ay, By) #+ 1 # Includes last row. (upper one)
        offset = from_y * pixels_width
        from_x += offset
        to_x += offset

        color = np.array(list(color))
        for _row in range(from_y, to_y):
            pixels[from_x:to_x] = color
            from_x += pixels_width
            to_x += pixels_width

        # Return to a 1-D array with N pixel count (RGBA). [ pixel_1, pixel_2, ... pixel_N ].
        pixels = pixels.reshape(-1)
        image.pixels.foreach_set(pixels)
        if context:
            ImageUtils.refresh(image, context)


    @staticmethod
    def erase(image, origin: Tuple[int, int], radius: int, strength: float = 1.0, roundness: float = 1.0, blur: float = 0.0, context=None) -> None:
        # Shape to be [ (pixel_1), (pixel_2), ... (pixel_N) ].
        rgba_pixel_count = len(image.pixels)
        pixels = np.empty(shape=rgba_pixel_count, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        pixels = pixels.reshape((int(rgba_pixel_count/4), 4))

        pixels_width = image.size[0] #* 4 # Multiply per 4 channels (RGBA).
        from_y = (origin[1] - radius)
        from_x = (origin[0] - radius) #* 4 # RGBA.
        to_y = (origin[1] + radius) #+ 1 # Includes last row. (upper one)
        to_x = (origin[0] + radius) #+ 1 #* 4 + 4 # RGBA. # Includes last column. (right one)
        alpha = np.array([1.0-min(1.0, max(0.0, strength))])
        offset = from_y * pixels_width
        from_x += offset
        to_x += offset
        # if roundness == 0.0 and blur == 0.0:
        for _row in range(from_y, to_y):
            pixels[from_x:to_x,3:4] = alpha
            from_x += pixels_width
            to_x += pixels_width

        # Return to a 1-D array with N pixel count (RGBA). [ pixel_1, pixel_2, ... pixel_N ].
        pixels = pixels.reshape(-1)
        image.pixels.foreach_set(pixels)
        ImageUtils.refresh(image, context)


    @staticmethod
    def clear(image, context=None) -> None:
        pixels = np.zeros(shape=len(image.pixels), dtype=np.float32)
        #image.pixels.foreach_get(pixels)
        #pixels[3::4] = np.array([0.0])
        image.pixels.foreach_set(pixels)
        ImageUtils.refresh(image, context)


    @staticmethod
    def refresh(target_image, context = None) -> None:
        # NOTE: Blender is completely broken, at least seems that Image Editor is broken from the base.
        # And we can't perform update in any logical way possible:
        # [x] tag_redraw()
        # [x] redraw operator
        # [x] image.update()
        # [x] change image of the editor's space back and forth
        # So the only thing that works (by code) is changing the editor.
        # Thank u Blender devs :-) ♥
        context = context if context else bpy.context
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                image = area.spaces[0].image
                if image != target_image:
                    continue
                area.type = 'INFO'
                area.type = 'IMAGE_EDITOR'

    def fill_from_offscreen(image, selection: Tuple[int, int, int, int], draw_callback: callable, include_image: bool = True, context=None, projection_matrix: Matrix=Matrix.Identity(4), *args):
        Ax, Ay, Bx, By = selection
        min_x, max_x = int(min(Ax, Bx)), int(max(Ax, Bx))
        min_y, max_y = int(min(Ay, By)), int(max(Ay, By))
        WIDTH, HEIGHT = int(max_x-min_x), int(max_y-min_y)
        #print(WIDTH, HEIGHT)

        if WIDTH == 0 or HEIGHT == 0:
            return

        # get currently bound framebuffer
        framebuffer = gpu.state.active_framebuffer_get()
        framebuffer.bind()
        framebuffer.clear(color=(0.0, 0.0, 0.0, 0.0))

        # get information on current viewport
        ## viewport_info = gpu.state.viewport_get()
        ## width = viewport_info[2]
        ## height = viewport_info[3]
        
        width, height = image.size
        pixel_count = width * height
        #offscreen = gpu.types.GPUOffScreen(img_width, img_height)
        #with offscreen.bind():
        
        print("Viewport Size:", width, height)

        # Write copied data to image
        ######################################################
        # resize image obect to fit the current 3D View size
        ## framebuffer_image = bpy.data.images.new('FRAMEBUFFER', width, height, float_buffer=True)
        ## framebuffer_image.scale(width, height)

        with gpu.matrix.push_pop():
            gpu.matrix.load_matrix(Matrix.Identity(4))
            if include_image:
                draw_texture_2d(gpu.texture.from_image(image), (-0.3675, -0.3675), width, height)
                #draw.Image(gpu.texture.from_image(image), (0, 0), (width, height))
            draw_callback([min_x, min_y, max_x, max_y], (WIDTH, HEIGHT), *args)

        # obtain pixels from the framebuffer
        pixelBuffer = framebuffer.read_color(min_x, min_y, WIDTH, HEIGHT, 4, 0, 'FLOAT')
        ## pixelBuffer = framebuffer.read_color(0, 0, width, height, 4, 0, 'FLOAT')

        # write all pixels into the blender image
        pixelBuffer.dimensions = WIDTH * HEIGHT * 4
        ## pixelBuffer.dimensions = width * height * 4
        ## framebuffer_image.pixels.foreach_set(pixelBuffer)

        pixels_from = pixelBuffer

        # Read pixels.
        pixels_to = np.empty(shape=(pixel_count*4), dtype=np.float32)
        image.pixels.foreach_get(pixels_to)


        """
        img_width, img_height = image.size
        offscreen = gpu.types.GPUOffScreen(img_width, img_height)

        with offscreen.bind():

            fb = gpu.state.active_framebuffer_get()
            fb.bind()
            gpu.state.viewport_set(0, 0, img_width, img_height)
            #fb.viewport_set(0, 0, img_width, img_height)
            fb.clear(color=(0.0, 0.0, 0.0, 0.0))
            #gpu.matrix.reset()

            with gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
                gpu.matrix.load_matrix(Matrix.Identity(4))
                #print(gpu.matrix.get_projection_matrix())
                #R = ratio/1000
                if projection_matrix:
                    gpu.matrix.load_projection_matrix(projection_matrix)
                #gpu.matrix.translate((0, 0))
                #gpu.matrix.scale((1.0, 1.0))

                if include_image:
                    #draw_texture_2d(gpu.texture.from_image(image), (-min_x, -min_y), img_width, img_height)
                    draw.Image(gpu.texture.from_image(image), (-min_x, -min_y), (img_width, img_height))
                draw_callback([0, 0, WIDTH, HEIGHT], (WIDTH, HEIGHT), *args)

            buffer = fb.read_color(0, 0, WIDTH, HEIGHT, 4, 0, 'FLOAT') # 'UBYTE')
            buffer.dimensions = WIDTH * HEIGHT * 4

            '''
            # get currently bound framebuffer
            framebuffer = gpu.state.active_framebuffer_get()

            # get information on current viewport
            viewport_info = gpu.state.viewport_get()
            width = viewport_info[2]
            height = viewport_info[3]

            offscreen = gpu.types.GPUOffScreen(width, height)

            print("Viewport Size:", width, height)

            with gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
                gpu.matrix.load_matrix(Matrix.Identity(4))
                if projection_matrix:
                    gpu.matrix.load_projection_matrix(projection_matrix)
                if include_image:
                    #draw_texture_2d(gpu.texture.from_image(image), (-min_x, -min_y), img_width, img_height)
                    draw.Image(gpu.texture.from_image(image), (0, 0), (width, height))
                draw_callback([min_x, min_y, max_x, max_y], (WIDTH, HEIGHT), *args)

            # Write copied data to image
            ######################################################
            # resize image obect to fit the current 3D View size
            #framebuffer_image.scale(self.width, self.height)

            buffer = framebuffer.read_color(min_x, min_y, WIDTH, HEIGHT, 4, 0, 'FLOAT') # 'UBYTE')
            buffer.dimensions = WIDTH * HEIGHT * 4
            '''

        offscreen.free()

        pixels_from = buffer
        #pixels_from = np.array(buffer, dtype=np.float32) # buffer #np.empty(shape=len(image.pixels), dtype=np.float32)
        # Color Correct
        #pixels_from = np.power(buffer, .454545)

        # Read pixels.
        pixel_count = image.size[0] * image.size[1]
        pixels_to = np.empty(shape=(pixel_count*4), dtype=np.float32)
        image.pixels.foreach_get(pixels_to)
        """

        """
        # METHOD WITHOUT DRAWING IMAGE...
        # Read pixels.
        pixels_to = np.empty(shape=(pixel_count*4), dtype=np.float32)
        image.pixels.foreach_get(pixels_to)

        # Create array with required shape.
        pixels_from = np.array(pixels_from, dtype=np.float32).reshape((width, height, 4)) # WIDTH, HEIGHT
        pixels_to   = pixels_to.reshape((width, height, 4))

        # Slice based on selection.
        srcRGBA = pixels_from
        dstRGBA = pixels_to # [min_x:max_x, min_y:max_y]

        # Extract the RGB channels
        srcRGB = srcRGBA[...,:3] # Source.
        dstRGB = dstRGBA[...,:3]   # Destination.

        # Extract the alpha channels and normalise to range [0, 1]
        srcA = srcRGBA[...,3]
        dstA = dstRGBA[...,3]

        # Work out resultant alpha channel
        outA = srcA + dstA*(1-srcA)

        # Work out resultant RGB
        outRGB = (srcRGB*srcA[...,np.newaxis] + dstRGB*dstA[...,np.newaxis]*(1-srcA[...,np.newaxis])) / outA[...,np.newaxis]


        #print(outRGB)

        # Merge RGB and alpha back into single image
        outRGBA = np.dstack((outRGB,outA)).astype(np.float32)
        #outRGB = outRGB.reshape((WIDTH, HEIGHT, 3))
        #outA   = outA.reshape((WIDTH, HEIGHT, 1))
        #outRGBA = np.concatenate((outRGB, outA), axis=2) # TWO dimensional array.

        # Merge selection to the image.
        ## pixels_to[min_x:max_x, min_y:max_y] = outRGBA[:]
        ## pixels_to = pixels_to.reshape(-1)
        pixels_to = outRGBA.reshape(-1)
        pixels_to = np.power(pixels_to, .4545)
        """

        
        # Iterator props for Original Image.
        i_pixels_width = image.size[0] * 4 # Multiply per 4 channels (RGBA).
        i_from_x = min_x * 4 # RGBA.
        i_to_x = max_x * 4 # RGBA.
        i_from_y = min_y
        i_to_y = max_y
        i_offset = i_from_y * i_pixels_width
        i_from_x += i_offset
        i_to_x += i_offset

        # Iterator props for Overlay Shape.
        s_pixels_width = WIDTH * 4
        s_from_x = 0
        #s_from_y = 0
        s_to_x = s_pixels_width
        #s_to_y = max_y

        for _row in range(i_from_y, i_to_y):
            pixels_to[i_from_x:i_to_x] = pixels_from[s_from_x:s_to_x]
            # This is when the pixels_from and pixels_to buffers have identical shapes.
            #pixels_to[i_from_x:i_to_x] = pixels_from[i_from_x:i_to_x]
            i_from_x += i_pixels_width
            i_to_x   += i_pixels_width
            s_from_x += s_pixels_width
            s_to_x   += s_pixels_width
        

        image.pixels.foreach_set(pixels_to)
        ImageUtils.refresh(image, context)
        

        ''' JUST FOR DEBUG. '''
        '''
        IMAGE_NAME = "Generated Image"
        if not IMAGE_NAME in bpy.data.images:
            image = bpy.data.images.new(IMAGE_NAME, WIDTH, HEIGHT)
        else:
            image = bpy.data.images[IMAGE_NAME]
            image.scale(WIDTH, HEIGHT)
        image.pixels.foreach_set(buffer)
        #image.pixels = [v / 255 for v in buffer]
        '''
