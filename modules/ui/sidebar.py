import bpy, os
from bpy.types import Panel

from .modifiers_ui import modifiers_ui_with_list, modifiers_ui_with_stack
from .ui_common import pin_object_button
from .vertex_groups_ui import vertex_groups_ui
from .attributes_ui import attributes_ui
from ..utils import get_ml_active_object, object_type_has_modifiers
from ..icons import get_icons, get_icon_folder_path
from ... import __package__ as base_package

class BasePanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Modifier List"

from bpy.utils import previews
# hack to get in the npanel icon for now! Cases errors on reload of addon though, but it works for now. TODO: Find better solution
_preview_collections = {}

def get_icon(name):
    # === Remove the current icons and clear preview_collections ===
    for pcoll in _preview_collections.values():
        previews.remove(pcoll)

    _preview_collections.clear()

    pcoll = previews.new()

    icons_dir = get_icon_folder_path()
    icons_dir_files = os.listdir(icons_dir)

    all_icon_files = [icon for icon in icons_dir_files if icon.endswith(".png")]
    all_icon_names = [icon[0:-4] for icon in all_icon_files]
    all_icon_files_and_names = zip(all_icon_names, all_icon_files)

    for icon_name, icon_file in all_icon_files_and_names:
        icon = pcoll.load(icon_name, os.path.join(icons_dir, icon_file), 'IMAGE')
        hacky_icon_fix = str(icon.icon_pixels)
    _preview_collections["main"] = pcoll
    
    return pcoll[name].icon_id

def unregister():
    for pcoll in _preview_collections.values():
        previews.remove(pcoll)
    _preview_collections.clear()

class VIEW3D_PT_ml_modifiers(Panel, BasePanel):
    # A leading space in the label, so there's separation between it
    # and the pin button
    bl_label = " Modifiers"
    bl_icon_value = get_icon("MODIFIER")

    @classmethod
    def poll(cls, context):
        prefs = bpy.context.preferences.addons[base_package].preferences

        if not prefs.use_sidebar:
            return False

        if prefs.keep_sidebar_visible:
            return True

        ob = get_ml_active_object()
        if ob is not None:
            return object_type_has_modifiers(ob)

        return False

    def draw_header(self, context):
        layout = self.layout
        pin_object_button(context, layout)
    def draw_header_preset(self, context):
        layout = self.layout
        layout.operator("preferences.addon_show", text="Prefs", icon='PREFERENCES', emboss=True).module = base_package


    def draw(self, context):
        layout = self.layout

        ob = get_ml_active_object()
        prefs = bpy.context.preferences.addons[base_package].preferences

        if not ob:
            layout.label(text="No active object")
        elif not object_type_has_modifiers(ob):
            layout.label(text="Wrong object type")
        else:
            if prefs.sidebar_style == 'LIST':
                modifiers_ui_with_list(context, layout, new_menu=True)
            else:
                modifiers_ui_with_stack(context, layout)


class VIEW3D_PT_ml_vertex_groups(Panel, BasePanel):
    bl_label = "Vertex Groups"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        prefs = bpy.context.preferences.addons[base_package].preferences

        if not prefs.use_sidebar:
            return False

        ob = get_ml_active_object()
        if ob is not None:
            return ob.type in {'MESH', 'LATTICE'}

        return False

    def draw(self, context):
        layout = self.layout
        vertex_groups_ui(context, layout)

class VIEW3D_PT_ml_attributes(Panel, BasePanel):
    bl_label = "Attributes"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        prefs = bpy.context.preferences.addons[base_package].preferences

        if not prefs.use_sidebar:
            return False

        ob = get_ml_active_object()
        if ob is not None:
            return ob.type in {'MESH', 'LATTICE'}

        return False

    def draw(self, context):
        layout = self.layout
        attributes_ui(context, layout)


def update_sidebar_category():
    bpy.utils.unregister_class(VIEW3D_PT_ml_modifiers)
    bpy.utils.unregister_class(VIEW3D_PT_ml_vertex_groups)
    bpy.utils.unregister_class(VIEW3D_PT_ml_attributes)

    category = bpy.context.preferences.addons[base_package].preferences.sidebar_category
    VIEW3D_PT_ml_modifiers.bl_category = category
    VIEW3D_PT_ml_vertex_groups.bl_category = category
    VIEW3D_PT_ml_attributes.bl_category = category

    bpy.utils.register_class(VIEW3D_PT_ml_modifiers)
    bpy.utils.register_class(VIEW3D_PT_ml_vertex_groups)
    bpy.utils.register_class(VIEW3D_PT_ml_attributes)


def register():
    update_sidebar_category()
