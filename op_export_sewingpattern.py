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
import bmesh
import mathutils
import random

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
        filepath = bpy.path.ensure_ext(filepath, "." + self.file_format.lower())
        
        #todo: data

        self.export(filepath)

        if is_editmode:
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        return {'FINISHED'}
    
    def export(self, filepath):
        svgstring = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + str(self.size[0]) + ' ' + str(self.size[1]) +'">'
        #svgstring += '<!-- Exported using the Seams to Sewing pattern for Blender  -->'
        svgstring += '\n<defs><style>.seam{stroke: #000; stroke-width:1px; fill:white} .sewinguide{stroke-width:0.1px;}</style></defs>'
        
        #get loops:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.select_all(action='SELECT')

        obj = bpy.context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        bpy.ops.mesh.region_to_loop()

        boundary_loop = [e for e in bm.edges if e.select]

        relevant_loops=[]

        for e in boundary_loop:
            relevant_loops.append(e.link_loops[0])
    
        loop_groups = [[]]
        
        while (len(relevant_loops) > 0):
            temp_group = [relevant_loops[0]]
            vertex_to_match = relevant_loops[0].link_loop_next.vert
            relevant_loops.remove(relevant_loops[0])
            match = True
            while(match == True):
                match = False
                for x in range(0, len(relevant_loops)):
                    if (relevant_loops[x].link_loop_next.vert == vertex_to_match):
                        temp_group.append(relevant_loops[x])
                        vertex_to_match = relevant_loops[x].vert
                        relevant_loops.remove(relevant_loops[x])
                        match = True
                        break
                    if (relevant_loops[x].vert == vertex_to_match):
                        temp_group.append(relevant_loops[x])
                        vertex_to_match = relevant_loops[x].link_loop_next.vert
                        relevant_loops.remove(relevant_loops[x])
                        match = True
                        break
            loop_groups.append(temp_group)
            
        uv_layer = bm.loops.layers.uv.active   

        for lg in loop_groups:
            if (len(lg) == 0):
                continue
            lg.append(lg[0])
            svgstring += '\n<g>' 
            svgstring += '<path class="seam" d="M ' 
            for l in lg:
                uv = l[uv_layer].uv.copy()
                svgstring += str(uv.x*self.size[0])
                svgstring += ','
                svgstring += str(uv.y*self.size[1])
                svgstring += ' '
            svgstring += '"/></g>'
        
        svgstring += '\n</svg>'
        
        with open(filepath, "w") as file:
            file.write(svgstring)
            
        bpy.ops.object.mode_set(mode='OBJECT')
        
        
