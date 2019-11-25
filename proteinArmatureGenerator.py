import bpy
import bmesh
import mathutils

# select all and delete
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.object.select_all(action='DESELECT')

# import the fCoil x3d model
file_loc = 'C:\\Users\\Frannken\\Desktop\\Blender Work\\x3dTest\\Complex.x3d'
bpy.ops.import_scene.x3d(filepath = file_loc)

# delete lamps and camera
# https://blender.stackexchange.com/questions/27234/python-how-to-completely-remove-an-object
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        o.select = True
    else:
        o.select = False
bpy.ops.object.delete()

# set each object's origin to volume center
# https://blender.stackexchange.com/questions/70098/how-to-move-an-objects-origin-to-the-center-of-its-bounding-box
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.origin_set(type = 'ORIGIN_GEOMETRY')
# then move cursor to center and move objects to cursor (offset)
bpy.context.area.type = 'VIEW_3D' # for a context issue
bpy.ops.view3d.snap_cursor_to_center()
bpy.ops.view3d.snap_selected_to_cursor(use_offset = True)
bpy.ops.object.select_all(action='DESELECT')

# loop through objects to figure out parts amounts
set_num   = 0 # set_amount determine structure
strip_num = 0 # strip_amount determine bones' number
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    #   Set_part
    if ('Set' in o.name) and ('Strip' not in o.name):
        set_num += 1
    #   Strip_part
    if 'Strip' in o.name:
        strip_num += 1
# print('strip_num = ' + str(strip_num))    # 15
# print('set_num = '   + str(set_num))      # 2
''' explain '''
# strip_num determines how many bones there are
# if set_num > 2, it means the model contains rigid parts



''' Bones Adding Functions '''
def flexible():  # for a model  only has flexible parts
    # add armature and a bone in between two ends
    ''' learnt from these website ''' 
    # https://blenderartists.org/t/bone-manipulation-with-python-in-2-5/456531
    # https://blender.stackexchange.com/questions/51684/python-create-custom-armature-without-ops
    bpy.ops.object.armature_add()    # add bone and armature
    arm_obj = bpy.data.objects['Armature'] # asisgn armature
    bpy.context.scene.objects.active = arm_obj # set  active
    bpy.ops.object.mode_set(mode = 'EDIT')     # edit   mode
    main_bone = arm_obj.data.edit_bones[0]     # assgin bone
    # get the object's world position
    # set the bone's head and tail position
    ''' learnt from these website ''' 
    # https://blender.stackexchange.com/questions/51684/python-create-custom-armature-without-ops
    # https://blender.stackexchange.com/questions/109984/how-to-get-global-object-location-python
    if set_num > 1:  # make sure it has two ends
        object1_name = 'Shape_IndexedTriangleSet.001'
        object2_name = 'Shape_IndexedTriangleSet'
        o1 = bpy.data.objects[object1_name]
        o2 = bpy.data.objects[object2_name]
        main_bone.head = o1.matrix_world.translation
        main_bone.tail = o2.matrix_world.translation
    else:
        print('The model is INCOMPLETE')

    # subdivide the bone with a specific number (keyword subdivide)
    # https://docs.blender.org/api/blender2.8/bpy.ops.armature.html
    main_bone.select = True
    bpy.ops.armature.subdivide(number_cuts = strip_num - 1)

    # snap each bone to the corresponding strip object
    bone_index = 1  # starts from 001
    strip_name = "" # starts from nothing
    for bone in arm_obj.data.edit_bones: 
        # print(bone.name) # show that we can access each bone
        if (bone_index > strip_num - 1) or ('.' not in bone.name):
            continue   # exclude two ends bones
        strip_name = 'Shape_IndexedTriangleStripSet.' + str(bone_index).zfill(3)
        strip = bpy.data.objects[strip_name]
        bone.head = strip.matrix_world.translation
        bone_index += 1
    bpy.ops.object.mode_set(mode = 'OBJECT') # go back to object mode
    ''' explain '''    
    # from bone.001 to bone.014
    # each of their heads moves to the corresponding mesh origin
    # of   strip.001 to strip.014 

    # select objects and join them (note: we must active one first)
    bpy.context.scene.objects.active = bpy.data.objects[strip_name] 
    bpy.ops.object.select_all(action='SELECT')
    arm_obj.select = False
    bpy.ops.object.join()
    bpy.ops.object.select_all(action='DESELECT')

    # automatic weights
    ''' select objects by their type '''
    # https://blender.stackexchange.com/questions/99664/how-can-i-select-all-objects-by-type-using-python
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            o.select = True # select object first then active the armature
    bpy.context.scene.objects.active = arm_obj    
    bpy.ops.object.parent_set(type = 'ARMATURE_AUTO')

    # add IK bone (extrude in EDIT mode and set IK in POSE mode)
    ''' extrude in EDIT mode '''
    bpy.ops.object.mode_set(mode = 'EDIT')         # go to edit mode
    bpy.ops.armature.select_all(action='DESELECT') # clear selections
    bone_head = None  # for storing the head position
    bone_tail = None  # for storing the tail position
    for bone in arm_obj.data.edit_bones:
        if '001' in bone.name:
            bone_head = bone.head
            bone_tail = bone.tail  
    # add an IK target_bone
    tar_name = "Target"
    tar_bone = arm_obj.data.edit_bones.new(tar_name)
    tar_bone.head = bone_tail
    tar_bone.tail = bone_tail - bone_head
    ''' set IK in POSE mode '''
    bpy.ops.object.mode_set(mode = 'POSE')   # go to pose mode
    bpy.ops.pose.select_all(action='DESELECT') # clear selections
    for bone in arm_obj.pose.bones: 
        if '001' in bone.name:
            bone.constraints.new('IK')
            bone.constraints['IK'].target    = arm_obj
            bone.constraints["IK"].subtarget = tar_name 
   
def rigid():     # for a model also  has rigid parts
    # declare an int array for node indices, afterwards, reverse back
    reverse_node_indices = []
    # loop through each object (strips) 
    for o in bpy.context.scene.objects:
        if 'Strip' in o.name: # focus on strip sets
            # use bmesh to calculate each strip's area
            bm = bmesh.new()
            bm.from_mesh(o.data)
            # calculate Strip's Area, if lower than 8, it's a flex part
            if (sum(f.calc_area() for f in bm.faces)) <= 8: # flex parts
                if '.' in o.name: # make sure the first strip not include
                    # use split to get the num after '.', append to array
                    reverse_node_indices.append(int(o.name.split('.')[1])) 
                else: # for the first stirp
                    reverse_node_indices.append(0)
            bm.free()
    # reverse the array to get the actual node_indices array
    node_indices = reverse_node_indices[::-1] 
    # use these nodes to add set bones position (head and tail)
       
    # add armature and a bone in between two geometry center
    bpy.ops.object.armature_add()    # add bone and armature
    arm_obj = bpy.data.objects['Armature'] # asisgn armature
    bpy.context.scene.objects.active = arm_obj # set  active
    bpy.ops.object.mode_set(mode = 'EDIT')     # edit   mode
    main_bone = arm_obj.data.edit_bones[0]     # assgin bone
    strip_name_pattern = 'Shape_IndexedTriangleStripSet.'
    # get the object's world position (with first two nodes)
    if node_indices[0] == 0: # the first strip is flex
        object1_name = 'Shape_IndexedTriangleStripSet'   # the first node 
        object2_name = strip_name_pattern + str(node_indices[1]).zfill(3)
    else:
        object1_name = strip_name_pattern + str(node_indices[0]).zfill(3)
        object2_name = strip_name_pattern + str(node_indices[1]).zfill(3)
    o1 = bpy.data.objects[object1_name]
    o2 = bpy.data.objects[object2_name]
    # set the bone's head and tail position
    main_bone.head = o1.matrix_world.translation
    main_bone.tail = o2.matrix_world.translation
    
    # add more bones based on nodes' position
    bone_pattern = 'Bone.'
    bone_index   = 1   # starts from 1
    for i in range(len(node_indices)):
        if i == 0: # since Bone's set, exclude it
            continue
        if i == len(node_indices) - 1 : # also exclude end node
            continue                    # to avoid the out of bound
        # set up name and create a new bone as child
        chi_name = bone_pattern + str(bone_index).zfill(3)
        chi_bone = arm_obj.data.edit_bones.new(chi_name)
        # get the object's world position (object = node)
        object1_name = strip_name_pattern + str(node_indices[i]).zfill(3)
        object2_name = strip_name_pattern + str(node_indices[i + 1]).zfill(3)
        o1 = bpy.data.objects[object1_name]
        o2 = bpy.data.objects[object2_name]
        # set the bone's head and tail position
        chi_bone.head = o1.matrix_world.translation
        chi_bone.tail = o2.matrix_world.translation
        # parent the child bone to main_bone
        chi_bone.parent = main_bone
        # set up for the next loop
        main_bone = chi_bone
        bone_index += 1
    bpy.ops.object.mode_set(mode = 'OBJECT') # go back to object mode

    # select objects and join them (note: we must active one first)
    bpy.context.scene.objects.active = bpy.data.objects['Shape_IndexedTriangleStripSet'] 
    bpy.ops.object.select_all(action='SELECT')
    arm_obj.select = False
    bpy.ops.object.join()
    bpy.ops.object.select_all(action='DESELECT')

    # automatic weights
    ''' select objects by their type '''
    # https://blender.stackexchange.com/questions/99664/how-can-i-select-all-objects-by-type-using-python
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            o.select = True # select object first then active the armature
    bpy.context.scene.objects.active = arm_obj    
    bpy.ops.object.parent_set(type = 'ARMATURE_AUTO')

    # add IK bone (add  one bone in EDIT mode and set IK in POSE mode)
    ''' extrude in EDIT mode '''
    bpy.ops.object.mode_set(mode = 'EDIT')         # go to edit mode
    bpy.ops.armature.select_all(action='DESELECT') # clear selections
    # get the last bone's index
    last_index = bone_index - 1
    bone_head = None  # for storing the head position
    bone_tail = None  # for storing the tail position
    for bone in arm_obj.data.edit_bones:
        if str(last_index).zfill(3) in bone.name:
            bone_head = bone.head
            bone_tail = bone.tail  
    # add an IK target_bone
    tar_name = "Target"
    tar_bone = arm_obj.data.edit_bones.new(tar_name)
    tar_bone.head = bone_tail
    tar_bone.tail = bone_tail + mathutils.Vector((1.0, 1.0, 1.0))
    ''' set IK in POSE mode '''
    bpy.ops.object.mode_set(mode = 'POSE')   # go to pose mode
    bpy.ops.pose.select_all(action='DESELECT') # clear selections
    for bone in arm_obj.pose.bones: 
        if str(last_index).zfill(3) in bone.name:
            bone.constraints.new('IK')
            bone.constraints['IK'].target    = arm_obj
            bone.constraints["IK"].subtarget = tar_name 
         
  
         
# check if the model is rigid or flexible
if set_num > 2:
    rigid()
else:
    flexible()