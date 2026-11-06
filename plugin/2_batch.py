"""Easy Export Batch: run the Easy Export steps on every .zprj in a folder.

Run from Plugins > Easy Export > 2_batch. Each project is exported to its own subfolder of
the output folder, named after the .zprj file. The .zprj files are never saved, so they stay unchanged.
UVs must already be arranged in the UV editor (0-1 tile) in every project.
"""
import importlib
import os
import sys
import traceback

import gui_api

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import pipeline_lib.batch_core  # noqa: E402
import pipeline_lib.gui_common  # noqa: E402
import pipeline_lib.png_flatten  # noqa: E402
import pipeline_lib.steps  # noqa: E402

# CLO keeps the interpreter alive between runs: reload so edits are picked up without restarting CLO.
importlib.reload(pipeline_lib.png_flatten)
importlib.reload(pipeline_lib.steps)
importlib.reload(pipeline_lib.batch_core)
importlib.reload(pipeline_lib.gui_common)
steps = pipeline_lib.steps
core = pipeline_lib.batch_core
common = pipeline_lib.gui_common

TITLE = common.TITLE + " Batch"
ui = {}


def progress(pct):
    gui_api.SetWidgetValue(ui["progress"], str(int(pct)))


def validate_input_dir(raw):
    folder = os.path.normpath(raw.strip().strip('"')) if raw.strip() else ""
    if not os.path.isabs(folder) or not os.path.isdir(folder):
        gui_api.AskConfirm(TITLE, "Paste the absolute path of the folder with your .zprj files.", "OK", "Close")
        return None
    return folder


def confirm_run(projects, in_dir, out_dir, distance, auto_uv):
    skipping = sum(core.is_exported(out_dir, name) for name in projects)
    uv_text = (common.AUTO_UV_NOTICE if auto_uv
               else common.UV_WARNING + "\nEvery project must be ready: the batch can't stop to fix UVs.")
    msg = ("%s\n\nExport %d projects from:\n%s\n\nto one subfolder each in:\n%s\n\n"
           "Each export uses quads, particle distance %g and Texture topstitches.\n"
           "Texture size: %d px. The .zprj files are not saved."
           % (uv_text, len(projects), in_dir, out_dir, distance, steps.texture_size()))
    if distance < steps.RECOMMENDED_MIN_DISTANCE:
        msg += "\n\nWARNING: particle distance below %g can cause performance issues." % steps.RECOMMENDED_MIN_DISTANCE
    if skipping:
        msg += ("\n\n%d already exported and will be skipped. To export one again, delete its subfolder first."
                % skipping)
    if skipping < len(projects):
        msg += "\n\nThe project open now will be closed WITHOUT saving. Cancel and save it first if you need to."
    msg += "\n\nOnce you press 'Continue', please wait until the batch fully finishes running."
    return gui_api.AskConfirm(TITLE, msg, "Continue", "Cancel")


def on_run():
    in_dir = validate_input_dir(gui_api.GetWidgetValue(ui["input"]))
    if not in_dir:
        return
    projects, duplicates = core.find_projects(in_dir)
    if not projects:
        gui_api.AskConfirm(TITLE, "No .zprj files in:\n%s" % in_dir, "OK", "Close")
        return
    if duplicates:
        gui_api.AskConfirm(TITLE, "These files would export to the same name as another file. Rename them first:\n"
                           + "\n".join(duplicates), "OK", "Close")
        return
    out_dir = common.validate_output_dir(gui_api.GetWidgetValue(ui["output"]))
    if not out_dir:
        return
    distance = common.validate_particle_distance(gui_api.GetWidgetValue(ui["distance"]))
    if distance is None:
        return
    auto_uv = common.is_checked(ui["auto_uv"])
    if not confirm_run(projects, in_dir, out_dir, distance, auto_uv):
        return

    common.save_settings(input_dir=in_dir, output_dir=out_dir, particle_distance=distance, auto_uv=auto_uv)
    log = common.window_log(ui["log"])
    gui_api.SetWidgetEnabled(ui["run"], False)
    progress(0)
    try:
        result = core.summary(*core.run_batch(projects, in_dir, out_dir, distance, log, progress, auto_uv))
    except Exception as e:  # noqa: BLE001
        result = "Batch stopped: %s" % e
        log("FAILED: %s" % e)
        log(traceback.format_exc())
        log.save(os.path.join(out_dir, core.BATCH_LOG_NAME))
    finally:
        gui_api.SetWidgetEnabled(ui["run"], True)
    gui_api.AskConfirm(TITLE, "%s\n\nLog: %s" % (result, os.path.join(out_dir, core.BATCH_LOG_NAME)), "OK", "Close")


def build_ui():
    settings = common.load_settings()
    win = gui_api.CreateToolWindow(TITLE, 560, 520)
    gui_api.AddLabel(win, common.UV_WINDOW_NOTE)
    gui_api.AddLabel(win, "Folder with .zprj files (paste a path):")
    ui["input"] = gui_api.AddTextInput(win, settings.get("input_dir", ""), "D:\\clo_projects\\collection")
    gui_api.AddLabel(win, "Output folder (paste a path), each project gets a subfolder:")
    ui["output"] = gui_api.AddTextInput(win, settings.get("output_dir", ""), "D:\\exports\\collection")
    gui_api.AddLabel(win, common.DISTANCE_LABEL)
    saved = common.saved_particle_distance(settings)
    ui["distance"] = gui_api.AddTextInput(win, "%g" % saved, "%g" % steps.PARTICLE_DISTANCE)
    ui["auto_uv"] = gui_api.AddCheckBox(win, common.AUTO_UV_LABEL, common.saved_auto_uv(settings))
    ui["run"] = gui_api.AddButton(win, "Run", on_run)
    ui["progress"] = gui_api.AddProgressBar(win, 0)
    ui["log"] = gui_api.AddTextArea(win, "", True)
    gui_api.ShowWindow(win)


if gui_api.IsGuiAvailable():
    build_ui()
else:
    print(TITLE + ": needs the CLO GUI (not available in headless mode)")
