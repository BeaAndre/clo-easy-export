"""Export Pipeline: quad mesh, particle distance 15, Texture topstitches, FBX, PBR bakes, topstitch mask.

Run from Plugins > Export Pipeline > export_pipeline. Opens a tool window: paste the output folder,
press Run. UVs must already be arranged in the UV editor (0-1 tile).
"""
import importlib
import json
import os
import sys
import time
import traceback

import gui_api

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import pipeline_lib.png_flatten  # noqa: E402
import pipeline_lib.steps  # noqa: E402

# CLO keeps the interpreter alive between runs: reload so edits are picked up without restarting CLO.
importlib.reload(pipeline_lib.png_flatten)
importlib.reload(pipeline_lib.steps)
steps = pipeline_lib.steps

TITLE = "Export Pipeline"
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".clo_export_pipeline.json")
ui = {}


UV_WARNING = "IMPORTANT: Arrange UVs in the UV Editor (0-1 tile) before running."
RECOMMENDED_MIN_DISTANCE = 10.0


def load_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(**values):
    data = load_settings()
    data.update(values)
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


class RunLog:
    def __init__(self):
        self.lines = []

    def __call__(self, msg):
        line = "%s  %s" % (time.strftime("%H:%M:%S"), msg)
        print(line)
        self.lines.append(line)
        gui_api.SetWidgetValue(ui["log"], "\n".join(self.lines))

    def save(self, path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.lines) + "\n")
        except OSError:
            pass


def progress(pct):
    gui_api.SetWidgetValue(ui["progress"], str(int(pct)))


def validate_output_dir(raw):
    out_dir = os.path.normpath(raw.strip().strip('"')) if raw.strip() else ""
    if not out_dir:
        gui_api.AskConfirm(TITLE, "Paste an output folder path first.", "OK", "Close")
        return None
    if not os.path.isabs(out_dir):
        gui_api.AskConfirm(TITLE, "Use an absolute path (e.g. D:\\exports\\shirt).", "OK", "Close")
        return None
    if not os.path.isdir(out_dir):
        if not gui_api.AskConfirm(TITLE, "Folder does not exist:\n%s\n\nCreate it?" % out_dir, "Create", "Cancel"):
            return None
        try:
            os.makedirs(out_dir)
        except OSError as e:
            gui_api.AskConfirm(TITLE, "Could not create folder:\n%s" % e, "OK", "Close")
            return None
    return out_dir


def validate_particle_distance(raw):
    try:
        value = float(str(raw).strip().replace(",", "."))
    except ValueError:
        value = 0.0
    if value <= 0:
        gui_api.AskConfirm(TITLE, "Particle distance must be a number greater than 0 (e.g. 15).", "OK", "Close")
        return None
    return value


def on_run():
    out_dir = validate_output_dir(gui_api.GetWidgetValue(ui["path"]))
    if not out_dir:
        return
    distance = validate_particle_distance(gui_api.GetWidgetValue(ui["distance"]))
    if distance is None:
        return
    name_input = gui_api.GetWidgetValue(ui["name"])
    name = steps.base_name(name_input)
    tex_dir = os.path.join(out_dir, "textures")
    size = steps.texture_size()
    targets = [os.path.join(out_dir, name + ".fbx")] + [
        os.path.join(tex_dir, "%s_%s.png" % (name, m)) for m in ("diffuse", "normal", "roughness", "topstitch")]
    existing = [p for p in targets if os.path.exists(p)]
    msg = ("%s\n\nExport '%s' to:\n%s\n\nThis permanently sets all patterns to quads, particle distance to %g and "
           "topstitches to Texture.\nTexture size: %d px%s"
           % (UV_WARNING, name, out_dir, distance, size,
              "  (DEV OVERRIDE from dev_settings.json)" if size != steps.TEXTURE_SIZE else ""))
    if distance < RECOMMENDED_MIN_DISTANCE:
        msg += "\n\nWARNING: particle distance below %g can cause performance issues." % RECOMMENDED_MIN_DISTANCE
    if existing:
        msg += "\n\nThese files will be overwritten:\n" + "\n".join(os.path.basename(p) for p in existing)
    msg += "\n\nOnce you press 'Continue', please wait until the plugin fully finishes running."
    if not gui_api.AskConfirm(TITLE, msg, "Continue", "Cancel"):
        return

    save_settings(output_dir=out_dir, particle_distance=distance)
    os.makedirs(tex_dir, exist_ok=True)
    log = RunLog()
    gui_api.SetWidgetEnabled(ui["run"], False)
    progress(0)
    t0 = time.time()
    ok = False
    try:
        log("Export '%s' -> %s (texture size %d, particle distance %g)" % (name, out_dir, size, distance))
        log("1/6 " + steps.set_quad_mesh())
        progress(8)
        log("2/6 " + steps.set_particle_distance(distance))
        progress(15)
        log("3/6 " + steps.set_topstitches_texture())
        progress(22)
        log("4/6 FBX: " + steps.export_fbx(out_dir, name))
        progress(40)
        for p in steps.bake_pbr(tex_dir, name):
            log("5/6 baked " + os.path.basename(p))
        progress(70)
        backup, warning = steps.backup_colours(name)
        log("    original colours saved to: " + backup)
        if warning:
            log("    WARNING: " + warning)
        final, method, n_faces, n_lines = steps.bake_topstitch_mask(tex_dir, name)
        log("6/6 baked %s (flattened via %s); %d fabric faces + %d stitch lines restored and verified"
            % (os.path.basename(final), method, n_faces, n_lines))
        progress(100)
        ok = True
        log("Done in %.1fs" % (time.time() - t0))
    except Exception as e:  # noqa: BLE001
        log("FAILED: %s" % e)
        log(traceback.format_exc())
    finally:
        log.save(os.path.join(out_dir, name + "_export_log.txt"))
        gui_api.SetWidgetEnabled(ui["run"], True)
    gui_api.AskConfirm(TITLE, ("Export finished:\n%s" % out_dir) if ok else
                       "Export FAILED - see the log in the window and %s_export_log.txt" % name, "OK", "Close")


def build_ui():
    settings = load_settings()
    project_name = steps.base_name()
    win = gui_api.CreateToolWindow(TITLE, 560, 520)
    gui_api.AddLabel(win, UV_WARNING)
    gui_api.AddLabel(win, "Output folder (paste a path):")
    ui["path"] = gui_api.AddTextInput(win, settings.get("output_dir", ""), "D:\\exports\\my_garment")
    gui_api.AddLabel(win, "File name (leave empty to use the project name):")
    ui["name"] = gui_api.AddTextInput(win, "", project_name)
    gui_api.AddLabel(win, "Particle distance (values under %g can cause performance issues):"
                     % RECOMMENDED_MIN_DISTANCE)
    saved = settings.get("particle_distance", steps.PARTICLE_DISTANCE)
    if not isinstance(saved, (int, float)) or saved <= 0:
        saved = steps.PARTICLE_DISTANCE
    ui["distance"] = gui_api.AddTextInput(win, "%g" % saved, "%g" % steps.PARTICLE_DISTANCE)
    ui["run"] = gui_api.AddButton(win, "Run", on_run)
    ui["progress"] = gui_api.AddProgressBar(win, 0)
    ui["log"] = gui_api.AddTextArea(win, "", True)
    gui_api.ShowWindow(win)


if gui_api.IsGuiAvailable():
    build_ui()
else:
    print(TITLE + ": needs the CLO GUI (not available in headless mode)")
