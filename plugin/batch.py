"""Easy Export Batch: run the Easy Export steps on every .zprj in a folder.

Run from Plugins > Easy Export > batch. Each project is exported to its own subfolder of
the output folder, named after the .zprj file. The .zprj files are never saved, so they stay unchanged.
UVs must already be arranged in the UV editor (0-1 tile) in every project.
"""
import importlib
import os
import sys
import time
import traceback

import ApiTypes
import gui_api
import import_api
import utility_api

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

TITLE = common.TITLE + " Batch"
BATCH_LOG_NAME = "batch_export_log.txt"
ui = {}


def progress(pct):
    gui_api.SetWidgetValue(ui["progress"], str(int(pct)))


def validate_input_dir(raw):
    folder = os.path.normpath(raw.strip().strip('"')) if raw.strip() else ""
    if not os.path.isabs(folder) or not os.path.isdir(folder):
        gui_api.AskConfirm(TITLE, "Paste the absolute path of the folder with your .zprj files.", "OK", "Close")
        return None
    return folder


def find_projects(folder):
    """{export name: .zprj path} for the .zprj files directly inside folder. Subfolders are not searched."""
    paths = [os.path.join(folder, n) for n in sorted(os.listdir(folder), key=str.lower)
             if n.lower().endswith(".zprj")]
    projects = {}
    duplicates = []
    for path in paths:
        name = steps.base_name(os.path.basename(path))
        if name in projects:
            duplicates.append(os.path.basename(path))
        projects[name] = path
    return projects, duplicates


def is_exported(out_dir, name):
    return all(os.path.exists(p) for p in steps.output_files(os.path.join(out_dir, name), name))


def open_project(path):
    """Replace the open project, discarding its changes without asking. ImportFile would show a dialog."""
    option = ApiTypes.ImportZPRJOption()
    option.bAppend = False
    option.bLoadGarment = True
    option.bLoadAvatar = True
    option.bLoadSceneAndProps = True
    option.bLoadRenderProperties = True
    if not import_api.ImportZprj(path, option):
        # The previous project is still open: exporting now would write the wrong garment under this name.
        raise steps.PipelineError("could not open %s" % path)


def export_project(path, out_dir, name, distance, log, file_progress):
    open_project(path)
    project_dir = os.path.join(out_dir, name)
    os.makedirs(project_dir, exist_ok=True)
    steps.run_pipeline(project_dir, name, distance, log, file_progress)


def run_batch(projects, out_dir, distance, log):
    """Export each project. One failure doesn't stop the others. Returns (exported, failed, skipped) name lists."""
    exported, failed, skipped = [], [], []
    batch_log = os.path.join(out_dir, BATCH_LOG_NAME)
    for i, (name, path) in enumerate(projects.items()):
        log("--- %d/%d %s" % (i + 1, len(projects), os.path.basename(path)))
        if is_exported(out_dir, name):
            log("Skipped: already exported")
            skipped.append(name)
        else:
            def file_progress(pct, done=i):
                progress((done + pct / 100.0) * 100.0 / len(projects))

            first_line = len(log.lines) - 1
            try:
                export_project(path, out_dir, name, distance, log, file_progress)
                exported.append(name)
            except Exception as e:  # noqa: BLE001
                log("FAILED: %s" % e)
                log(traceback.format_exc())
                failed.append(name)
            project_dir = os.path.join(out_dir, name)
            if os.path.isdir(project_dir):
                log.save(os.path.join(project_dir, name + "_export_log.txt"), first_line)
        progress((i + 1) * 100.0 / len(projects))
        log.save(batch_log)  # after every project, so a crash still leaves a log
    return exported, failed, skipped


def confirm_run(projects, in_dir, out_dir, distance):
    skipping = sum(is_exported(out_dir, name) for name in projects)
    msg = ("%s\nEvery project must be ready: the batch can't stop to fix UVs.\n\nExport %d projects from:\n%s\n\nto "
           "one subfolder each in:\n%s\n\nEach export uses quads, particle distance %g and Texture topstitches.\n"
           "Texture size: %d px. The .zprj files are not saved."
           % (common.UV_WARNING, len(projects), in_dir, out_dir, distance, steps.texture_size()))
    if distance < steps.RECOMMENDED_MIN_DISTANCE:
        msg += "\n\nWARNING: particle distance below %g can cause performance issues." % steps.RECOMMENDED_MIN_DISTANCE
    if skipping:
        msg += ("\n\n%d already exported and will be skipped. To export one again, delete its subfolder first."
                % skipping)
    msg += "\n\nThe project open now will be closed WITHOUT saving."
    if utility_api.CheckZPRJForUnsavedChanges():
        msg += "\nWARNING: it has unsaved changes, which will be lost. Cancel and save it first if you need them."
    msg += "\n\nOnce you press 'Continue', please wait until the batch fully finishes running."
    return gui_api.AskConfirm(TITLE, msg, "Continue", "Cancel")


def on_run():
    in_dir = validate_input_dir(gui_api.GetWidgetValue(ui["input"]))
    if not in_dir:
        return
    projects, duplicates = find_projects(in_dir)
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
    if not confirm_run(projects, in_dir, out_dir, distance):
        return

    common.save_settings(input_dir=in_dir, output_dir=out_dir, particle_distance=distance)
    log = common.RunLog(ui["log"])
    gui_api.SetWidgetEnabled(ui["run"], False)
    progress(0)
    t0 = time.time()
    exported, failed, skipped = [], [], []
    try:
        log("Batch: %d projects from %s -> %s" % (len(projects), in_dir, out_dir))
        exported, failed, skipped = run_batch(projects, out_dir, distance, log)
        summary = "%d exported, %d failed, %d skipped" % (len(exported), len(failed), len(skipped))
        if failed:
            summary += "\n\nFailed:\n" + "\n".join(failed)
        log("Batch finished in %.1fs: %s" % (time.time() - t0, summary))
    except Exception as e:  # noqa: BLE001
        summary = "Batch stopped: %s" % e
        log("FAILED: %s" % e)
        log(traceback.format_exc())
    finally:
        # The last project has changes that shouldn't be saved over its .zprj by accident.
        utility_api.NewProject()
        log.save(os.path.join(out_dir, BATCH_LOG_NAME))
        gui_api.SetWidgetEnabled(ui["run"], True)
    gui_api.AskConfirm(TITLE, "%s\n\nLog: %s" % (summary, os.path.join(out_dir, BATCH_LOG_NAME)), "OK", "Close")


def build_ui():
    settings = common.load_settings()
    win = gui_api.CreateToolWindow(TITLE, 560, 520)
    gui_api.AddLabel(win, common.UV_WARNING)
    gui_api.AddLabel(win, "Folder with .zprj files (paste a path):")
    ui["input"] = gui_api.AddTextInput(win, settings.get("input_dir", ""), "D:\\clo_projects\\collection")
    gui_api.AddLabel(win, "Output folder (paste a path), each project gets a subfolder:")
    ui["output"] = gui_api.AddTextInput(win, settings.get("output_dir", ""), "D:\\exports\\collection")
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
