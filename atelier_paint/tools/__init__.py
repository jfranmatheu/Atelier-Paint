import bpy

from .fill_shape import FillRectShapeTool

def register():
    bpy.utils.register_tool(FillRectShapeTool, separator=True, group=True)

def unregister():
    bpy.utils.unregister_tool(FillRectShapeTool)
