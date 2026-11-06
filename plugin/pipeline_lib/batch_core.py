"""Batch logic shared by 2_batch.py and 4_older_batch.py. Must not import gui_api: older CLO builds don't have it."""
import os
import time
import traceback

import ApiTypes
import import_api

from . import steps

BATCH_LOG_NAME = "batch_export_log.txt"


def find_projects(folder):
    """Returns ({export name: .zprj path}, [files whose name is already taken]).
    Only looks at the .zprj files directly inside folder, not in subfolders."""
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


def run_batch(projects, in_dir, out_dir, distance, log, progress=lambda pct: None, auto_uv=False,
              save_uvs=False):
    """Export each project with a steps.RunLog as log. One failure doesn't stop the others.
    With save_uvs, a project that Auto-UV packed is saved over its .zprj, with no other changes.
    Returns (exported, failed, skipped) name lists."""
    t0 = time.time()
    exported, failed, skipped = [], [], []
    batch_log = os.path.join(out_dir, BATCH_LOG_NAME)
    log("Batch: %d projects from %s -> %s" % (len(projects), in_dir, out_dir))
    try:
        for i, (name, path) in enumerate(projects.items()):
            log("--- %d/%d %s" % (i + 1, len(projects), os.path.basename(path)))
            if is_exported(out_dir, name):
                log("Skipped: already exported")
                skipped.append(name)
            else:
                def file_progress(pct, done=i):
                    progress((done + pct / 100.0) * 100.0 / len(projects))

                first_line = len(log.lines) - 1
                project_dir = os.path.join(out_dir, name)
                try:
                    open_project(path)
                    os.makedirs(project_dir, exist_ok=True)
                    steps.run_pipeline(project_dir, name, distance, log, file_progress, auto_uv,
                                       path if save_uvs else None)
                    exported.append(name)
                except Exception as e:  # noqa: BLE001
                    log("FAILED: %s" % e)
                    log(traceback.format_exc())
                    failed.append(name)
                if os.path.isdir(project_dir):
                    log.save(os.path.join(project_dir, name + "_export_log.txt"), first_line)
            progress((i + 1) * 100.0 / len(projects))
            log.save(batch_log)  # after every project, so a crash still leaves a log
        log("Batch finished in %.1fs: %s" % (time.time() - t0, summary(exported, failed, skipped)))
    finally:
        log.save(batch_log)
    return exported, failed, skipped


def summary(exported, failed, skipped):
    text = "%d exported, %d failed, %d skipped" % (len(exported), len(failed), len(skipped))
    if failed:
        text += "\n\nFailed:\n" + "\n".join(failed)
    if exported:
        text += "\n\nThe last project is still open with the export changes. Don't save it, or they go into its .zprj."
    return text
