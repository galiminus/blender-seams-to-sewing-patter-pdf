import bpy
import bmesh

def do_bevel():
    bpy.ops.mesh.bevel(affect='EDGES', offset=0.0002)
