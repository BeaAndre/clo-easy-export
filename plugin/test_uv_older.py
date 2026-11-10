# Local probe, not committed. Run from CLO's script editor on the older build with any project open.
# Logs which Auto-UV APIs exist. Read-only: nothing is reset, packed or saved.

import time
import traceback

LOG = r"C:\Users\Public\clo_uv_probe.txt"
out = []


def log(msg):
    out.append(msg)
    print(msg)


def has(module_name, attr):
    try:
        mod = __import__(module_name)
    except Exception as e:  # noqa: BLE001
        log("%-45s  MODULE MISSING (%s)" % (module_name, e))
        return False
    ok = hasattr(mod, attr)
    log("%-45s  %s" % (module_name + "." + attr, "yes" if ok else "NO"))
    return ok


try:
    log("=== UV probe %s ===" % time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        import utility_api
        log("API version: %s" % utility_api.GetAPIVersion())
    except Exception as e:  # noqa: BLE001
        log("API version: unknown (%s)" % e)

    uv_space = has("pattern_api", "GetPatternUVSpace")
    has("utility_api", "ResetUVTo2DArrangement")
    has("utility_api", "UVPacking")
    has("export_api", "ExportZPrj")
    has("utility_api", "MoveNonFabricObjectsToUVSpace")

    if uv_space:
        import pattern_api
        n = pattern_api.GetPatternCount()
        log("pattern count: %d" % n)
        if n:
            log("GetPatternUVSpace(0) -> %s" % pattern_api.GetPatternUVSpace(0))
except Exception:  # noqa: BLE001
    log("FAILED:\n" + traceback.format_exc())
finally:
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
    except OSError:
        pass
