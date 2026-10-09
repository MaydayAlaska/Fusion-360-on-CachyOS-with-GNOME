#!/usr/bin/env python3
"""Launch the installed Fusion launcher and run the XWayland popup helper.

The real Autodesk launcher is left untouched. The popup helper applies the
XFixes input fix before hiding the overlay, and is stopped after Fusion exits.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time

HOME = Path.home()
LAUNCHER = HOME / '.autodesk_fusion/bin/autodesk_fusion_launcher.sh'
HELPER = HOME / '.local/bin/fusion-popup-fix.py'
LOG = HOME / '.cache/fusion-popup-fix.log'


def fusion_running() -> bool:
    # Check only the current user's processes; match actual exe, not the wrapper.
    return subprocess.run(
        ['pgrep', '-u', str(os.getuid()), '-fi', 'fusion360[.]exe'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def main() -> int:
    if not LAUNCHER.is_file() or not os.access(LAUNCHER, os.X_OK):
        print(f'Original Fusion launcher not executable: {LAUNCHER}', file=sys.stderr)
        return 1
    if not HELPER.is_file():
        print(f'Popup helper not found: {HELPER}', file=sys.stderr)
        return 1

    LOG.parent.mkdir(parents=True, exist_ok=True)
    watcher_env = os.environ.copy()
    watcher_env.pop('WAYLAND_DISPLAY', None)  # Must query XWayland windows.
    with LOG.open('a', encoding='utf-8') as logfile:
        logfile.write('\n--- Starting Fusion popup helper ---\n')
        logfile.flush()
        helper = subprocess.Popen(
            [sys.executable, str(HELPER)],
            env=watcher_env,
            stdin=subprocess.DEVNULL,
            stdout=logfile,
            stderr=subprocess.STDOUT,
        )
        try:
            # Original launcher and any parameters are forwarded unchanged.
            # Launch Fusion under XWayland and use the original script's directory.
            fusion = subprocess.Popen(
                [str(LAUNCHER), *sys.argv[1:]],
                env=watcher_env,
                cwd=str(LAUNCHER.parent),
            )

            # Some launchers return before Wine finishes starting Fusion.
            # Keep the helper active while waiting for the real executable.
            appeared = False
            for _ in range(120):
                if fusion_running():
                    appeared = True
                    break
                if helper.poll() is not None:
                    logfile.write('Warning: popup helper exited (see log above).\n')
                    logfile.flush()
                    # Still launch Fusion, but report helper problem in the log.
                time.sleep(1)

            if appeared:
                # Several consecutive misses avoid stopping on a brief respawn.
                misses = 0
                while misses < 5:
                    if fusion_running():
                        misses = 0
                    else:
                        misses += 1
                    time.sleep(2)
            elif fusion.poll() is None:
                # No observable Fusion360.exe, yet the original script is
                # still working: wait rather than killing it abruptly.
                fusion.wait()

            if fusion.poll() is None:
                try:
                    fusion.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            return fusion.returncode if fusion.returncode is not None else 0
        finally:
            if helper.poll() is None:
                helper.terminate()
                try:
                    helper.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    helper.kill()
                    helper.wait()


if __name__ == '__main__':
    raise SystemExit(main())
