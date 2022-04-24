import bpy

from .fill_shape import FillCircleShapeTool, FillRectShapeTool
from .fill_convex import FillConvexShapeTool
from .fill_draw import FillDrawShapeTool

from .px_paint import PixelPaintTool

def register():
    bpy.utils.register_tool(FillRectShapeTool, separator=True, group=True)
    bpy.utils.register_tool(FillCircleShapeTool, after={FillRectShapeTool.bl_idname})
    bpy.utils.register_tool(FillConvexShapeTool)
    bpy.utils.register_tool(FillDrawShapeTool)

    bpy.utils.register_tool(PixelPaintTool, separator=True)

def unregister():
    bpy.utils.unregister_tool(FillRectShapeTool)
    bpy.utils.unregister_tool(FillCircleShapeTool)
    bpy.utils.unregister_tool(FillConvexShapeTool)
    bpy.utils.unregister_tool(FillDrawShapeTool)
    
    bpy.utils.unregister_tool(PixelPaintTool)
