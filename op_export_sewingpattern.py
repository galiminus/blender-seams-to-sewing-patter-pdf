import bpy
from os.path import join, dirname
import shutil
import subprocess
from xml.sax.saxutils import escape
from bpy.props import (
    StringProperty,
    EnumProperty,
    IntProperty
)
import bmesh
import mathutils
import tempfile
import math

page_formats = {
    "Letter": (22.0, 28.0),
    "A6": (10.5, 14.8),
    "A5": (14.8, 21.0),
    "A4": (21.0, 29.7),
    "A3": (29.7, 42.0),
    "A2": (42.0, 59.4),
    "A1": (59.4, 84.1),
    "A0": (84.1, 118.9),
}

class Export_Sewingpattern(bpy.types.Operator):
    """Export Sewingpattern to .SVG or .PDF file format. This should be called after the Seams to Sewing Pattern operator"""

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
            ('PDF', "Portable Document Format (.pdf)", "Export the sewing pattern to a .PDF file with the given page size and overlap"),
            ('SVG', "Scalable Vector Graphic (.svg)", "Export the sewing pattern to a .SVG file"),
        ),
        name="Format",
        description="File format to export the UV layout to",
        default='PDF',
    )
    page_format: EnumProperty(
        items=(map(lambda page_format: (page_format, f'{page_format} page format', str(page_formats[page_format])), page_formats.keys())),
        name="PDF Pages format",
        description="Page format of the PDF file",
        default='A4',
    )

    page_overlap: IntProperty(
        name="PDF Pages overlap",
        default=50,
        min=0,
        subtype="PIXEL"
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
        
        if (self.alignment_markers == 'AUTO'):
            self.auto_detect_markers()

        try:
            working_directory = tempfile.TemporaryDirectory() 
            svg_ouput_filepath = join(working_directory.name, "output.svg")

            self.export(svg_ouput_filepath)

            if self.file_format == "SVG":
                shutil.move(svg_ouput_filepath, filepath)

            if self.file_format == "PDF":
                pdf_output_filepath = self.convert_svg_to_pdf(svg_ouput_filepath)
                shutil.move(pdf_output_filepath, filepath)

        finally:
            shutil.rmtree(working_directory.name)

        if is_editmode:
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        return {'FINISHED'}

    def convert_svg_to_pdf(self, svg_output_filepath, dpi = 96):
        working_directory = dirname(svg_output_filepath)

        page_width = math.ceil(page_formats[self.page_format][0] / 2.54 * dpi)
        page_height = math.ceil(page_formats[self.page_format][1] / 2.54 * dpi)

        # Convert the image to PNG and trim it
        png_output_filepath = join(working_directory, "output.png")

        self.run_convert([svg_output_filepath, "-trim", "+repage", png_output_filepath])

        # Get the resulting image dimensions
        pixel_width, pixel_height = self.run_identify(["-ping", "-format", "%w:%h", png_output_filepath]).split(':')

        page_width_with_overlap = page_width - self.page_overlap
        page_height_with_overlap = page_height - self.page_overlap

        pages_horizontal_count = math.ceil(float(pixel_width) / page_width_with_overlap)
        pages_vertical_count = math.ceil(float(pixel_height) / page_height_with_overlap)

        # Resize the image with enough room on both sides
        extended_width = (pages_horizontal_count + 1) * page_width_with_overlap
        extended_height = (pages_vertical_count + 1) * page_height_with_overlap

        self.run_convert([
            png_output_filepath,
            "-background", "white",
            "-compose", "Copy",
            "-extent", f'{extended_width}x{extended_height}',
            png_output_filepath
        ])

        # Crop and generate all the pages
        pages_filepaths = []
        for page_y in range(0, pages_vertical_count):
            for page_x in range(0, pages_horizontal_count):
                page_filepath = join(working_directory, f'page_{page_x + 1}_{page_y + 1}.png')

                x = page_x * page_width_with_overlap
                y = page_y * page_height_with_overlap

                # Crop the right part of the image, with the right overlap
                self.run_convert([
                    png_output_filepath,
                    "-crop", f'{page_width}x{page_height}+{x}+{y}',
                    "+repage",
                    page_filepath
                ])

                # Skip the page if it's all white, to save on paper
                if self.run_identify(["-format", "%[fx:100*mean]", page_filepath]) == "100":
                    continue

                # Add caption to the image to make them easier to sort
                self.run_convert([
                    page_filepath,
                    "-size", "140x",
                    "-pointsize", "18",
                    "-background", "black",
                    "-fill", "white",
                    f"caption: {page_x + 1} / {pages_horizontal_count} X {page_y + 1} / {pages_vertical_count}",
                    "-gravity", "center",
                    "-composite",
                    page_filepath
                ])

                pages_filepaths.append(page_filepath)

        pdf_output_filepath = join(working_directory, "output.pdf")

        self.run_convert(pages_filepaths + [ "-quality", "100", "-page", self.page_format, pdf_output_filepath ])

        return pdf_output_filepath
    
    def run_convert(self, args):
        print(args)

        completed = subprocess.run(["convert"] + args)
        print(completed)

    def run_identify(self, args):
        print(args)

        completed = subprocess.run(["identify"] + args, stdout=subprocess.PIPE)
        print(completed)

        return completed.stdout.decode("ascii")

    def export(self, filepath):
        #get loops:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="FACE")

        obj = bpy.context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        document_scale = 1000.0 #millimeter
        document_scale *= obj["S2S_UVtoWORLDscale"]

        svgstring = '<svg xmlns="http://www.w3.org/2000/svg"\n viewBox="0 0 ' + str(document_scale) + ' ' + str(document_scale) +'"\n'
        svgstring += 'width="' + str(document_scale) + 'mm" height="' + str(document_scale) + 'mm">'
        #svgstring += '<!-- Exported using the Seams to Sewing pattern for Blender  -->'
        svgstring += '\n<defs><style>.seam{stroke: #000; stroke-width:1px; fill:white} .sewinguide{stroke-width:1px;}</style></defs>'

        face_groups = []
        faces = set(bm.faces[:])
        while faces:
            bpy.ops.mesh.select_all(action='DESELECT')
            face = faces.pop()
            face.select = True
            bpy.ops.mesh.select_linked()
            selected_faces = {f for f in faces if f.select}
            selected_faces.add(face) # this or bm.faces above?
            face_groups.append(selected_faces)
            faces -= selected_faces

        print('Loop groups for sewing pattern export: ' + str(len(face_groups)))

        marker_indexes = {}

        for fg in face_groups:

            bpy.ops.mesh.select_all(action='DESELECT')
            for f in fg:
                f.select = True

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
            
            #print border

            svgstring += '\n<g>'
            svgstring += '<path class="seam" d="'

            for lg in loop_groups:
                if (len(lg) == 0):
                    continue
                lg.append(lg[0])

                svgstring += 'M '

                for l in lg:
                    uv = l[uv_layer].uv.copy()
                    svgstring += str(uv.x*document_scale)
                    svgstring += ','
                    svgstring += str((1-uv.y)*document_scale)
                    svgstring += ' '

            svgstring += '"/>'
            
            #print markers
            for lg in loop_groups:
                #markers
                if (self.alignment_markers != 'OFF'):
                    for l in lg:
                        has_wire = False
                        for w in l.vert.link_edges:
                            if w.is_wire and w.seam:
                                has_wire = True
                                svgstring += self.add_alignment_marker(l, w, uv_layer, document_scale, marker_indexes)

            svgstring += '</g>'

        svgstring += '\n</svg>'
        
        with open(filepath, "w") as file:
            file.write(svgstring)

        bpy.ops.object.mode_set(mode='OBJECT')
        
    def add_alignment_marker(self, loop, wire, uv_layer, document_scale, marker_indexes):
        wire_dir = mathutils.Vector((0,0));
        for l in loop.vert.link_edges:
            if (len(l.link_loops) > 0 and len(l.link_faces) == 1):
                this_dir = l.link_loops[0][uv_layer].uv - l.link_loops[0].link_loop_next[uv_layer].uv
                if (l.link_loops[0].vert == loop.vert):
                    wire_dir -= this_dir
                else:
                    wire_dir -= this_dir
        
        wire_dir.normalize()
        #wire_dir.y *= -1;
        wire_dir.xy = wire_dir.yx
        wire_dir *= -0.005 

        sew_color = mathutils.Color((1,0,0))
        color_hash = (hash(wire))
        color_hash /= 100000000.0
        color_hash *= 1345235.23523
        color_hash %= 1.0
        sew_color.hsv = color_hash, 1, 1
        sew_color_hex = "#%.2x%.2x%.2x" % (int(sew_color.r * 255), int(sew_color.g * 255), int(sew_color.b * 255))
        
        returnstring = '<path class="sewinguide" stroke="' + sew_color_hex + '" d="M '
        uv1 = loop[uv_layer].uv.copy();
        uv1.y = 1-uv1.y;
        returnstring += str((uv1.x + wire_dir.x) * document_scale)
        returnstring += ','
        returnstring += str((uv1.y + wire_dir.y) * document_scale)
        returnstring += ' '
    
        returnstring += str((uv1.x) * document_scale)
        returnstring += ','
        returnstring += str((uv1.y) * document_scale)
        returnstring += ' '
        returnstring += '"/>\n'  

        # Add here wire index text
        edge_index = self.get_edge_index(wire)
        if(edge_index in marker_indexes):
            wire_index = marker_indexes[edge_index]
        else:
            wire_index = len(marker_indexes)
            marker_indexes[edge_index] = wire_index
        
        anchor = ''
        if(uv1.x - wire_dir.x > uv1.x + wire_dir.x):
            anchor = 'text-anchor="end"'
        baseline = ''
        if(uv1.y + wire_dir.y > uv1.y - wire_dir.y):
            baseline = 'dominant-baseline="hanging"'
        returnstring += '<text x="'
        returnstring += str((uv1.x + wire_dir.x) * document_scale)
        returnstring += '" y="'
        returnstring += str((uv1.y + wire_dir.y) * document_scale)
        returnstring += '" class="sewinguidetext" ' + anchor + ' ' + baseline
        returnstring += ' font-size="' + str(int(0.008 * document_scale))+ 'px">'
        returnstring += str(wire_index)
        returnstring += '</text>\n'
        
        return returnstring

    # Get edge index. Edge positionned in a corned touch another wire edge.
    # So we get the minimal index of all edges in this corner.
    def get_edge_index(self, wire):

        def get_vert_wires(v):
            return [e for e in v.link_edges if e.is_wire and e.seam]

        def get_linked_edges(e):
            return get_vert_wires(e.verts[0]) + get_vert_wires(e.verts[1])

        def get_all_linked_edges(e, linked_edges):
            for e in get_linked_edges(e):
                if not e in linked_edges:
                    linked_edges.append(e)
                    get_all_linked_edges(e, linked_edges)

        min_index = wire.index
        all_linked_edges = []
        get_all_linked_edges(wire, all_linked_edges)
        for e in all_linked_edges:
            if(e.index < min_index):
                min_index = e.index

        return min_index
        
    def auto_detect_markers(self):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.select_all(action='SELECT')

        obj = bpy.context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        bpy.ops.mesh.region_to_loop()

        bpy.ops.mesh.select_mode(type="VERT")

        boundary_vertices = [v for v in bm.verts if v.select]

        for v in boundary_vertices:
            intrest = 0
            for e in v.link_edges:
                if (len(e.link_faces) != 0):
                    intrest += 1;
            if intrest == 2:
                for l in v.link_edges:
                    if (len(l.link_faces) == 0):
                        l.seam = True
        
    
