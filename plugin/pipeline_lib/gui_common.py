"""Window helpers shared by the windowed scripts. Needs gui_api, so the no-GUI script must not import this."""
import json
import os
import time

import gui_api

from . import steps

TITLE = "Easy Export"
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".clo_export_pipeline.json")
UV_WARNING = "IMPORTANT: Arrange UVs in the UV Editor (0-1 tile) before running."


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


def saved_particle_distance(settings):
    saved = settings.get("particle_distance", steps.PARTICLE_DISTANCE)
    if not isinstance(saved, (int, float)) or saved <= 0:
        return steps.PARTICLE_DISTANCE
    return saved


class RunLog:
    """Timestamps each line, shows it in a text area widget and prints it to the console."""

    def __init__(self, widget):
        self.widget = widget
        self.lines = []

    def __call__(self, msg):
        line = "%s  %s" % (time.strftime("%H:%M:%S"), msg)
        print(line)
        self.lines.append(line)
        gui_api.SetWidgetValue(self.widget, "\n".join(self.lines))

    def save(self, path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.lines) + "\n")
        except OSError:
            pass


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
