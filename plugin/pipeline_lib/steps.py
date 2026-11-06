"""Core pipeline steps. Each step raises PipelineError on failure."""
import json
import os
import re
import time

import ApiTypes
import export_api
import fabric_api
import pattern_api
import utility_api

from . import png_flatten

MESH_TYPE = "Quad"
PARTICLE_DISTANCE = 15.0
RECOMMENDED_MIN_DISTANCE = 10.0
TOPSTITCH_MODEL_TEXTURE = 1  # 0 = OBJ, 1 = Texture
TEXTURE_SIZE = 4096          # release value; dev_settings.json may override for testing
MATERIAL_FACES = (0, 1, 2)   # Front, Back, Side
STITCH_LINES = range(4)      # GetTopStitchColor works for lines 0-3 regardless of the real line count
UDIM_SUFFIX = "_1001"
TEXTURES_FOLDER = "textures"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEV_SETTINGS_PATH = os.path.join(_REPO_ROOT, "dev_settings.json")


class PipelineError(Exception):
    pass


class RunLog:
    """Timestamps each line and prints it to the console. on_change(lines) runs after every new line."""

    def __init__(self, on_change=None):
        self.on_change = on_change
        self.lines = []

    def __call__(self, msg):
        line = "%s  %s" % (time.strftime("%H:%M:%S"), msg)
        print(line)
        self.lines.append(line)
        if self.on_change:
            self.on_change(self.lines)

    def save(self, path, start=0):
        """Write the log to path, from line number start onwards."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.lines[start:]) + "\n")
        except OSError:
            pass


def texture_size():
    """4096 unless <repo>/dev_settings.json says {"texture_size": N} (dev/testing only)."""
    try:
        with open(DEV_SETTINGS_PATH, encoding="utf-8") as f:
            return int(json.load(f).get("texture_size", TEXTURE_SIZE))
    except (OSError, ValueError):
        return TEXTURE_SIZE


def sanitize_name(raw):
    raw = (raw or "").strip()
    if raw.lower().endswith((".fbx", ".zprj")):
        raw = os.path.splitext(raw)[0]
    return re.sub(r"[^\w\-]+", "_", raw).strip("_")


def base_name(override=""):
    """User-given file name if set, else the project name, else 'garment'."""
    return sanitize_name(override) or sanitize_name(utility_api.GetProjectName()) or "garment"


def output_files(out_dir, name):
    """Every file an export writes, apart from the log."""
    tex_dir = os.path.join(out_dir, TEXTURES_FOLDER)
    return [os.path.join(out_dir, name + ".fbx")] + [
        os.path.join(tex_dir, "%s_%s.png" % (name, m)) for m in ("diffuse", "normal", "roughness", "topstitch")]


def current_colorway():
    return utility_api.GetCurrentColorwayIndex()


# ---------------------------------------------------------------------------------- steps 1-3
def set_quad_mesh():
    n = pattern_api.GetPatternCount()
    for i in range(n):
        pattern_api.SetMeshType(i, MESH_TYPE)
    return "%d patterns set to %s" % (n, MESH_TYPE)


def set_particle_distance(distance=PARTICLE_DISTANCE):
    distance = float(distance)
    pattern_api.SetParticleDistanceOfPatterns(distance)
    n = pattern_api.GetPatternCount()
    wrong = [i for i in range(n) if abs(pattern_api.GetParticleDistanceOfPattern(i) - distance) > 1e-3]
    if wrong:
        raise PipelineError("particle distance not applied to patterns %s" % wrong)
    return "%d patterns at particle distance %g" % (n, distance)


def set_topstitches_texture():
    n = utility_api.GetTopStitchCount(False)
    failed = []
    for s in range(n):
        pattern_api.SetTopstitchStyleModelType(s, TOPSTITCH_MODEL_TEXTURE)
        if pattern_api.GetTopstitchStyleModelType(s) != TOPSTITCH_MODEL_TEXTURE:
            failed.append(utility_api.GetTopStitchName(s))
    if failed:
        raise PipelineError("could not set topstitch styles to Texture: %s" % failed)
    return "%d topstitch styles set to Texture" % n


# -------------------------------------------------------------------------------------- step 4
def export_fbx(out_dir, name):
    opt = ApiTypes.ImportExportOption()
    opt.bExportGarment = True
    opt.bExportAvatar = False
    opt.bSingleObject = True
    opt.bThin = False
    opt.bClothUnifiedUVCoordinates = True
    opt.bAvatarUnifiedUVCoordinates = False
    opt.bSaveColorWays = False
    opt.bSaveInZip = False
    opt.bIncludeHiddenObject = False
    for flag in ("bUnifiedDiffuseMap", "bUnifiedNormalMap", "bUnifiedRoughnessMap",
                 "bUnifiedMetalnessMap", "bUnifiedOpacityMap", "bUnifiedDisplacementMap"):
        setattr(opt, flag, False)  # textures come from BakeUVTexture
    path = os.path.join(out_dir, name + ".fbx")
    export_api.ExportFBX(path, opt)
    if not os.path.isfile(path):
        raise PipelineError("FBX was not written: %s" % path)
    return path


# ---------------------------------------------------------------------------------- steps 5, 6
def _bake(tex_dir, stem, diffuse, normal, roughness):
    """BakeUVTexture into tex_dir; returns {map: path} with the _1001 UDIM suffix stripped."""
    opt = ApiTypes.ImportExportOption()
    opt.bClothUnifiedUVCoordinates = True
    opt.unifiedTextureSize = float(texture_size())
    opt.bUnifiedDiffuseMap = diffuse
    opt.bUnifiedNormalMap = normal
    opt.bUnifiedRoughnessMap = roughness
    opt.bUnifiedMetalnessMap = False
    opt.bUnifiedOpacityMap = False
    opt.bUnifiedDisplacementMap = False
    produced = utility_api.BakeUVTexture(os.path.join(tex_dir, stem + ".png"), opt, False) or []
    result = {}
    for p in produced:
        if not os.path.isfile(p):
            continue
        root, ext = os.path.splitext(p)
        if root.endswith(UDIM_SUFFIX):
            root = root[: -len(UDIM_SUFFIX)]
        os.replace(p, root + ext)
        result[os.path.basename(root)[len(stem) + 1:]] = root + ext  # "diffuse", "normal", ...
    wanted = [m for m, on in (("diffuse", diffuse), ("normal", normal), ("roughness", roughness)) if on]
    missing = [m for m in wanted if m not in result]
    if missing:
        raise PipelineError("bake did not produce %s (got %s)" % (missing, produced))
    return result


def bake_pbr(tex_dir, name):
    maps = _bake(tex_dir, name, True, True, True)
    return [maps["diffuse"], maps["normal"], maps["roughness"]]


def _fabric_indices(cw):
    """Every fabric index in use. GetFabricCount(True) can be smaller than the highest index patterns
    reference, so take the union with what the patterns actually use."""
    idx = set(range(fabric_api.GetFabricCount(False)))
    for p in range(pattern_api.GetPatternCount()):
        f = fabric_api.GetFabricIndexForPattern(p, cw)
        if f >= 0:
            idx.add(f)
    return sorted(idx)


def _snapshot_colours(cw):
    fabrics = []
    for f in _fabric_indices(cw):
        for face in MATERIAL_FACES:
            try:
                linked = bool(face) and fabric_api.GetUseSameMaterialAsFront(cw, f, face)
                colour = tuple(fabric_api.GetFabricPBRMaterialBaseColor(cw, f, face))
            except Exception:  # noqa: BLE001 - index not valid for this colorway
                continue
            fabrics.append((f, face, linked, colour))
    stitches = []
    for s in range(utility_api.GetTopStitchCount(False)):
        for line in STITCH_LINES:
            c = utility_api.GetTopStitchColor(s, cw, line)
            stitches.append((s, line, (c.R, c.G, c.B, c.A)))
    return fabrics, stitches


def _restore_colours(cw, fabrics, stitches):
    """Restore in reverse order (linked Back/Side faces follow Front), then verify. Returns problems."""
    for f, face, linked, c in reversed(fabrics):
        if not linked:
            fabric_api.SetFabricPBRMaterialBaseColor(cw, f, face, *c)
    for s, line, c in stitches:
        utility_api.SetTopStitchColor(s, cw, line, *c)
    problems = []
    for f, face, _linked, c in fabrics:
        now = tuple(fabric_api.GetFabricPBRMaterialBaseColor(cw, f, face))
        if any(abs(a - b) > 1e-4 for a, b in zip(now, c)):
            problems.append("fabric %d face %d: was %r, now %r" % (f, face, c, now))
    for s, line, c in stitches:
        n = utility_api.GetTopStitchColor(s, cw, line)
        if (n.R, n.G, n.B, n.A) != c:
            problems.append("topstitch %d line %d: was %r, now %r" % (s, line, c, (n.R, n.G, n.B, n.A)))
    return problems


def backup_colours(name):
    """Safety net before step 6: write the original fabric/topstitch colours to JSON in CLO's temp folder.
    (Not ExportZPrj: that acts like Save As and switches the open project to the backup file.)
    Returns (path, warning or None)."""
    cw = current_colorway()
    fabrics, stitches = _snapshot_colours(cw)
    path = os.path.join(utility_api.GetCLOTemporaryFolderPath(), "export_pipeline_colours_%s.json" % name)
    data = {
        "colorway": cw,
        "fabrics": [{"fabric": f, "face": face, "linked": linked, "rgba": list(c)} for f, face, linked, c in fabrics],
        "topstitches": [{"style": s, "line": line, "rgba": list(c)} for s, line, c in stitches],
    }
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1)
    except OSError as e:
        return path, "colour backup was not written (%s)" % e
    return path, None


def bake_topstitch_mask(tex_dir, name):
    """Black cloth + white topstitches -> diffuse bake -> flattened opaque <name>_topstitch.png.
    Colours are restored in all cases; raises if the restore check finds a difference."""
    cw = current_colorway()
    fabrics, stitches = _snapshot_colours(cw)
    stem = name + "_topstitch"
    raw = None
    try:
        for f, face, linked, _c in fabrics:
            if not linked:
                fabric_api.SetFabricPBRMaterialBaseColor(cw, f, face, 0.0, 0.0, 0.0, 1.0)
        for s in range(utility_api.GetTopStitchCount(False)):
            utility_api.SetTopStitchColor(s, cw, -1, 255, 255, 255, 255)
        raw = _bake(tex_dir, stem + "_raw", True, False, False)["diffuse"]
    finally:
        problems = _restore_colours(cw, fabrics, stitches)
    if problems:
        raise PipelineError("COLOURS NOT RESTORED EXACTLY:\n  " + "\n  ".join(problems))
    final = os.path.join(tex_dir, stem + ".png")
    method = png_flatten.flatten_png(raw, final, (0, 0, 0))
    os.remove(raw)
    return final, method, len(fabrics), len(stitches)


# ---------------------------------------------------------------------------------- whole export
def run_pipeline(out_dir, name, distance, log, progress=lambda pct: None):
    """Run steps 1-6 on the open project. log(msg) gets one line per step, progress(pct) gets 0-100.
    Failures raise: the calling script decides how to report them."""
    tex_dir = os.path.join(out_dir, TEXTURES_FOLDER)
    os.makedirs(tex_dir, exist_ok=True)
    t0 = time.time()
    log("Export '%s' -> %s (texture size %d, particle distance %g)" % (name, out_dir, texture_size(), distance))
    log("1/6 " + set_quad_mesh())
    progress(8)
    log("2/6 " + set_particle_distance(distance))
    progress(15)
    log("3/6 " + set_topstitches_texture())
    progress(22)
    log("4/6 FBX: " + export_fbx(out_dir, name))
    progress(40)
    for p in bake_pbr(tex_dir, name):
        log("5/6 baked " + os.path.basename(p))
    progress(70)
    backup, warning = backup_colours(name)
    log("    original colours saved to: " + backup)
    if warning:
        log("    WARNING: " + warning)
    final, method, n_faces, n_lines = bake_topstitch_mask(tex_dir, name)
    log("6/6 baked %s (flattened via %s); %d fabric faces + %d stitch lines restored and verified"
        % (os.path.basename(final), method, n_faces, n_lines))
    progress(100)
    log("Done in %.1fs" % (time.time() - t0))
