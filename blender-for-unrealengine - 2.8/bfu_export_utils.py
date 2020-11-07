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

from . import bfu_write_text
from . import bfu_basics
from .bfu_basics import *
from . import bfu_utils
from .bfu_utils import *


def ApplyProxyData(obj):

    # Apply proxy data if needed.
    if obj.ExportProxyChild is not None:

        def ReasignProxySkeleton(newArmature, oldArmature):
            for select in bpy.context.selected_objects:
                if select.type == "CURVE":
                    for mod in select.modifiers:
                        if mod.type == "HOOK":
                            if mod.object == oldArmature:
                                matrix_inverse = mod.matrix_inverse.copy()
                                mod.object = newArmature
                                mod.matrix_inverse = matrix_inverse

                else:
                    for mod in select.modifiers:
                        if mod.type == 'ARMATURE':
                            if mod.object == oldArmature:
                                mod.object = newArmature

            for bone in newArmature.pose.bones:
                for cons in bone.constraints:
                    if hasattr(cons, 'target'):
                        if cons.target == oldArmature:
                            cons.target = newArmature
                        else:
                            ChildProxyName = (
                                cons.target.name +
                                "_UEProxyChild"
                            )
                            if ChildProxyName in bpy.data.objects:
                                cons.target = bpy.data.objects[ChildProxyName]

        # Get old armature in selected objects
        OldProxyChildArmature = None
        for selectedObj in bpy.context.selected_objects:
            if selectedObj != obj:
                if selectedObj.type == "ARMATURE":
                    OldProxyChildArmature = selectedObj

        # Reasing parent + add to remove
        if OldProxyChildArmature is not None:
            ToRemove = []
            ToRemove.append(OldProxyChildArmature)
            for selectedObj in bpy.context.selected_objects:
                if selectedObj != obj:
                    if selectedObj.parent == OldProxyChildArmature:
                        # Reasing parent and keep position
                        SavedPos = selectedObj.matrix_world.copy()
                        selectedObj.name += "_UEProxyChild"
                        selectedObj.parent = obj
                        selectedObj.matrix_world = SavedPos
                    else:
                        ToRemove.append(selectedObj)
            ReasignProxySkeleton(obj, OldProxyChildArmature)
            SavedSelect = GetCurrentSelection()
            RemovedObjects = CleanDeleteObjects(ToRemove)
            SavedSelect.RemoveFromListByName(RemovedObjects)
            SetCurrentSelection(SavedSelect)


def BakeArmatureAnimation(armature, frame_start, frame_end):
    # Change to pose mode
    SavedSelect = GetCurrentSelection()
    bpy.ops.object.select_all(action='DESELECT')
    SelectSpecificObject(armature)
    bpy.ops.nla.bake(
        frame_start=frame_start-10,
        frame_end=frame_end+10,
        only_selected=False,
        visual_keying=True,
        clear_constraints=True,
        use_current_action=False,
        bake_types={'POSE'}
        )
    bpy.ops.object.select_all(action='DESELECT')
    SetCurrentSelection(SavedSelect)


def DuplicateSelectForExport():
    # Note: Need look for a optimized duplicate, This is too long

    scene = bpy.context.scene
    bpy.ops.object.duplicate()

    # Save the name for found after "Make Instances Real"
    currentSelectNames = []
    for currentSelectName in bpy.context.selected_objects:
        currentSelectNames.append(currentSelectName.name)

    # Make Instances Real
    bpy.ops.object.duplicates_make_real(
        use_base_parent=True,
        use_hierarchy=True
        )

    for objSelect in currentSelectNames:
        if objSelect not in bpy.context.selected_objects:
            bpy.data.objects[objSelect].select_set(True)

    # Make sigle user and clean useless data.
    for objScene in bpy.context.selected_objects:
        if objScene.data is not None:
            oldData = objScene.data.name
            objScene.data = objScene.data.copy()
            RemoveUselessSpecificData(oldData, objScene.type)


def SetSocketsExportTransform(obj):
    # Set socket scale for Unreal

    addon_prefs = bpy.context.preferences.addons[__package__].preferences
    for socket in GetSocketDesiredChild(obj):
        if GetShouldRescaleSocket():
            socket.delta_scale *= GetRescaleSocketFactor()

        if addon_prefs.staticSocketsAdd90X:
            savedScale = socket.scale.copy()
            savedLocation = socket.location.copy()
            AddMat = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
            socket.matrix_world = socket.matrix_world @ AddMat
            socket.scale = savedScale
            socket.location = savedLocation


def AddSocketsTempName(obj):
    # Add _UE4Socket_TempName at end of the name

    for socket in GetSocketDesiredChild(obj):
        socket.name += "_UE4Socket_TempName"


def RemoveDuplicatedSocketsTempName(obj):
    # Remove _UE4Socket_TempName at end of the name

    for socket in GetSocketDesiredChild(obj):
        ToRemove = "_UE4Socket_TempName.xxx"
        socket.name = socket.name[:-len(ToRemove)]


def TryToApplyCustomSocketsName(obj):
    # Try to apply the custom SocketName
    scene = bpy.context.scene

    for socket in GetSocketDesiredChild(obj):
        if socket.usesocketcustomName:
            if socket.socketcustomName not in scene.objects:
                socket.name = "SOCKET_"+socket.socketcustomName
            else:
                print(
                    'Can\'t rename socket "' +
                    socket.name +
                    '" to "'+socket.socketcustomName +
                    '".'
                    )


def RemoveSocketsTempName(obj):
    # Remove _UE4Socket_TempName at end of the name
    for socket in GetSocketDesiredChild(obj):
        ToRemove = "_UE4Socket_TempName"
        socket.name = socket.name[:-len(ToRemove)]


def GetShouldRescaleRig(obj):
    # This will return if the rig should be rescale.

    if obj.bfu_export_procedure == "auto-rig-pro":
        return False

    addon_prefs = bpy.context.preferences.addons[__package__].preferences
    if addon_prefs.rescaleFullRigAtExport == "auto":
        if math.isclose(
            bpy.context.scene.unit_settings.scale_length,
                0.01,
                rel_tol=1e-5,
                ):

            return False  # False because that useless to rescale at 1 :v
        else:
            return True
    if addon_prefs.rescaleFullRigAtExport == "custom_rescale":
        return True
    if addon_prefs.rescaleFullRigAtExport == "dont_rescale":
        return False
    return False


def GetRescaleRigFactor():
    # This will return the rescale factor.

    addon_prefs = bpy.context.preferences.addons[__package__].preferences
    if addon_prefs.rescaleFullRigAtExport == "auto":
        return 100 * bpy.context.scene.unit_settings.scale_length
    else:
        return addon_prefs.newRigScale  # rigRescaleFactor


def GetShouldRescaleSocket():
    # This will return if the socket should be rescale.

    addon_prefs = bpy.context.preferences.addons[__package__].preferences
    if addon_prefs.rescaleSocketsAtExport == "auto":
        if bpy.context.scene.unit_settings.scale_length == 0.01:
            return False  # False because that useless to rescale at 1 :v
        else:
            return True
    if addon_prefs.rescaleSocketsAtExport == "custom_rescale":
        return True
    if addon_prefs.rescaleSocketsAtExport == "dont_rescale":
        return False
    return False


def GetRescaleSocketFactor():
    # This will return the rescale factor.

    addon_prefs = bpy.context.preferences.addons[__package__].preferences
    if addon_prefs.rescaleSocketsAtExport == "auto":
        return 1/(100*bpy.context.scene.unit_settings.scale_length)
    else:
        return addon_prefs.staticSocketsImportedSize


def ExportAutoProRig(
        filepath,
        use_selection=True,
        export_rig_name="root",
        bake_anim=True,
        anim_export_name_string="",
        mesh_smooth_type="OFF"
        ):
    bpy.context.scene.arp_engine_type = 'unreal'
    bpy.context.scene.arp_export_rig_type = 'mped'  # types: 'humanoid', 'mped'
    bpy.context.scene.arp_ge_sel_only = use_selection
    bpy.context.scene.arp_export_rig_name = export_rig_name
    # bpy.context.scene.arp_keep_bend_bones = True
    bpy.context.scene.arp_units_x100 = False
    bpy.context.scene.arp_bake_actions = bake_anim
    bpy.context.scene.arp_export_h_actions = False
    bpy.context.scene.arp_export_name_actions = True
    bpy.context.scene.arp_export_name_string = anim_export_name_string
    # bpy.context.scene.arp_export_name_actions = True
    # bpy.context.scene.arp_export_name_string = "test"
    bpy.context.scene.arp_mesh_smooth_type = mesh_smooth_type
    bpy.context.scene.arp_ue_root_motion = False
    bpy.context.scene.arp_export_noparent = False
    bpy.context.scene.arp_export_twist = False
    
    # export it
    bpy.ops.id.arp_export_fbx_panel(filepath=filepath)


def ExportSingleAdditionalTrackCamera(dirpath, filename, obj):
    # Export additional camera track for ue4
    # FocalLength
    # FocusDistance
    # Aperture

    absdirpath = bpy.path.abspath(dirpath)
    VerifiDirs(absdirpath)
    AdditionalTrack = bfu_write_text.WriteSingleCameraAdditionalTrack(obj)
    return bfu_write_text.ExportSingleText(
        AdditionalTrack,
        absdirpath,
        filename
        )


def ExportSingleAdditionalParameterMesh(dirpath, filename, obj):
    # Export additional parameter from static and skeletal mesh track for ue4
    # SocketsList

    absdirpath = bpy.path.abspath(dirpath)
    VerifiDirs(absdirpath)
    AdditionalTrack = bfu_write_text.WriteSingleMeshAdditionalParameter(obj)
    return bfu_write_text.ExportSingleConfigParser(
        AdditionalTrack,
        absdirpath,
        filename
        )
