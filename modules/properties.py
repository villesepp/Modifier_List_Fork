import bpy, os, functools
from bpy.app.handlers import persistent
from bpy.props import *
from bpy.types import PropertyGroup
from . import modifier_categories
from .utils import get_ml_active_object
from pathlib import Path

assets_dic = []
BLENDER_VERSION_MAJOR_POINT_MINOR = float(bpy.app.version_string[0:4].strip("."))

# should read all .blend files and get a hash based on file amounts, names, size, modifierd dated etc and only updated if hash does not match!

def get_asset_blend_files():
    prefs = bpy.context.preferences
    filepaths = prefs.filepaths
    asset_libraries = filepaths.asset_libraries
    blend_file_paths = []

    for asset_library in asset_libraries:
        if BLENDER_VERSION_MAJOR_POINT_MINOR >= 5.2: 
            if not asset_library.enabled:
                continue
        library_name = asset_library.name
        library_path = Path(asset_library.path)
        blend_files = [fp for fp in library_path.glob("**/*.blend") if fp.is_file()]

        essentials = Path(os.path.join(bpy.app.binary_path.replace("blender.exe", ""), str(BLENDER_VERSION_MAJOR_POINT_MINOR), "datafiles", "assets", "nodes"))
        essentials_blend_files = [fp for fp in essentials.glob("**/*.blend") if fp.is_file()]
        blend_files.extend(essentials_blend_files)
        blend_file_paths.extend(blend_files)
    return blend_file_paths

def get_assets_asset_library_hash(paths):
    data = []

    for path in paths:
        data.append(os.path.getsize(path))
        data.append(os.path.getctime(path))
        data.append(os.path.getmtime(path))
        data.append(os.path.basename(path))
    data.append(len(paths))

    return hash(str(data))
    
def has_asset_library_been_updated(paths): # we should do it per asset liberay!
    hash_value = get_assets_asset_library_hash(paths)
    return False    

# def get_assset_libery_modifiers(blend_files):
#     for filepath in blend_files:
#         try:
#             with bpy.data.libraries.load(str(filepath), assets_only=True) as (file_contents, _):
#                 for ng_name in file_contents.node_groups:
#                     asset_library_identifier = library_name
#                     blend = str(os.path.basename(blend_file))
#                     for item in file_contents.node_groups:
#                         relative_asset_identifier = os.path.join(blend, "NodeTree", str(item))
#                         asset_library_type = "CUSTOM"
#                         if blend_file in essentials_blend_files:
#                             asset_library_type = "ESSENTIALS"
#                         assets_dic.append(
#                         {
#                             "name": os.path.basename(relative_asset_identifier).replace(".blend", ""),
#                             "relative_asset_identifier": relative_asset_identifier,
#                             "asset_library_identifier": asset_library_identifier,
#                             "asset_library_type": asset_library_type,
#                         })
#         except Exception as e:
#             print(f"Could not read asset file {filepath.name}: {e}")

def get_all_modifier_assets():
    global assets_dic

    #  Scan the local current file, needs to be updated if new node gruope is added! 
    for ng in bpy.data.node_groups:
        assets_dic.append(
        {
            "name": ng.name,
            "relative_asset_identifier": "NodeTree\\"+ng.name,
            "asset_library_identifier": "",
            "asset_library_type": 'LOCAL',
        })

    if not assets_dic:
        prefs = bpy.context.preferences
        filepaths = prefs.filepaths
        asset_libraries = filepaths.asset_libraries

        essentials = Path(os.path.join(bpy.app.binary_path.replace("blender.exe", ""), str(BLENDER_VERSION_MAJOR_POINT_MINOR), "datafiles", "assets", "nodes"))
        essentials_blend_files = [fp for fp in essentials.glob("**/*.blend") if fp.is_file()]

        for asset_library in asset_libraries: # user asset liberays
            if BLENDER_VERSION_MAJOR_POINT_MINOR >= 5.2: 
                if not asset_library.enabled:
                    continue
            library_name = asset_library.name
            library_path = Path(asset_library.path)
            blend_files = [fp for fp in library_path.glob("**/*.blend") if fp.is_file()]

            if has_asset_library_been_updated(blend_files):
                for blend_file in blend_files:
                    with bpy.data.libraries.load(str(blend_file), assets_only=True) as (file_contents, _):
                        asset_library_identifier = library_name
                        blend = str(os.path.basename(blend_file))
                        for item in file_contents.node_groups:
                            relative_asset_identifier = os.path.join(blend, "NodeTree", str(item))
                            asset_library_type = "CUSTOM"
                            if blend_file in essentials_blend_files:
                                asset_library_type = "ESSENTIALS"
                            assets_dic.append(
                            {
                                "name": os.path.basename(relative_asset_identifier).replace(".blend", ""),
                                "relative_asset_identifier": relative_asset_identifier,
                                "asset_library_identifier": asset_library_identifier,
                                "asset_library_type": asset_library_type,
                            })
        # essentials asset liberays
    
    return assets_dic
# bpy.ops.object.modifier_add_node_group(asset_library_type='ESSENTIALS', asset_library_identifier="", relative_asset_identifier="nodes\\procedural_hair_node_assets.blend\\NodeTree\\Curl Hair Curves")

def get_assets(prop):
    assets = get_all_modifier_assets()
    # prop.clear()
    for item in assets:
        try:
            new_item = prop.add()
            new_item.name = item["name"]
            new_item.value = item["relative_asset_identifier"]
            new_item.library = item["asset_library_identifier"]
            new_item.asset_library_type = item["asset_library_type"]
            new_item.is_asset = True
        except:
            pass
            # path = item["relative_asset_identifier"]
            # print(f"failed to add asset: {path}")
# Callbacks
# ======================================================================

def modifier_active_index_get(self):
    for mod in self.modifiers:
        if mod.is_active:
            return self.modifiers.find(mod.name)

    return 0


def modifier_active_index_set(self, value):
    mods = self.modifiers

    if mods:
        mods[value].is_active = True


def pinned_object_ensure_users(scene):
    """Handler for making sure a pinned object which is only used by
    pinned_object, i.e. an object which was deleted while it was
    pinned, really gets deleted + the property gets reset.
    """
    ml_props = scene.modifier_list

    if ml_props.pinned_object:
        if ml_props.pinned_object.users == 1 and not ml_props.pinned_object.use_fake_user:
            bpy.data.objects.remove(ml_props.pinned_object)
            ml_props.pinned_object = None


def on_pinned_object_change(self, context):
    """Callback function for pinned_object"""
    depsgraph_handlers = bpy.app.handlers.depsgraph_update_pre

    if context.scene.modifier_list.pinned_object:
        depsgraph_handlers.append(pinned_object_ensure_users)
    else:
        try:
            depsgraph_handlers.remove(pinned_object_ensure_users)
        except ValueError:
            pass


def set_all_modifier_collection_items():
    """This is to be called on loading a new file or reloading addons
    to make modifiers available in search.
    """
    all_modifiers = bpy.context.window_manager.modifier_list.all_modifiers
    sorted_names_icons_types = sorted(modifier_categories.ALL_MODIFIERS_NAMES_ICONS_TYPES,
                                      key=lambda mod: mod[0])

    if not all_modifiers:
        for name, _, mod in sorted_names_icons_types:
            item = all_modifiers.add()
            item.name = name
            item.value = mod

    # bpy.app.timers.register(functools.partial(get_assets, all_modifiers), first_interval=1.1)

def set_mesh_modifier_collection_items():
    """This is to be called on loading a new file or reloading addons
    to make modifiers available in search.
    """
    mesh_modifiers = bpy.context.window_manager.modifier_list.mesh_modifiers
    sorted_names_icons_types = sorted(modifier_categories.MESH_ALL_NAMES_ICONS_TYPES,
                                      key=lambda mod: mod[0])

    if not mesh_modifiers:
        for name, _, mod in sorted_names_icons_types:
            item = mesh_modifiers.add()
            item.name = name
            item.value = mod

    # bpy.app.timers.register(functools.partial(get_assets, mesh_modifiers), first_interval=1.2)


def set_curve_text_modifier_collection_items():
    """This is to be called on loading a new file or reloading addons
    to make modifiers available in search.
    """
    curve_and_text_modifiers = bpy.context.window_manager.modifier_list.curve_text_modifiers
    sorted_names_icons_types = sorted(modifier_categories.CURVE_TEXT_ALL_NAMES_ICONS_TYPES,
                                      key=lambda mod: mod[0])

    if not curve_and_text_modifiers:
        for name, _, mod in sorted_names_icons_types:
            item = curve_and_text_modifiers.add()
            item.name = name
            item.value = mod

    # bpy.app.timers.register(functools.partial(get_assets, curve_and_text_modifiers), first_interval=1.3)

def set_curves_modifier_collection_items():
    """This is to be called on loading a new file or reloading addons
    to make modifiers available in search.
    """
    curves_modifiers = bpy.context.window_manager.modifier_list.curves_modifiers
    sorted_names_icons_types = sorted(modifier_categories.CURVES_ALL_NAMES_ICONS_TYPES,
                                      key=lambda mod: mod[0])

    if not curves_modifiers:
        for name, _, mod in sorted_names_icons_types:
            item = curves_modifiers.add()
            item.name = name
            item.value = mod

    # bpy.app.timers.register(functools.partial(get_assets, curves_modifiers), first_interval=1.4)

def set_lattice_modifier_collection_items():
    """This is to be called on loading a new file or reloading addons
    to make modifiers available in search.
    """
    lattice_modifiers = bpy.context.window_manager.modifier_list.lattice_modifiers
    sorted_names_icons_types = sorted(modifier_categories.LATTICE_ALL_NAMES_ICONS_TYPES,
                                      key=lambda mod: mod[0])

    if not lattice_modifiers:
        for name, _, mod in sorted_names_icons_types:
            item = lattice_modifiers.add()
            item.name = name
            item.value = mod

    # bpy.app.timers.register(functools.partial(get_assets, lattice_modifiers), first_interval=1.5)

def set_pointcloud_modifier_collection_items():
    """This is to be called on loading a new file or reloading addons
    to make modifiers available in search.
    """
    pointcloud_modifiers = bpy.context.window_manager.modifier_list.pointcloud_modifiers
    sorted_names_icons_types = sorted(modifier_categories.POINTCLOUD_ALL_NAMES_ICONS_TYPES,
                                      key=lambda mod: mod[0])

    if not pointcloud_modifiers:
        for name, _, mod in sorted_names_icons_types:
            item = pointcloud_modifiers.add()
            item.name = name
            item.value = mod

    # bpy.app.timers.register(functools.partial(get_assets, pointcloud_modifiers), first_interval=1.6)


def set_surface_modifier_collection_items():
    """This is to be called on loading a new file or reloading addons
    to make modifiers available in search.
    """
    surface_modifiers = bpy.context.window_manager.modifier_list.surface_modifiers
    sorted_names_icons_types = sorted(modifier_categories.SURFACE_ALL_NAMES_ICONS_TYPES,
                                      key=lambda mod: mod[0])

    if not surface_modifiers:
        for name, _, mod in sorted_names_icons_types:
            item = surface_modifiers.add()
            item.name = name
            item.value = mod

    # bpy.app.timers.register(functools.partial(get_assets, surface_modifiers), first_interval=1.7)


def set_volume_modifier_collection_items():
    """This is to be called on loading a new file or reloading addons
    to make modifiers available in search.
    """
    volume_modifiers = bpy.context.window_manager.modifier_list.volume_modifiers
    sorted_names_icons_types = sorted(modifier_categories.VOLUME_ALL_NAMES_ICONS_TYPES,
                                      key=lambda mod: mod[0])

    if not volume_modifiers:
        for name, _, mod in sorted_names_icons_types:
            item = volume_modifiers.add()
            item.name = name
            item.value = mod

    # bpy.app.timers.register(functools.partial(get_assets, volume_modifiers), first_interval=1.8)


@persistent
def on_file_load(dummy):
    set_all_modifier_collection_items()
    set_mesh_modifier_collection_items()
    set_curve_text_modifier_collection_items()
    set_curves_modifier_collection_items()
    set_lattice_modifier_collection_items()
    set_pointcloud_modifier_collection_items()
    set_surface_modifier_collection_items()
    set_volume_modifier_collection_items()


def modifier_search_items(self, context, edit_text):
    ob = get_ml_active_object()
    if ob is None:
        return ()

    collection_by_object_type = {
        'MESH': "mesh_modifiers",
        'CURVE': "curve_text_modifiers",
        'FONT': "curve_text_modifiers",
        'CURVES': "curves_modifiers",
        'LATTICE': "lattice_modifiers",
        'POINTCLOUD': "pointcloud_modifiers",
        'SURFACE': "surface_modifiers",
        'VOLUME': "volume_modifiers",
    }
    collection_name = collection_by_object_type.get(ob.type)
    if collection_name is None:
        return ()

    ml_props = context.window_manager.modifier_list
    return getattr(ml_props, collection_name).keys()


def add_modifier(self, context):
    # Add modifier
    ml_props = bpy.context.window_manager.modifier_list
    mod_name = ml_props.modifier_to_add_from_search

    if mod_name == "":
        return None
    
    search_collections = (
        ml_props.mesh_modifiers,
        ml_props.curve_text_modifiers,
        ml_props.curves_modifiers,
        ml_props.lattice_modifiers,
        ml_props.pointcloud_modifiers,
        ml_props.surface_modifiers,
        ml_props.volume_modifiers,
        ml_props.all_modifiers,
    )
    modifier_item = next(
        (item for collection in search_collections
         if (item := collection.get(mod_name)) is not None),
        None,
    )
    if modifier_item is None:
        return None

    bpy.ops.object.ml_modifier_add('EXEC_DEFAULT', modifier_type=modifier_item.value)
    # Executing an operator via a function doesn't create an undo event,
    # so it needs to be added manually.
    bpy.ops.ed.undo_push(message="Add Modifier")
    ml_props.modifier_to_add_from_search = ""


# Modifier collections
# ======================================================================

class AllModifiersCollection(PropertyGroup):
    # Collection Property for search
    value: StringProperty(name="Type")
    # library: StringProperty(name="Library", default="")
    # is_asset: BoolProperty(name="Is Asset?", default=False)
    # asset_library_type: StringProperty(name="asset_library_type")

class MeshModifiersCollection(PropertyGroup):
    # Collection Property for search
    value: StringProperty(name="Type")
    # library: StringProperty(name="Library", default="")
    # is_asset: BoolProperty(name="Is Asset?", default=False)
    # asset_library_type: StringProperty(name="asset_library_type")

class CurveTextModifiersCollection(PropertyGroup):
    # Collection Property for search
    value: StringProperty(name="Type")
    # library: StringProperty(name="Library", default="")
    # is_asset: BoolProperty(name="Is Asset?", default=False)
    # asset_library_type: StringProperty(name="asset_library_type")


class CurvesModifiersCollection(PropertyGroup):
    # Collection Property for search
    value: StringProperty(name="Type")
    # library: StringProperty(name="Library", default="")
    # is_asset: BoolProperty(name="Is Asset?", default=False)
    # asset_library_type: StringProperty(name="asset_library_type")


class LatticeModifiersCollection(PropertyGroup):
    # Collection Property for search
    value: StringProperty(name="Type")
    # library: StringProperty(name="Library", default="")
    # is_asset: BoolProperty(name="Is Asset?", default=False)
    # asset_library_type: StringProperty(name="asset_library_type")


class PointcloudModifiersCollection(PropertyGroup):
    # Collection Property for search
    value: StringProperty(name="Type")
    # library: StringProperty(name="Library", default="")
    # is_asset: BoolProperty(name="Is Asset?", default=False)
    # asset_library_type: StringProperty(name="asset_library_type")


class SurfaceModifiersCollection(PropertyGroup):
    # Collection Property for search
    value: StringProperty(name="Type")
    # library: StringProperty(name="Library", default="")
    # is_asset: BoolProperty(name="Is Asset?", default=False)
    # asset_library_type: StringProperty(name="asset_library_type")


class VolumeModifiersCollection(PropertyGroup):
    # Collection Property for search
    value: StringProperty(name="Type")
    # library: StringProperty(name="Library", default="")
    # is_asset: BoolProperty(name="Is Asset?", default=False)
    # asset_library_type: StringProperty(name="asset_library_type")


# Property groups
# ======================================================================

class ML_SceneProperties(PropertyGroup):
    pinned_object: PointerProperty(
        type=bpy.types.Object,
        update=on_pinned_object_change)


class ML_PreferencesUIProperties(PropertyGroup):
    favourite_modifiers_expand: BoolProperty(name="", default=True)
    favourite_modifiers_menu_expand: BoolProperty(name="", default=True)
    general_expand: BoolProperty(name="")
    popup_expand: BoolProperty(name="")
    gizmo_expand: BoolProperty(name="")
    modifier_defaults_expand: BoolProperty()
    modifier_to_show_defaults_for: StringProperty(
        name="Modifier to show defaults for",
        description="Search for a modifier to show its customizable default settings",
        default="Armature")


class ML_WindowManagerProperties(PropertyGroup):
    modifier_to_add_from_search: StringProperty(
        name="Search for Modifier",
        update=add_modifier,
        search=modifier_search_items,
        search_options={'SORT'},
        description="Search for a modifier and add it to the stack")
    all_modifiers: CollectionProperty(type=AllModifiersCollection)
    mesh_modifiers: CollectionProperty(type=MeshModifiersCollection)
    curve_text_modifiers: CollectionProperty(type=CurveTextModifiersCollection)
    curves_modifiers: CollectionProperty(type=CurvesModifiersCollection)
    lattice_modifiers: CollectionProperty(type=LatticeModifiersCollection)
    pointcloud_modifiers: CollectionProperty(type=PointcloudModifiersCollection)
    surface_modifiers: CollectionProperty(type=SurfaceModifiersCollection)
    volume_modifiers: CollectionProperty(type=VolumeModifiersCollection)
    popup_tabs_items = [
        ("MODIFIERS", "Modifiers", "Modifiers", 'MODIFIER', 1),
        ("OBJECT_DATA", "Object Data", "Object Data", 'MESH_DATA', 2),
        ("ATTRIBUTES", "Attributes", "Attributes", 'OUTLINER_DATA_FONT', 3),
    ]
    popup_active_tab: EnumProperty(
        items=popup_tabs_items,
        name="Popup Tabs",
        default='MODIFIERS')
    preferences_ui_props: PointerProperty(type=ML_PreferencesUIProperties)
    active_favourite_modifier_slot_index: IntProperty()
    gizmo_object_settings_expand: BoolProperty()


# Registering
# ======================================================================

classes = (
    AllModifiersCollection,
    MeshModifiersCollection,
    CurveTextModifiersCollection,
    CurvesModifiersCollection,
    LatticeModifiersCollection,
    PointcloudModifiersCollection,
    SurfaceModifiersCollection,
    VolumeModifiersCollection,
    ML_SceneProperties,
    ML_PreferencesUIProperties,
    ML_WindowManagerProperties
)


def register():
    # === Properties ===
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.ml_modifier_active_index = IntProperty(
        options={'LIBRARY_EDITABLE'},
        override={'LIBRARY_OVERRIDABLE'},
        get=modifier_active_index_get,
        set=modifier_active_index_set)

    wm = bpy.types.WindowManager
    wm.modifier_list = PointerProperty(type=ML_WindowManagerProperties)

    bpy.types.Scene.modifier_list = PointerProperty(type=ML_SceneProperties)

    bpy.app.handlers.load_post.append(on_file_load)

    set_all_modifier_collection_items()
    set_mesh_modifier_collection_items()
    set_curve_text_modifier_collection_items()
    set_curves_modifier_collection_items()
    set_lattice_modifier_collection_items()
    set_pointcloud_modifier_collection_items()
    set_surface_modifier_collection_items()
    set_volume_modifier_collection_items()
    # if not assets_dic:
    #     bpy.app.timers.register(functools.partial(get_all_modifier_assets), first_interval=1.0)


def unregister():
    try:
        bpy.app.handlers.load_post.remove(on_file_load)
    except ValueError:
        pass
    
    try:
        del bpy.types.Object.ml_modifier_active_index
    except AttributeError:
        pass

    try:
        del bpy.types.WindowManager.modifier_list
    except AttributeError:
        pass

    try:
        del bpy.types.Scene.modifier_list
    except AttributeError:
        pass

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
