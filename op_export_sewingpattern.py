import bpy
from os.path import basename
from xml.sax.saxutils import escape
from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
    IntVectorProperty,
    FloatProperty,
)

class Export_Sewingpattern(bpy.types.Operator):
    """Export Sewingpattern"""

    bl_idname = "object.export_sewingpattern"
    bl_label = "Export Sewing Pattern"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(
        subtype='FILE_PATH',
    )
    alignment_markers: EnumProperty(
        items=(
            ('OFF', "Off",
             "No alignment markers"),
            ('SEAM', "Marked as seam",
             "Use sewing edges manually marked as seam"),
            ('AUTO', "Autodetect + seam",
             "Finds sewing edges of corners automatically and marks them as seam"),
        ),
        name="Alignment markers",
        description="Exports matching colored lines on the borders of sewing patterns to assist with alignment",
        default='AUTO',
    )
    file_format: EnumProperty(
        items=(
            ('SVG', "Scalable Vector Graphic (.svg)",
             "Export the sewing pattern to a .SVG file"),
            ('PNG', "PNG Image (.png)",
             "Export the sewing pattern to a .PNG file")
        ),
        name="Format",
        description="File format to export the UV layout to",
        default='SVG',
    )
    size: IntVectorProperty(
        size=2,
        default=(1024, 1024),
        min=8, max=32768,
        description="Dimensions of the exported file",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.data.uv_layers

    def invoke(self, context, event):
        #stuff to check / set before goes here :)
        self.filepath = self.get_default_file_name(context) + "." + self.file_format.lower()
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def get_default_file_name(self, context):
        return context.active_object.name

    def check(self, context):
        if any(self.filepath.endswith(ext) for ext in (".png", ".eps", ".svg")):
            self.filepath = self.filepath[:-4]

        ext = "." + self.file_format.lower()
        self.filepath = bpy.path.ensure_ext(self.filepath, ext)
        return True

    def execute(self, context):
        obj = context.active_object
        is_editmode = (obj.mode == 'EDIT')
        if is_editmode:
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, "." + self.mode.lower())
        
        #todo: data

        export(filepath, data, self.size[0], self.size[1])

        if is_editmode:
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        return {'FINISHED'}
