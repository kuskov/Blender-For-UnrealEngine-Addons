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


def ExportSingleFbxNLAAnim(
        originalScene,
        dirpath,
        filename,
        obj
        ):

    '''
    #####################################################
            #NLA ANIMATION
    #####################################################
    '''
    # Export a single NLA Animation

    scene = bpy.context.scene
    addon_prefs = bpy.context.preferences.addons[__package__].preferences

    filename = ValidFilenameForUnreal(filename)
    s = CounterStart()

    SelectParentAndDesiredChilds(obj)
    DuplicateSelectForExport()
    BaseTransform = obj.matrix_world.copy()
    active = bpy.context.view_layer.objects.active
    export_procedure = active.bfu_export_procedure

    if active.ExportAsProxy:
        ApplyProxyData(active)

    if addon_prefs.bakeArmatureAction:
        BakeArmatureAnimation(active, scene.frame_start, scene.frame_end)

    ApplyExportTransform(active)

    # This will rescale the rig and unit scale to get a root bone egal to 1
    ShouldRescaleRig = GetShouldRescaleRig(active)
    if ShouldRescaleRig:

        rrf = GetRescaleRigFactor()  # rigRescaleFactor
        savedUnitLength = bpy.context.scene.unit_settings.scale_length
        bpy.context.scene.unit_settings.scale_length *= 1/rrf
        oldScale = active.scale.z
        ApplySkeletalExportScale(active, rrf)
        RescaleAllActionCurve(rrf*oldScale)
        for selected in bpy.context.selected_objects:
            if selected.type == "MESH":
                RescaleShapeKeysCurve(selected, 1/rrf)
        RescaleSelectCurveHook(1/rrf)
        ResetArmaturePose(active)
        RescaleRigConsraints(active, rrf)

    scene.frame_start += active.StartFramesOffset
    scene.frame_end += active.EndFramesOffset
    absdirpath = bpy.path.abspath(dirpath)
    VerifiDirs(absdirpath)
    fullpath = os.path.join(absdirpath, filename)

    # Set rename temporarily the Armature as "Armature"
    oldArmatureName = RenameArmatureAsExportName(active)

    if (export_procedure == "normal"):
        bpy.ops.export_scene.fbx(
            filepath=fullpath,
            check_existing=False,
            use_selection=True,
            global_scale=GetObjExportScale(active),
            object_types={'ARMATURE', 'EMPTY', 'MESH'},
            use_custom_props=addon_prefs.exportWithCustomProps,
            add_leaf_bones=False,
            use_armature_deform_only=active.exportDeformOnly,
            bake_anim=True,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False,
            bake_anim_force_startend_keying=True,
            bake_anim_step=GetAnimSample(active),
            bake_anim_simplify_factor=active.SimplifyAnimForExport,
            use_metadata=addon_prefs.exportWithMetaData,
            primary_bone_axis=active.exportPrimaryBaneAxis,
            secondary_bone_axis=active.exporSecondaryBoneAxis,
            axis_forward=active.exportAxisForward,
            axis_up=active.exportAxisUp,
            bake_space_transform=False
            )

    if (export_procedure == "auto-rig-pro"):
        ExportAutoProRig(
            filepath=fullpath,
            # export_rig_name=GetDesiredExportArmatureName(),
            bake_anim=True,
            anim_export_name_string=active.animation_data.action.name,
            mesh_smooth_type="FACE"
            )

    ResetArmaturePose(active)
    scene.frame_start -= active.StartFramesOffset
    scene.frame_end -= active.EndFramesOffset
    exportTime = CounterEnd(s)

    # Reset armature name
    ResetArmatureName(active, oldArmatureName)

    ResetArmaturePose(obj)

    # Reset Transform
    obj.matrix_world = BaseTransform

    # This will rescale the rig and unit scale to get a root bone egal to 1
    if ShouldRescaleRig:
        # Reset Curve an unit
        bpy.context.scene.unit_settings.scale_length = savedUnitLength
        RescaleAllActionCurve(1/(rrf*oldScale))

    CleanDeleteObjects(bpy.context.selected_objects)

    MyAsset = originalScene.UnrealExportedAssetsList.add()
    MyAsset.assetName = filename
    MyAsset.assetType = "NlAnim"
    MyAsset.exportPath = absdirpath
    MyAsset.exportTime = exportTime
    MyAsset.object = obj
    return MyAsset
