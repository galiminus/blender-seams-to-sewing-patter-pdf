import bpy
from collections import defaultdict
from bpy.types import Operator
import bmesh
import mathutils
import math
from bpy.props import (
        StringProperty,
        BoolProperty,
        IntProperty,
        FloatProperty,
        FloatVectorProperty,
        EnumProperty,
        )

if bpy.app.version >= (2, 90, 0):
    from . import function_wrapper_2_9 as function_wrapper
else:
    from . import function_wrapper_2_8 as function_wrapper

class Seams_To_SewingPattern(Operator):
    bl_idname = "object.seams_to_sewingpattern"
    bl_label = "Seams to Sewing Pattern"
    bl_description = "Converts a manifold mesh with seams into a swewing pattern for cloth simulation"
    bl_options = {'REGISTER', 'UNDO'}
    
    use_remesh: BoolProperty(
        name="Remesh",
        description="Use Boundary Aligned Remesh to remesh",
        default=True,
    )
    target_tris: IntProperty(
        name="Target number of triangles",
        description="Actual number of triangle migh be a bit off",
        default=5000,
    )
    do_calc_volume: BoolProperty(
        name="Calculate and store Volume",
        description="Calculate the mesh's volume and store in custom object data\nThis can be used in the clothsim's \"target volume\" property",
        default=True,
    )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=200)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "do_calc_volume")
        row = layout.row()
        row.prop(self, "use_remesh")
        row = layout.row()
        row.prop(self, "target_tris")
        row.enabled = self.use_remesh

    def execute(self, context):
        wm = bpy.context.window_manager
        bpy.ops.object.mode_set(mode='EDIT')


        obj = bpy.context.edit_object
        me = obj.data

        bpy.ops.mesh.select_mode(type="EDGE")

        bpy.ops.mesh.select_all(action='SELECT')
        #bpy.ops.uv.select_all(action='SELECT') ??
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.02)
        bpy.ops.mesh.select_all(action='DESELECT')

        bm = bmesh.from_edit_mesh(me)

        obj["S2S_InitialVolume"] = bm.calc_volume()

        bmesh.update_edit_mesh(me, False)

        #calculate edge length based on a surface of equilateral triangles
        
        if (self.use_remesh):
            current_area = sum(f.calc_area() for f in bm.faces)
            target_triangle_count = self.target_tris
            area_per_triangle = current_area / target_triangle_count

            max_edge_length = math.sqrt(area_per_triangle/(math.sqrt(3)/4))

            self.ensure_edgelength(max_edge_length * 0.8, bm, wm) #A bias to compensate for stretching


        for e in bm.edges:
            if e.seam:
                e.select = True

        function_wrapper.do_bevel()

        #fix fanning seams
        degenerate_edges = list()
        for f in list(filter(lambda f: (f.select), bm.faces)):
            is_degenerate = False
            for v in f.verts:
                vert_degenerate = True
                for e in v.link_edges:
                    if e.seam:
                        vert_degenerate = False
                if vert_degenerate:
                    is_degenerate = True

            if is_degenerate:
                for e in f.edges:
                    degenerate_edges.append(e)

        bmesh.ops.collapse(bm, edges = degenerate_edges, uvs = True)

        bpy.ops.mesh.delete(type='ONLY_FACE')

        bpy.ops.mesh.select_mode(type="FACE")
        faceGroups = []

        # isolate all face islands, and UV unwrap each island

        faces = set(bm.faces[:])
        wm.progress_begin(0, 99)
        progress_max = len(faces)
        progress = 0
        while faces:    
            bpy.ops.mesh.select_all(action='DESELECT')  
            face = faces.pop() 
            face.select = True
            bpy.ops.mesh.select_linked()
            selected_faces = {f for f in faces if f.select}
            selected_faces.add(face) # this or bm.faces above?
            faceGroups.append(selected_faces)
            faces -= selected_faces
            
            progress += len(selected_faces)
            wm.progress_update((progress / progress_max))

        uv_layer = bm.loops.layers.uv.active
        
        progress = 0

        avg_area_ratio = 0
            
        for g in faceGroups:
            progress += 1
            wm.progress_update((progress / len(faceGroups)))
            previous_area = 0
            bpy.ops.mesh.select_mode(type='FACE')
            bpy.ops.mesh.select_all(action='DESELECT')
            average_position = mathutils.Vector((0,0,0))
            facenum = 0
            
            # calculate the area, average position
            
            for f in g:
                f.select = True
                previous_area += f.calc_area()
                average_position += f.calc_center_median()
                facenum += 1
            
            average_position /= facenum

            average_tangent = mathutils.Vector((0,0,0))
            average_bitangent = mathutils.Vector((0,0,0))

            # calculate a rough tangent and a bitangent

            average_uv_position = mathutils.Vector((0,0))
            uv_position_samples = 0

            for face in g:
                for loop in face.loops:       
                    uv = loop[uv_layer].uv
                    uv_position_samples += 1
                    average_uv_position += uv
                    delta = loop.vert.co - average_position
                    average_tangent += delta * (uv.x - 0.5)
                    average_bitangent += delta * (uv.y - 0.5)
                    
            # reorient the tangent and bitangent
            
            average_uv_position /= uv_position_samples
            average_tangent = average_tangent.normalized()
            average_bitangent = average_bitangent.normalized()
            average_normal = average_tangent.cross(average_bitangent).normalized()
            halfvector = average_bitangent + average_tangent
            halfvector /= 2
            halfvector.normalize()
            #straighten out half vector
            halfvector = average_normal.cross(halfvector)
            halfvector = average_normal.cross(halfvector)
            cw = mathutils.Matrix.Rotation(math.radians(45.0), 4, average_normal)
            ccw = mathutils.Matrix.Rotation(math.radians(-45.0), 4, average_normal)
            
            average_tangent = mathutils.Vector(halfvector)
            average_tangent.rotate(ccw)
            
            average_bitangent = mathutils.Vector(halfvector)
            average_bitangent.rotate(cw)
            
            # offset each face island by their UV value, using the tangent and bitangent
                
            for face in g:
                for loop in face.loops:       
                    uv = loop[uv_layer].uv
                    vert = loop.vert
                    pos = mathutils.Vector((0,0,0))
                    pos += average_position
                    pos += average_tangent * -(uv.x - average_uv_position.x)
                    pos += average_bitangent * -(uv.y - average_uv_position.y)
                    pos += average_normal * 0.3 #arbitrary - should probably depend on object scale?
                    vert.co = pos;
            
            bmesh.update_edit_mesh(me, False)
            
            #resize to match previous area
            
            new_area = sum(f.calc_area() for f in g)
            
            area_ratio = previous_area / new_area
            area_ratio = math.sqrt(area_ratio)
            avg_area_ratio += area_ratio
            bpy.ops.transform.resize(value=(area_ratio, area_ratio, area_ratio))
            
        # done

        avg_area_ratio /= len(faceGroups)

        obj["S2S_UVtoWORLDscale"] = avg_area_ratio
            
        bmesh.update_edit_mesh(me, False)
        bpy.ops.mesh.select_all(action='SELECT') 

        if (self.use_remesh):
            bpy.ops.mesh.dissolve_limited(angle_limit=0.01)
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            bpy.ops.remesh.boundary_aligned_remesh(edge_length = max_edge_length, iterations = 10)

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        wm.progress_end()

        #fix 2.9 wm.progress problem
        bpy.context.window.cursor_set('NONE')
        bpy.context.window.cursor_set('DEFAULT')

        return{'FINISHED'}
    
    def ensure_edgelength(self, max_length, mesh, wm):
        seam_edges = list(filter(lambda e: e.seam, mesh.edges))
        edge_groups = defaultdict(list)
        for e in seam_edges:
            edge_groups[math.floor(e.calc_length() / max_length)].append(e)

        wm.progress_begin(0, 99)
        progress = 0;

        #A little weird, but by grouping the edges by number of required cuts,
        #subdivide_edges() can work a lot more effecient

        for eg in edge_groups.values():
            edge_length = eg[0].calc_length()
            wm.progress_update((progress / len(edge_groups)))
            bmesh.ops.subdivide_edges(mesh, edges=eg, cuts=math.floor(edge_length / max_length))

        bmesh.ops.triangulate(mesh, faces = mesh.faces, quad_method = 'BEAUTY', ngon_method = 'BEAUTY')
        #done

