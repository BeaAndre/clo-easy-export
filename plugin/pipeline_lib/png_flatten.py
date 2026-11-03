"""Flatten an RGBA PNG onto an opaque background colour (result: RGB, fully opaque).

Uses libpng's simplified API through ctypes (CLO ships libpng16.dll next to its executable), so the
compositing runs in C — fast enough for 4k bakes. Falls back to a pure-Python implementation
(correct but slow: tens of seconds at 4k) if libpng can't be loaded.
"""
import ctypes
import os
import struct
import sys
import zlib

PNG_IMAGE_VERSION = 1
PNG_FORMAT_FLAG_ALPHA = 0x01
PNG_FORMAT_FLAG_COLOR = 0x02
PNG_FORMAT_RGB = PNG_FORMAT_FLAG_COLOR
PNG_FORMAT_RGBA = PNG_FORMAT_FLAG_COLOR | PNG_FORMAT_FLAG_ALPHA


class _PngImage(ctypes.Structure):
    _fields_ = [
        ("opaque", ctypes.c_void_p),
        ("version", ctypes.c_uint32),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("format", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("colormap_entries", ctypes.c_uint32),
        ("warning_or_error", ctypes.c_uint32),
        ("message", ctypes.c_char * 64),
    ]


class _PngColor(ctypes.Structure):
    _fields_ = [("red", ctypes.c_uint8), ("green", ctypes.c_uint8), ("blue", ctypes.c_uint8)]


def _candidate_dirs():
    yield os.path.dirname(sys.executable)  # inside CLO: the CLO install folder
    yield os.environ.get("CLO_INSTALL_DIR", "")
    yield r"D:\Clo3D\CLO Standalone OnlineAuth"  # dev machine (system Python)


_lib = None


def _load_libpng():
    global _lib
    if _lib is not None:
        return _lib
    errors = []
    for d in _candidate_dirs():
        path = os.path.join(d, "libpng16.dll") if d else ""
        if not path or not os.path.isfile(path):
            continue
        try:
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(d)  # for libpng's zlib dependency
            lib = ctypes.CDLL(path)
            lib.png_image_begin_read_from_file.argtypes = [ctypes.POINTER(_PngImage), ctypes.c_char_p]
            lib.png_image_finish_read.argtypes = [ctypes.POINTER(_PngImage), ctypes.POINTER(_PngColor),
                                                  ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p]
            lib.png_image_write_to_file.argtypes = [ctypes.POINTER(_PngImage), ctypes.c_char_p, ctypes.c_int,
                                                    ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p]
            lib.png_image_free.argtypes = [ctypes.POINTER(_PngImage)]
            _lib = lib
            return lib
        except (OSError, AttributeError) as e:
            errors.append("%s: %s" % (path, e))
    raise OSError("libpng16.dll not usable: %s" % ("; ".join(errors) or "not found"))


def _flatten_libpng(src, dst, rgb):
    lib = _load_libpng()
    img = _PngImage()
    img.version = PNG_IMAGE_VERSION
    if not lib.png_image_begin_read_from_file(ctypes.byref(img), os.fsencode(src)):
        raise OSError("libpng read %s: %s" % (src, img.message.decode(errors="replace")))
    try:
        img.format = PNG_FORMAT_RGB  # dropping alpha + background colour => composite onto it
        stride = img.width * 3
        buf = ctypes.create_string_buffer(stride * img.height)
        bg = _PngColor(*rgb)
        if not lib.png_image_finish_read(ctypes.byref(img), ctypes.byref(bg), buf, stride, None):
            raise OSError("libpng decode %s: %s" % (src, img.message.decode(errors="replace")))
    finally:
        lib.png_image_free(ctypes.byref(img))
    out = _PngImage()
    out.version = PNG_IMAGE_VERSION
    out.width, out.height, out.format = img.width, img.height, PNG_FORMAT_RGB
    if not lib.png_image_write_to_file(ctypes.byref(out), os.fsencode(dst), 0, buf, stride, None):
        raise OSError("libpng write %s: %s" % (dst, out.message.decode(errors="replace")))


# ----------------------------------------------------------------------------------- fallback
def _read_png_rgba(path):
    d = open(path, "rb").read()
    p, idat = 8, b""
    while p < len(d):
        n = struct.unpack(">I", d[p:p + 4])[0]
        t = d[p + 4:p + 8]
        if t == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", d[p + 8:p + 18])
            if bd != 8 or ct not in (2, 6):
                raise ValueError("unsupported PNG (bitdepth %d, colortype %d)" % (bd, ct))
            bpp = 4 if ct == 6 else 3
        elif t == b"IDAT":
            idat += d[p + 8:p + 8 + n]
        p += 12 + n
    raw = zlib.decompress(idat)
    stride = w * bpp
    rows, prev, i = [], bytearray(stride), 0
    for _y in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        if f == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 255
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif f == 3:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif f == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        rows.append(line)
        prev = line
    return w, h, bpp, rows


def _flatten_python(src, dst, rgb):
    w, h, bpp, rows = _read_png_rgba(src)
    out = []
    for line in rows:
        o = bytearray(b"\x00")  # filter type 0
        if bpp == 3:
            o += line
        else:
            r = line[0::4]
            g = line[1::4]
            b = line[2::4]
            a = line[3::4]
            rr = bytearray((r[k] * a[k] + rgb[0] * (255 - a[k]) + 127) // 255 for k in range(w))
            gg = bytearray((g[k] * a[k] + rgb[1] * (255 - a[k]) + 127) // 255 for k in range(w))
            bb = bytearray((b[k] * a[k] + rgb[2] * (255 - a[k]) + 127) // 255 for k in range(w))
            px = bytearray(w * 3)
            px[0::3], px[1::3], px[2::3] = rr, gg, bb
            o += px
        out.append(bytes(o))

    def chunk(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)

    with open(dst, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(b"".join(out), 6)))
        f.write(chunk(b"IEND", b""))


def flatten_png(src, dst, rgb=(0, 0, 0)):
    """Composite src (RGBA) over a solid `rgb` background and write an opaque RGB PNG to dst.

    Returns the method used: "libpng" or "python".
    """
    try:
        _flatten_libpng(src, dst, rgb)
        return "libpng"
    except Exception:  # noqa: BLE001 - fall back to the slow path
        _flatten_python(src, dst, rgb)
        return "python"
