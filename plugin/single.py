"""Easy Export: quad mesh, particle distance 15, Texture topstitches, FBX, PBR bakes, topstitch mask.

Run from Plugins > Easy Export > single. Opens a tool window: paste the output folder,
press Run. UVs must already be arranged in the UV editor (0-1 tile).
"""
import importlib
import os
import sys
import traceback

import gui_api

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import pipeline_lib.gui_common  # noqa: E402
import pipeline_lib.png_flatten  # noqa: E402
import pipeline_lib.steps  # noqa: E402

# CLO keeps the interpreter alive between runs: reload so edits are picked up without restarting CLO.
importlib.reload(pipeline_lib.png_flatten)
importlib.reload(pipeline_lib.steps)
importlib.reload(pipeline_lib.gui_common)
steps = pipeline_lib.steps
common = pipeline_lib.gui_common

TITLE = common.TITLE
ui = {}


def progress(pct):
    gui_api.SetWidgetValue(ui["progress"], str(int(pct)))


def on_run():
    out_dir = common.validate_output_dir(gui_api.GetWidgetValue(ui["path"]))
    if not out_dir:
        return
    distance = common.validate_particle_distance(gui_api.GetWidgetValue(ui["distance"]))
    if distance is None:
        return
    name_input = gui_api.GetWidgetValue(ui["name"])
    name = steps.base_name(name_input)
    size = steps.texture_size()
    existing = [p for p in steps.output_files(out_dir, name) if os.path.exists(p)]
    msg = ("%s\n\nExport '%s' to:\n%s\n\nThis permanently sets all patterns to quads, particle distance to %g and "
           "topstitches to Texture.\nTexture size: %d px%s"
           % (common.UV_WARNING, name, out_dir, distance, size,
              "  (DEV OVERRIDE from dev_settings.json)" if size != steps.TEXTURE_SIZE else ""))
    if distance < steps.RECOMMENDED_MIN_DISTANCE:
        msg += "\n\nWARNING: particle distance below %g can cause performance issues." % steps.RECOMMENDED_MIN_DISTANCE
    if existing:
        msg += "\n\nThese files will be overwritten:\n" + "\n".join(os.path.basename(p) for p in existing)
    msg += "\n\nOnce you press 'Continue', please wait until the plugin fully finishes running."
    if not gui_api.AskConfirm(TITLE, msg, "Continue", "Cancel"):
        return

    common.save_settings(output_dir=out_dir, particle_distance=distance)
    log = common.window_log(ui["log"])
    gui_api.SetWidgetEnabled(ui["run"], False)
    progress(0)
    ok = False
    try:
        steps.run_pipeline(out_dir, name, distance, log, progress)
        ok = True
    except Exception as e:  # noqa: BLE001
        log("FAILED: %s" % e)
        log(traceback.format_exc())
    finally:
        log.save(os.path.join(out_dir, name + "_export_log.txt"))
        gui_api.SetWidgetEnabled(ui["run"], True)
    gui_api.AskConfirm(TITLE, ("Export finished:\n%s" % out_dir) if ok else
                       "Export FAILED - see the log in the window and %s_export_log.txt" % name, "OK", "Close")


def build_ui():
    settings = common.load_settings()
    project_name = steps.base_name()
    win = gui_api.CreateToolWindow(TITLE, 560, 520)
    gui_api.AddLabel(win, common.UV_WARNING)
    gui_api.AddLabel(win, "Output folder (paste a path):")
    ui["path"] = gui_api.AddTextInput(win, settings.get("output_dir", ""), "D:\\exports\\my_garment")
    gui_api.AddLabel(win, "File name (leave empty to use the project name):")
    ui["name"] = gui_api.AddTextInput(win, "", project_name)
    gui_api.AddLabel(win, common.DISTANCE_LABEL)
    saved = common.saved_particle_distance(settings)
    ui["distance"] = gui_api.AddTextInput(win, "%g" % saved, "%g" % steps.PARTICLE_DISTANCE)
    ui["run"] = gui_api.AddButton(win, "Run", on_run)
    ui["progress"] = gui_api.AddProgressBar(win, 0)
    ui["log"] = gui_api.AddTextArea(win, "", True)
    gui_api.ShowWindow(win)


if gui_api.IsGuiAvailable():
    build_ui()
else:
    print(TITLE + ": needs the CLO GUI (not available in headless mode)")
