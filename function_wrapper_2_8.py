import bpy
import bmesh

def do_bevel():
    bpy.ops.mesh.bevel(vertex_only=False, offset=0.001)
