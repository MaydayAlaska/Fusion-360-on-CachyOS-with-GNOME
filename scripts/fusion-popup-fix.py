#!/usr/bin/env python3
"""Work around Fusion 360's translucent modal overlay on Wine + XWayland.

For each matching overlay, apply an empty X11 input shape FIRST, then set its
_NET_WM_WINDOW_OPACITY to 0. Run while Fusion is open; Ctrl+C to stop.
No Wine settings or Autodesk files are modified.
"""

import ctypes as C
import ctypes.util
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ORIGINAL_OPACITY = "1280068684"
POLL_SECONDS = 0.4


def command(*argv):
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def overlay_properties(window):
    result = command(
        "xprop", "-id", window,
        "WM_NAME", "WM_CLASS", "_NET_WM_WINDOW_TYPE",
        "_NET_WM_WINDOW_OPACITY", "WM_TRANSIENT_FOR",
    )
    if result.returncode != 0:
        return False
    props = result.stdout
    opacity_line = next(
        (line for line in props.splitlines() if line.startswith("_NET_WM_WINDOW_OPACITY(")),
        "",
    )
    return (
        '"Fusion360"' in props
        and '"fusion360.exe"' in props
        and "_NET_WM_WINDOW_TYPE_DIALOG" in props
        and "WM_TRANSIENT_FOR(WINDOW)" in props
        and opacity_line.rsplit("=", 1)[-1].strip() == ORIGINAL_OPACITY
    )


def fix_input_shape(display, x11, xfixes, window):
    # ShapeInput = 2. An empty region means pointer events pass through.
    region = xfixes.XFixesCreateRegion(display, None, 0)
    if not region:
        raise RuntimeError("XFixesCreateRegion failed")
    try:
        xfixes.XFixesSetWindowShapeRegion(display, int(window), 2, 0, 0, region)
        x11.XSync(display, 0)  # Ordering matters: input fix comes FIRST.
    finally:
        xfixes.XFixesDestroyRegion(display, region)


def main():
    for executable in ("xprop", "xdotool"):
        if not shutil.which(executable):
            sys.exit(f"Install {executable} before running this helper")

    # Don't accidentally run two simultaneous watchers.
    lock_path = Path.home() / ".cache" / "fusion-popup-fix.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit("Fusion popup helper is already running")

        x11_path = ctypes.util.find_library("X11")
        xfixes_path = ctypes.util.find_library("Xfixes")
        if not x11_path or not xfixes_path:
            sys.exit("X11 or Xfixes library not found")
        x11 = C.CDLL(x11_path)
        xfixes = C.CDLL(xfixes_path)

        x11.XOpenDisplay.argtypes = [C.c_char_p]
        x11.XOpenDisplay.restype = C.c_void_p
        x11.XSync.argtypes = [C.c_void_p, C.c_int]
        x11.XCloseDisplay.argtypes = [C.c_void_p]
        xfixes.XFixesCreateRegion.argtypes = [C.c_void_p, C.c_void_p, C.c_int]
        xfixes.XFixesCreateRegion.restype = C.c_ulong
        xfixes.XFixesSetWindowShapeRegion.argtypes = [
            C.c_void_p, C.c_ulong, C.c_int, C.c_int, C.c_int, C.c_ulong
        ]
        xfixes.XFixesDestroyRegion.argtypes = [C.c_void_p, C.c_ulong]

        display = x11.XOpenDisplay(None)
        if not display:
            sys.exit("Cannot connect to XWayland (check DISPLAY)")
        print("Watching Fusion 360 popups. Stop with Ctrl+C.", flush=True)
        try:
            while True:
                found = command("xdotool", "search", "--class", "fusion360.exe")
                if found.returncode == 0:
                    for window in found.stdout.splitlines():
                        if not window.isdecimal() or not overlay_properties(window):
                            continue
                        try:
                            # 1) Let clicks pass THROUGH the dark overlay.
                            fix_input_shape(display, x11, xfixes, window)
                            # 2) ONLY AFTERWARDS hide the dark overlay.
                            changed = command(
                                "xprop", "-id", window,
                                "-f", "_NET_WM_WINDOW_OPACITY", "32c",
                                "-set", "_NET_WM_WINDOW_OPACITY", "0",
                            )
                            if changed.returncode != 0:
                                print(f"Opacity update failed for {window}: {changed.stderr.strip()}", flush=True)
                            else:
                                print(f"Fixed overlay {window}: clicks first, opacity second", flush=True)
                        except Exception as exc:
                            print(f"Could not fix {window}: {exc}", flush=True)
                time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            x11.XCloseDisplay(display)


if __name__ == "__main__":
    main()
