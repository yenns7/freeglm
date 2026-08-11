"""Standalone Blender render script (runs inside Blender's Python).

Usage: blender --background --python _blender_render.py -- <model_path> <output_dir> [max_views]
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

VIEWS = [
    ("Perspective", 30, 45),
    ("Front", 0, 0),
    ("Top", 90, 0),
]

RESOLUTION = 1200
SAMPLES = 64


def _clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if not block.users:
            bpy.data.meshes.remove(block)


def _import_model(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=path)
    elif ext in (".step", ".stp"):
        raise RuntimeError(f"STEP import not supported by Blender natively: {path}")
    else:
        raise RuntimeError(f"Unsupported format: {ext}")

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh objects after import")
    return meshes


def _bbox(meshes):
    mins = Vector((float("inf"),) * 3)
    maxs = Vector((float("-inf"),) * 3)
    for obj in meshes:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            for i in range(3):
                mins[i] = min(mins[i], world[i])
                maxs[i] = max(maxs[i], world[i])
    center = (mins + maxs) / 2
    scale = (maxs - mins).length
    return center, max(scale, 0.001)


def _setup_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = False
    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"


def _setup_world():
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    output = nodes.new("ShaderNodeOutputWorld")
    world.node_tree.links.new(bg.outputs["Background"], output.inputs["Surface"])


def _setup_lighting(center, scale):
    d = scale * 2.5

    bpy.ops.object.light_add(type="SUN", location=(d, -d, d))
    key = bpy.context.active_object
    key.data.energy = 3.0
    key.rotation_euler = (Vector(center) - Vector((d, -d, d))).to_track_quat("-Z", "Y").to_euler()

    bpy.ops.object.light_add(type="SUN", location=(-d, -d * 0.5, d * 0.8))
    fill = bpy.context.active_object
    fill.data.energy = 1.5
    fill.rotation_euler = (Vector(center) - Vector((-d, -d * 0.5, d * 0.8))).to_track_quat("-Z", "Y").to_euler()

    bpy.ops.object.light_add(type="SUN", location=(0, d, -d * 0.3))
    rim = bpy.context.active_object
    rim.data.energy = 1.0
    rim.rotation_euler = (Vector(center) - Vector((0, d, -d * 0.3))).to_track_quat("-Z", "Y").to_euler()


def _camera_pose(center, scale, elev_deg, azim_deg):
    distance = scale * 2.0
    elev = math.radians(elev_deg)
    azim = math.radians(azim_deg)
    x = distance * math.cos(elev) * math.sin(azim)
    y = -distance * math.cos(elev) * math.cos(azim)
    z = distance * math.sin(elev)
    cam_loc = center + Vector((x, y, z))

    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    direction = center - cam_loc
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    bpy.context.scene.camera = cam
    return cam


def main():
    argv = sys.argv
    sep = argv.index("--") if "--" in argv else len(argv)
    args = argv[sep + 1 :]
    if len(args) < 2:
        print(json.dumps({"error": "Usage: blender --background --python script.py -- <model> <outdir> [max_views]"}))
        sys.exit(1)

    model_path = args[0]
    output_dir = args[1]
    max_views = int(args[2]) if len(args) > 2 else len(VIEWS)

    os.makedirs(output_dir, exist_ok=True)

    _clear_scene()
    meshes = _import_model(model_path)
    center, scale = _bbox(meshes)

    _setup_render()
    _setup_world()
    _setup_lighting(center, scale)

    outputs = []
    for title, elev, azim in VIEWS[:max_views]:
        cam = _camera_pose(center, scale, elev, azim)
        out_path = os.path.join(output_dir, f"{title.lower()}.png")
        bpy.context.scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        outputs.append({"title": title, "path": out_path})
        bpy.data.objects.remove(cam, do_unlink=True)

    total_verts = sum(len(o.data.vertices) for o in meshes if o.type == "MESH" and o.data)
    total_faces = sum(len(o.data.polygons) for o in meshes if o.type == "MESH" and o.data)

    print(
        json.dumps(
            {
                "outputs": outputs,
                "total_verts": total_verts,
                "total_faces": total_faces,
            }
        )
    )


if __name__ == "__main__":
    main()
