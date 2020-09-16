import bpy
from bpy.types import Operator
import bmesh
import mathutils
import math

if bpy.app.version >= (2, 90, 0):
    from . import function_wrapper_2_9 as function_wrapper
else:
    from . import function_wrapper_2_8 as function_wrapper

class Seams_To_SewingPattern(Operator):
    bl_idname = "object.seams_to_sewingpattern"
    bl_label = "Seams to Sewing Pattern"
    bl_description = "Converts a manifold mesh with seams into a swewing pattern for cloth simulation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        wm = bpy.context.window_manager
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')

        obj = bpy.context.edit_object
        me = obj.data

        bpy.ops.mesh.select_mode(type="EDGE")

        # select all seams

        bm = bmesh.from_edit_mesh(me)
        for e in bm.edges:
            if e.seam:
                e.select = True

        function_wrapper.do_bevel()

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
            
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.0)

        bpy.ops.mesh.select_all(action='SELECT') 
        bpy.ops.uv.select_all(action='SELECT')
        bmesh.update_edit_mesh(me, False)    

        uv_layer = bm.loops.layers.uv.active
        
        progress = 0
            
        for g in faceGroups:
            progress += 1
            wm.progress_update((progress / len(faceGroups)))
            previous_area = 0
            bpy.ops.mesh.select_mode(type='FACE')
            bpy.ops.mesh.select_all(action='DESELECT')
            average_position = mathutils.Vector((0,0,0))
            facenum = 0
            average_normal = mathutils.Vector((0,0,0))
            
            # calculate the area, average position, and average normal
            
            for f in g:
                f.select = True
                previous_area += f.calc_area()
                average_position += f.calc_center_median()
                average_normal += f.normal
                facenum += 1
                        
            average_normal.normalize()
            
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
            average_normal = average_normal.normalized()
            average_tangent = average_tangent.normalized()
            average_bitangent = average_bitangent.normalized()
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
            bpy.ops.transform.resize(value=(area_ratio, area_ratio, area_ratio))
            
        # done
            
        bmesh.update_edit_mesh(me, False)
        bpy.ops.mesh.select_all(action='SELECT') 

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        wm.progress_end()

        return{'FINISHED'}
