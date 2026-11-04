# ------------------------------ EDIT THESE ------------------------------
OUTPUT_DIR = r"D:\exports\my_garment"   # absolute path; created if missing
FILE_NAME = ""                           # empty = use the project name
PARTICLE_DISTANCE = 15.0                 # 10 or higher is recommended
# Folder that contains pipeline_lib (used if this file's own folder can't be detected):
PLUGIN_DIR = r"C:\Users\Public\Documents\CLO\Plugins\clo-easy-export-main\plugin"
# ------------------------------------------------------------------------

# Easy Export - NO-GUI version, for CLO builds without the gui_api module (e.g. 2026.1.224).
#
# Same pipeline as export_pipeline.py (quad mesh, particle distance, Texture topstitches, FBX,
# PBR bakes, topstitch mask), but the settings are the plain variables above instead of a window.
#
# HOW TO USE
#   1. Arrange the UVs in the UV Editor (0-1 tile) first.
#   2. Edit OUTPUT_DIR (and optionally FILE_NAME / PARTICLE_DISTANCE) above.
#   3. Run it: drag this file into the CLO 3D window, or open it in Edit > Python Script and run it.
#   4. Check <OUTPUT_DIR>\<name>_export_log.txt (or the Python console) for the result.
#
# WARNING: this permanently changes the project's mesh type, particle distance and topstitch
# settings. Save a copy of your project first.

import importlib
import os
import sys
import time
import traceback

PLACEHOLDER_DIR = r"D:\exports\my_garment"
RECOMMENDED_MIN_DISTANCE = 10.0
EMERGENCY_LOG = r"C:\Users\Public\clo_easy_export_run.txt"

lines = []


def log(msg):
    line = "%s  %s" % (time.strftime("%H:%M:%S"), msg)
    print(line)
    lines.append(line)
    try:
        with open(EMERGENCY_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def find_plugin_dir():
    candidates = []
    try:
        candidates.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass
    candidates.append(PLUGIN_DIR)
    for c in candidates:
        if os.path.isdir(os.path.join(c, "pipeline_lib")):
            return c
    raise RuntimeError("pipeline_lib folder not found. Looked in: %s" % candidates)


def run():
    log("=== Easy Export (no-GUI) started ===")
    here = find_plugin_dir()
    if here not in sys.path:
        sys.path.insert(0, here)

    import pipeline_lib.png_flatten
    import pipeline_lib.steps
    importlib.reload(pipeline_lib.png_flatten)
    importlib.reload(pipeline_lib.steps)
    steps = pipeline_lib.steps

    out_dir = os.path.normpath(OUTPUT_DIR.strip().strip('"')) if OUTPUT_DIR.strip() else ""
    if not out_dir or out_dir == os.path.normpath(PLACEHOLDER_DIR):
        raise RuntimeError("Edit OUTPUT_DIR at the top of this file first.")
    if not os.path.isabs(out_dir):
        raise RuntimeError("OUTPUT_DIR must be an absolute path, e.g. D:\\exports\\shirt")
    distance = float(PARTICLE_DISTANCE)
    if distance <= 0:
        raise RuntimeError("PARTICLE_DISTANCE must be greater than 0.")
    if distance < RECOMMENDED_MIN_DISTANCE:
        log("WARNING: particle distance below %g can cause performance issues." % RECOMMENDED_MIN_DISTANCE)

    os.makedirs(out_dir, exist_ok=True)
    name = steps.base_name(FILE_NAME)
    tex_dir = os.path.join(out_dir, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    size = steps.texture_size()

    ok = False
    t0 = time.time()
    try:
        log("Export '%s' -> %s (texture size %d, particle distance %g)" % (name, out_dir, size, distance))
        log("1/6 " + steps.set_quad_mesh())
        log("2/6 " + steps.set_particle_distance(distance))
        log("3/6 " + steps.set_topstitches_texture())
        log("4/6 FBX: " + steps.export_fbx(out_dir, name))
        for p in steps.bake_pbr(tex_dir, name):
            log("5/6 baked " + os.path.basename(p))
        backup, warning = steps.backup_colours(name)
        log("    original colours saved to: " + backup)
        if warning:
            log("    WARNING: " + warning)
        final, method, n_faces, n_lines = steps.bake_topstitch_mask(tex_dir, name)
        log("6/6 baked %s (flattened via %s); %d fabric faces + %d stitch lines restored and verified"
            % (os.path.basename(final), method, n_faces, n_lines))
        ok = True
        log("Done in %.1fs" % (time.time() - t0))
    except Exception:  # noqa: BLE001
        log("FAILED:\n" + traceback.format_exc())
    finally:
        try:
            with open(os.path.join(out_dir, name + "_export_log.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except OSError:
            pass
    return ok


try:
    run()
except Exception:  # noqa: BLE001
    log("FAILED:\n" + traceback.format_exc())
