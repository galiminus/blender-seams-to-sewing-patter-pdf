import bpy
import bmesh
import random
from bpy.types import Operator
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
)


class ObjectModeOperator:
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

class CleanUpEdges(bpy.types.Operator):
    """Clean up selected edges, for example after using the knife tool"""
    bl_idname = "mesh.clean_up_edges"
    bl_label = "Clean up edges"
    bl_options = {'REGISTER', 'UNDO'}

    loop_relax_it: EnumProperty(
        name="Relax Iterations",
        items=(("1", "1", "One"),
               ("3", "3", "Three"),
               ("5", "5", "Five"),
               ("10", "10", "Ten"),
              ("25", "25", "Twenty-five")),
        description="Number of times the loop is relaxed",
        default="1"
        )

    relax_size: IntProperty(
        name="Smooth vertex neighbor size:",
        description="After the seam has been relaxed, neighboring vertices are smoothed.",
        default=1,
        min=0,
        soft_max=5
    )

    min_length: FloatProperty(
        name="Minimum Edge Length",
        description="Collapse edges under this length",
        default=0.002,
        min=0,
        soft_max=0.1
    )

    def execute(self, context):

        obj = bpy.context.edit_object
        me = obj.data
        mesh = bmesh.from_edit_mesh(me)


        seam_edges = list(filter(lambda e: e.seam, mesh.edges))
        to_relax = []
        for e in seam_edges:
            is_star = False
            for v in e.verts:
                if v.is_boundary:
                    is_star = True
                star_count = 0
                for ce in v.link_edges:
                    if ce.seam:
                        star_count += 1
                if star_count > 2:
                    is_star = True
            if not is_star:
                to_relax.append(e)

        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
        bpy.ops.mesh.select_all(action='DESELECT')

        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT', action='DISABLE')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE', action='DISABLE')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE', action='ENABLE')
        bpy.ops.mesh.select_all(action='DESELECT')

        for e in to_relax:
            e.select = True;

        bpy.ops.mesh.looptools_relax(regular=False, iterations=self.loop_relax_it, interpolation='cubic') #todo: detect
        bpy.ops.mesh.dissolve_degenerate(threshold=self.min_length)

        bmesh.update_edit_mesh(me)
        mesh = bmesh.from_edit_mesh(me)



        if (self.relax_size > 0):

            selected_edges = list(filter(lambda e: e.select, mesh.edges))

            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE', action='DISABLE')
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT', action='ENABLE')

            for x in range(self.relax_size):
                bpy.ops.mesh.select_more(use_face_step=False)


            for e in selected_edges:
                for v in e.verts:
                    v.select = False;

            selected_verts = list(filter(lambda v: v.select, mesh.verts))
            for v in selected_verts:
                if v.is_boundary:
                    v.select = False

            bpy.ops.mesh.vertices_smooth(factor=0.2, repeat=10)
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
            bpy.ops.mesh.select_all(action='DESELECT')

        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE', action='ENABLE')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT', action='DISABLE')

        bmesh.update_edit_mesh(me)
        mesh = bmesh.from_edit_mesh(me)


        '''
        for x in range(self.iterations):

            seam_edges = list(filter(lambda e: e.seam, mesh.edges))

            samples = int(len(seam_edges) / self.iterations)
            samples *= 2
            sublist = random.sample(seam_edges, int(samples))
            toremove = []
            for e in sublist:
                if e.calc_length() < self.min_length:
                    is_star = False
                    for v in e.verts:
                        if v.is_boundary:
                            is_star = True
                        star_count = 0
                        for ce in v.link_edges:
                            if ce.seam:
                                star_count += 1
                        if star_count > 2:
                            is_star = True
                    if not is_star:
                        toremove.append(e)

            if (len(toremove) > 0):
                bmesh.ops.collapse(mesh, edges = toremove, uvs = True)

        bmesh.update_edit_mesh(me)
        mesh = bmesh.from_edit_mesh(me)
        '''
        '''
        if self.use_dissolve:
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT', action='DISABLE')
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE', action='DISABLE')
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE', action='ENABLE')
            bpy.ops.mesh.select_all(action='DESELECT')
            seam_edges = list(filter(lambda e: e.seam, mesh.edges))
            for e in seam_edges:
                e.select = True;

            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE', action='DISABLE')
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT', action='ENABLE')

            bpy.ops.mesh.select_more(use_face_step=False)

            for e in seam_edges:
                for v in e.verts:
                        v.select = False;

            bpy.ops.mesh.dissolve_limited(angle_limit=0.6, use_dissolve_boundaries=False, delimit={'SEAM'})
            bmesh.update_edit_mesh(me)
            mesh = bmesh.from_edit_mesh(me)
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT', action='DISABLE')
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE', action='ENABLE')
            bpy.ops.mesh.select_all(action='DESELECT')

            for e in seam_edges:
                for f in e.link_faces:
                        f.select = True;

            bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
            bpy.ops.mesh.tris_convert_to_quads(face_threshold=0.698132, shape_threshold=0.698132, uvs=True, vcols=False, seam=True, sharp=True, materials=True)

        '''

        #bpy.ops.mesh.select_all(action='DESELECT')

        return {'FINISHED'}


