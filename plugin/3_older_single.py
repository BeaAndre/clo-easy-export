# ------------------------------ EDIT THESE ------------------------------
OUTPUT_DIR = r"D:\exports\my_garment"   # absolute path; created if missing
FILE_NAME = ""                           # empty = use the project name
PARTICLE_DISTANCE = 15.0                 # 10 or higher is recommended
# Folder that contains pipeline_lib (used if this file's own folder can't be detected):
PLUGIN_DIR = r"C:\Users\Public\Documents\CLO\Plugins\clo-easy-export-main\plugin"
# ------------------------------------------------------------------------

# Easy Export - NO-GUI version, for CLO builds without the gui_api module (e.g. 2026.1.224).
#
# Same pipeline as 1_single.py (quad mesh, particle distance, Texture topstitches, FBX,
# PBR bakes, topstitch mask), but the settings are the plain variables above instead of a window.
#
# HOW TO USE
#   1. Arrange the UVs in the UV Editor (0-1 tile) first.
#   2. Drag this file into the CLO 3D window. CLO opens it in its own script editor.
#   3. In that editor, edit OUTPUT_DIR (and optionally FILE_NAME / PARTICLE_DISTANCE) above.
#   4. Run it from CLO's script editor.
#   5. Check <OUTPUT_DIR>\<name>_export_log.txt (or the Python console) for the result.
#
# WARNING: this permanently changes the project's mesh type, particle distance and topstitch
# settings. Save a copy of your project first.

import importlib
import os
import sys
import time
import traceback

PLACEHOLDER_DIR = r"D:\exports\my_garment"
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
    if distance < steps.RECOMMENDED_MIN_DISTANCE:
        log("WARNING: particle distance below %g can cause performance issues." % steps.RECOMMENDED_MIN_DISTANCE)

    os.makedirs(out_dir, exist_ok=True)
    name = steps.base_name(FILE_NAME)

    ok = False
    try:
        steps.run_pipeline(out_dir, name, distance, log)
        ok = True
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
