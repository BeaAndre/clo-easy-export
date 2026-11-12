# ------------------------------ EDIT THESE ------------------------------
INPUT_DIR = r"D:\clo_projects\my_collection"   # absolute path of the folder with the .zprj files
OUTPUT_DIR = r"D:\exports\my_collection"       # absolute path; created if missing
PARTICLE_DISTANCE = 15.0                        # 10 or higher is recommended
AUTO_UV = False                                 # True = if any pattern is outside 0-1, reset and pack all UVs first
SAVE_AUTO_UVS = False                           # True = save packed UVs over the .zprj (only works with AUTO_UV)
# Folder that contains pipeline_lib (used if this file's own folder can't be detected):
PLUGIN_DIR = r"C:\Users\Public\Documents\CLO\Plugins\clo-easy-export-main\plugin"
# ------------------------------------------------------------------------

# Easy Export Batch - NO-GUI version, for CLO builds without the gui_api module (e.g. 2026.1.224).
#
# Same batch as 2_batch.py: exports every .zprj directly inside INPUT_DIR to its own subfolder of
# OUTPUT_DIR, named after the .zprj file. The settings are the plain variables above instead of a window.
#
# HOW TO USE
#   1. Arrange the UVs in the UV Editor (0-1 tile) in every project and save them, or set AUTO_UV = True.
#   2. Save the project that's open in CLO. It will be closed WITHOUT saving, and there is no warning.
#   3. Drag this file into the CLO 3D window. CLO opens it in its own script editor.
#   4. In that editor, edit INPUT_DIR, OUTPUT_DIR and PARTICLE_DISTANCE (and optionally AUTO_UV /
#      SAVE_AUTO_UVS) above.
#   5. Run it from CLO's script editor. There is no way to stop it once it has started.
#   6. Check <OUTPUT_DIR>\batch_export_log.txt (or the Python console) for the result.
#
# AUTO_UV: if any pattern in a project is outside the 0-1 tile, all its UVs are reset to the 2D arrangement
# and packed into 0-1 before exporting. Projects where every pattern already fits are left alone.
# Buttons outside 0-1 aren't detected.
# SAVE_AUTO_UVS: a project that AUTO_UV packed is saved over its .zprj with the new UVs and nothing else.
# This OVERWRITES those .zprj files. It does nothing unless AUTO_UV is True too.
#
# Otherwise the .zprj files are never saved. The last project stays open with the export changes, so don't
# save it or they go into its .zprj. Projects that are already fully exported are skipped: to export
# one again, delete its subfolder first.

import importlib
import os
import sys
import traceback

PLACEHOLDER_INPUT = r"D:\clo_projects\my_collection"
PLACEHOLDER_OUTPUT = r"D:\exports\my_collection"
EMERGENCY_LOG = r"C:\Users\Public\clo_easy_export_run.txt"


def write_emergency_log(line):
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


def clean_dir(raw, setting, placeholder):
    folder = os.path.normpath(raw.strip().strip('"')) if raw.strip() else ""
    if not folder or folder == os.path.normpath(placeholder):
        raise RuntimeError("Edit %s at the top of this file first." % setting)
    if not os.path.isabs(folder):
        raise RuntimeError("%s must be an absolute path, e.g. D:\\exports\\collection" % setting)
    return folder


def run():
    here = find_plugin_dir()
    if here not in sys.path:
        sys.path.insert(0, here)

    import pipeline_lib.batch_core
    import pipeline_lib.png_flatten
    import pipeline_lib.steps
    importlib.reload(pipeline_lib.png_flatten)
    importlib.reload(pipeline_lib.steps)
    importlib.reload(pipeline_lib.batch_core)
    steps = pipeline_lib.steps
    core = pipeline_lib.batch_core

    log = steps.RunLog(lambda lines: write_emergency_log(lines[-1]))
    log("=== Easy Export Batch (no-GUI) started ===")

    in_dir = clean_dir(INPUT_DIR, "INPUT_DIR", PLACEHOLDER_INPUT)
    if not os.path.isdir(in_dir):
        raise RuntimeError("INPUT_DIR does not exist: %s" % in_dir)
    out_dir = clean_dir(OUTPUT_DIR, "OUTPUT_DIR", PLACEHOLDER_OUTPUT)
    distance = float(PARTICLE_DISTANCE)
    if distance <= 0:
        raise RuntimeError("PARTICLE_DISTANCE must be greater than 0.")
    projects, duplicates = core.find_projects(in_dir)
    if not projects:
        raise RuntimeError("No .zprj files in %s" % in_dir)
    if duplicates:
        raise RuntimeError("These files would export to the same name as another file. Rename them first: %s"
                           % ", ".join(duplicates))

    if distance < steps.RECOMMENDED_MIN_DISTANCE:
        log("WARNING: particle distance below %g can cause performance issues." % steps.RECOMMENDED_MIN_DISTANCE)
    auto_uv = AUTO_UV is True
    save_uvs = auto_uv and SAVE_AUTO_UVS is True
    if auto_uv:
        log("Auto-UV is on: if any pattern is outside 0-1, all UVs are reset and packed into 0-1.")
    if save_uvs:
        log("Save auto-UVs is on: packed projects are saved over their .zprj with the new UVs.")
    elif SAVE_AUTO_UVS is True:
        log("WARNING: SAVE_AUTO_UVS does nothing because AUTO_UV is off. The .zprj files are not saved.")

    os.makedirs(out_dir, exist_ok=True)
    try:
        log(core.summary(*core.run_batch(projects, in_dir, out_dir, distance, log, auto_uv=auto_uv,
                                         save_uvs=save_uvs)))
    except Exception:  # noqa: BLE001
        log("FAILED:\n" + traceback.format_exc())
        log.save(os.path.join(out_dir, core.BATCH_LOG_NAME))


try:
    run()
except Exception:  # noqa: BLE001
    message = "FAILED:\n" + traceback.format_exc()
    print(message)
    write_emergency_log(message)
