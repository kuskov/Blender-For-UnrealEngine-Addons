# ====================== BEGIN GPL LICENSE BLOCK ============================
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.
#  All rights reserved.
#
# ======================= END GPL LICENSE BLOCK =============================


import bpy
import time
import math

if "bpy" in locals():
    import importlib
    if "bfu_write_text" in locals():
        importlib.reload(bfu_write_text)
    if "bfu_basics" in locals():
        importlib.reload(bfu_basics)
    if "bfu_utils" in locals():
        importlib.reload(bfu_utils)
    if "bfu_export_utils" in locals():
        importlib.reload(bfu_export_utils)

from . import bfu_write_text
from . import bfu_basics
from .bfu_basics import *
from . import bfu_utils
from .bfu_utils import *
from . import bfu_export_utils
from .bfu_export_utils import *


def ExportSingleFbxCamera(
        originalScene,
        dirpath,
        filename,
        obj
        ):

    '''
    #####################################################
            #CAMERA
    #####################################################
    '''
    # Export single camera

    scene = bpy.context.scene
    addon_prefs = bpy.context.preferences.addons[__package__].preferences

    filename = ValidFilename(filename)
    if obj.type != 'CAMERA':
        return

    s = CounterStart()
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    # Select and rescale camera for export
    bpy.ops.object.select_all(action='DESELECT')
    SelectSpecificObject(obj)

    obj.delta_scale *= 0.01
    if obj.animation_data is not None:
        action = obj.animation_data.action
        scene.frame_start = GetDesiredActionStartEndTime(obj, action)[0]
        scene.frame_end = GetDesiredActionStartEndTime(obj, action)[1]

    absdirpath = bpy.path.abspath(dirpath)
    VerifiDirs(absdirpath)
    fullpath = os.path.join(absdirpath, filename)

    bpy.ops.export_scene.fbx(
        filepath=fullpath,
        check_existing=False,
        use_selection=True,
        global_scale=GetObjExportScale(obj),
        object_types={'CAMERA'},
        use_custom_props=addon_prefs.exportWithCustomProps,
        add_leaf_bones=False,
        use_armature_deform_only=obj.exportDeformOnly,
        bake_anim=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_step=GetAnimSample(obj),
        bake_anim_simplify_factor=obj.SimplifyAnimForExport,
        use_metadata=addon_prefs.exportWithMetaData,
        primary_bone_axis=obj.exportPrimaryBaneAxis,
        secondary_bone_axis=obj.exporSecondaryBoneAxis,
        axis_forward=obj.exportAxisForward,
        axis_up=obj.exportAxisUp,
        bake_space_transform=False
        )

    # Reset camera scale
    obj.delta_scale *= 100

    exportTime = CounterEnd(s)

    MyAsset = originalScene.UnrealExportedAssetsList.add()
    MyAsset.assetName = filename
    MyAsset.assetType = "Camera"
    MyAsset.exportPath = absdirpath
    MyAsset.exportTime = exportTime
    MyAsset.object = obj
    return MyAsset
