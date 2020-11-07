import bpy
import bmesh
import random
import mathutils
from bpy.types import Operator
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
)

class FakeEdge:
  v1 = None
  v2 = None

class FakeVert:
  pos = None
  verts = None

class CleanUpEdges(bpy.types.Operator):
    """Clean up selected edges, for example after using the knife tool"""
    bl_idname = "mesh.clean_up_knife_cut"
    bl_label = "Clean up knife cut"
    bl_options = {'REGISTER', 'UNDO'}


    remove_poles_beforehand: BoolProperty(
        default=True
    )
    delimit_boundary: BoolProperty(
        default=True
    )
    delimit_existing_seams: BoolProperty(
        default=True
    )
    delimit_intersections: BoolProperty(
        default=True
    )

    min_length: FloatProperty(
        default=0.02,
        min=0,
        soft_max=0.5
    )

    relax_iterations: IntProperty(
        default=0,
        min=0,
        soft_max=20
    )

    neighbor_selection_radius: IntProperty(
        default=1,
        min=1,
        soft_max=20
    )

    neighbor_smooth_factor: FloatProperty(
        default=0.5,
        min=0,
        max=1
    )

    def execute(self, context):
        bpy.ops.mesh.select_mode(type="EDGE")


        obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(obj.data)

        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()


        if self.remove_poles_beforehand:
            selection = list(filter(lambda e: e.select, bm.edges))
            #clean up possible non-manifold mesh parts
            selected_verts = list(filter(lambda v: v.select, bm.verts))
            bpy.ops.mesh.select_more(use_face_step=True)
            neighboring_verts = list(filter(lambda v: v.select, bm.verts))
            bpy.ops.mesh.region_to_loop()
            boundary_verts = list(filter(lambda v: v.select, bm.verts))
            invalid_verts = list((set(neighboring_verts) - set(boundary_verts)) - set(selected_verts))
            bmesh.ops.dissolve_verts(bm, verts=invalid_verts)
            bpy.ops.mesh.select_all(action='DESELECT')
            for e in selection:
                e.select = True

        max_it = len(list(filter(lambda e: e.select, bm.edges)))
        edges = list(filter(lambda e: e.select, bm.edges))

        if self.delimit_intersections:
            for e in edges:
                for v in e.verts:
                    star_count = 0
                    for le in v.link_edges:
                        if le.select:
                            star_count += 1
                    if star_count > 2:
                        e.select = False
                        break

        if self.delimit_existing_seams:
            for e in edges:
                for v in e.verts:
                    for le in v.link_edges:
                        if le.seam and not (le in edges):
                            e.select = False
                            break


        if self.delimit_boundary:
            for e in edges:
                for v in e.verts:
                    if v.is_boundary:
                        e.select = False
                        break

        edges = list(filter(lambda e: e.select, bm.edges))

        fake_verts = dict()
        for e in edges:
            for v in e.verts:
                fake_vert = FakeVert()
                fake_vert = FakeVert()
                fake_vert.verts = []
                fake_vert.verts.append(v)
                fake_vert.pos = v.co
                fake_verts[v] = fake_vert

        fake_vert_list = []
        fake_vert_list.extend(fake_verts.values())
        for fv in fake_vert_list:
            print(fv)

        fake_edges = []
        for e in edges:
            fake_edge = FakeEdge()
            fake_edge.v1 = fake_verts[e.link_loops[0].vert]
            fake_edge.v2 = fake_verts[e.link_loops[0]. link_loop_next.vert]
            fake_edges.append(fake_edge)

        for _ in range(max_it):
            if (len(fake_edges) <= 1):
                break;
            shortest = min(fake_edges, key=lambda e: (e.v1.pos - e.v2.pos).length)
            if ((shortest.v1.pos - shortest.v2.pos).length < self.min_length):
                fake_vert_list.remove(shortest.v1)
                fake_vert_list.remove(shortest.v2)
                new_fake_vert = FakeVert()
                new_fake_vert.pos = (shortest.v1.pos + shortest.v2.pos)/2
                new_fake_vert.verts = []
                new_fake_vert.verts.extend(shortest.v1.verts)
                new_fake_vert.verts.extend(shortest.v2.verts)
                fake_vert_list.append(new_fake_vert)
                fake_edges.remove(shortest)
                for fe in fake_edges:
                    if (fe.v1 is shortest.v1):
                        fe.v1 = new_fake_vert
                    if (fe.v2 is shortest.v2):
                        fe.v2 = new_fake_vert
                    if (fe.v1 is shortest.v2):
                        fe.v1 = new_fake_vert
                    if (fe.v2 is shortest.v1):
                        fe.v2 = new_fake_vert

        for fv in fake_vert_list:
            for v in fv.verts:
                v.co = fv.pos

        fake_vert_list.clear()
        fake_edges.clear()
        fake_verts.clear()

        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        bm = bmesh.from_edit_mesh(bpy.context.active_object.data)

        print(len(edges))

        selection = list(filter(lambda e: e.select, bm.edges))

        for _ in range(self.relax_iterations):
            verts = list(filter(lambda v: v.select, bm.verts))
            locations = dict()
            for v in verts:
                locations[v] = v.co.copy()

            for v in verts:
                neighbors = []
                for l in v.link_loops:
                    if (l.edge.select):
                        neighbors.append(l.link_loop_next.vert)
                if (len(neighbors) == 2):
                    avg_pos = mathutils.Vector()
                    for n in neighbors:
                        avg_pos += locations[n]
                    avg_pos /= len(neighbors)
                    v.co = v.co.lerp(avg_pos, 0.2)

        for _ in range(self.neighbor_selection_radius):
            bpy.ops.mesh.select_more(use_face_step=True)

        if self.delimit_existing_seams:
            sel = list(filter(lambda e: e.select, bm.edges))
            for e in sel:
                if e.seam:
                    for v in e.verts:
                        v.select = False


        selected_verts = list(filter(lambda v: v.select, bm.verts))
        verts_to_smooth = []

        for v in selected_verts:
            if not(v.is_boundary and self.delimit_boundary):
                verts_to_smooth.append(v)

        print(len(verts_to_smooth))

        for e in selection:
            for v in e.verts:
                while v in verts_to_smooth:
                    verts_to_smooth.remove(v)

        smoothing_factor = self.neighbor_smooth_factor
        smoothing_factor = pow(smoothing_factor, 4)
        smoothing_factor /= 2

        for x in range(10):
            bmesh.ops.smooth_vert(bm, verts=verts_to_smooth, factor= smoothing_factor, use_axis_x=True, use_axis_y=True, use_axis_z=True)
            print("smooth")


        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)


        return {'FINISHED'}


