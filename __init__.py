bl_info = {
        'name': 'Seams to Sewing Pattern',
        'author': 'Thomas Kole',
        'version': (0, 6),
        'blender': (2, 80, 0),
        'category': 'Cloth',
        'description': 'Converts a mesh with seams into sewing patterns with sewing edges',
        'location': 'Object > Seams to Sewing Pattern > ...',
        'wiki_url': 'https://blenderartists.org/t/seams-to-sewing-pattern-v-0-5-for-2-8-and-2-9/1248713'}

import bpy
import bmesh
import mathutils
import math
from bpy.types import Menu

def menu_func(self, context):
    lay_out = self.layout
    lay_out.operator_context = 'INVOKE_REGION_WIN'

    lay_out.separator()
    lay_out.menu("VIEW3D_mesh_seams_to_sewing_pattern_menu",
                text="Seams to Sewing Pattern")
    
class VIEW3D_mesh_seams_to_sewing_pattern_menu(Menu):
    bl_idname = "VIEW3D_mesh_seams_to_sewing_pattern_menu"
    bl_label = "Seams to Sewing Pattern"

    def draw(self, context):
        layout = self.layout
        layout.operator("mesh.primitive_monkey_add",
                        text="Seams to Sewing Pattern", icon="OUTLINER_DATA_SURFACE")
        layout.operator("mesh.primitive_monkey_add",
                        text="Export Sewing Pattern (.svg)", icon="EXPORT")


# Register
classes = [
    VIEW3D_mesh_seams_to_sewing_pattern_menu
    ]

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    # Adds submenu in View3D > Seams to Sewing Pattern
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    # Removes submenu
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

if __name__ == "__main__":
    register()
