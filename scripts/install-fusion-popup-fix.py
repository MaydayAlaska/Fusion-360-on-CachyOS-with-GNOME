#!/usr/bin/env python3
"""Install the Fusion popup workaround and integrate it with GNOME's dock.

Runs as the logged-in user. Changes only user-owned files and GNOME favorites.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HOME = Path.home()
HERE = Path(__file__).resolve().parent
APP_DIR = HOME / '.local/share/applications'
BIN_DIR = HOME / '.local/bin'
ENTRY = APP_DIR / 'autodesk-fusion.desktop'
WRAPPER = BIN_DIR / 'fusion-launch-with-fix.py'
ORIGINAL = HOME / '.autodesk_fusion/bin/autodesk_fusion_launcher.sh'
BACKUP_SUFFIX = '.fusion-popup-fix.bak'


def update_key(contents: str, key: str, value: str) -> str:
    """Modify only the [Desktop Entry] section; preserve other sections."""
    match = re.search(r'^\[Desktop Entry\]\s*$', contents, re.M)
    if not match:
        raise ValueError('File does not contain a [Desktop Entry] section')
    section_start = match.end()
    next_section = re.search(r'^\[.+\]\s*$', contents[section_start:], re.M)
    section_end = section_start + next_section.start() if next_section else len(contents)
    head, section, tail = contents[:section_start], contents[section_start:section_end], contents[section_end:]
    pattern = rf'^{re.escape(key)}=.*$'
    if re.search(pattern, section, flags=re.M):
        section = re.sub(pattern, lambda _m: f'{key}={value}', section, count=1, flags=re.M)
    else:
        if not section.endswith('\n'):
            section += '\n'
        section += f'{key}={value}\n'
    return head + section + tail


def is_fusion_shortcut(contents: str) -> bool:
    return bool(re.search(r'^Name=Autodesk Fusion\s*$', contents, re.M))


def save_backup(file: Path) -> None:
    backup = file.with_name(file.name + BACKUP_SUFFIX)
    if file.exists() and not backup.exists():
        shutil.copy2(file, backup)


def install_scripts() -> None:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    for file in ('fusion-popup-fix.py', 'fusion-launch-with-fix.py'):
        src = HERE / file
        if not src.is_file():
            sys.exit(f'Missing {src}: run this installer from a complete repository checkout')
        dest = BIN_DIR / file
        shutil.copy2(src, dest)
        dest.chmod(dest.stat().st_mode | 0o755)
        print(f'Installed {dest}')


def fix_old_desktop_entries() -> int:
    updated = 0
    for desktop in APP_DIR.rglob('*.desktop'):
        if desktop == ENTRY:
            continue
        try:
            contents = desktop.read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            continue
        if not is_fusion_shortcut(contents):
            continue
        save_backup(desktop)
        revised = update_key(contents, 'Exec', str(WRAPPER))
        revised = update_key(revised, 'NoDisplay', 'true')
        if revised != contents:
            desktop.chmod(desktop.stat().st_mode | 0o200)
            desktop.write_text(revised, encoding='utf-8')
            updated += 1
            print(f'Updated and hidden duplicate shortcut: {desktop}')
    return updated


def create_managed_desktop_entry() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    save_backup(ENTRY)
    icon = HOME / '.autodesk_fusion/resources/graphics/autodesk_fusion.svg'
    text = '\n'.join((
        '[Desktop Entry]',
        'Version=1.0',
        'Type=Application',
        'Name=Autodesk Fusion',
        'Comment=Fusion 360 with automatic XWayland popup fix',
        f'Exec={WRAPPER}',
        f'TryExec={WRAPPER}',
        f'Icon={icon}',
        f'Path={ORIGINAL.parent}',
        'Terminal=false',
        'Categories=Graphics;Engineering;',
        'StartupWMClass=fusion360.exe',
        '',
    ))
    ENTRY.write_text(text, encoding='utf-8')
    ENTRY.chmod(0o644)
    print(f'Created desktop entry: {ENTRY}')


def sync_gnome_favorites() -> None:
    if not shutil.which('gsettings'):
        print('GNOME favorites not updated (gsettings unavailable)')
        return
    result = subprocess.run(['gsettings', 'get', 'org.gnome.shell', 'favorite-apps'],
                            text=True, capture_output=True, check=False)
    if result.returncode:
        print('GNOME favorites not updated:', result.stderr.strip())
        return
    raw = result.stdout.strip()
    try:
        favorites = [] if raw == '@as []' else ast.literal_eval(raw)
        if not isinstance(favorites, list) or not all(isinstance(x, str) for x in favorites):
            raise ValueError('not a list of strings')
    except (SyntaxError, ValueError):
        print('Cannot interpret GNOME favorite-apps; use the new menu entry manually:', raw)
        return

    managed_id = ENTRY.name
    new_favorites = []
    did_pin = False
    for item in favorites:
        if ('autodesk' in item.lower() and 'fusion' in item.lower()) or item == managed_id:
            if not did_pin:
                new_favorites.append(managed_id)
                did_pin = True
        else:
            new_favorites.append(item)
    if not did_pin:
        new_favorites.append(managed_id)
    if new_favorites != favorites:
        changed = subprocess.run(['gsettings', 'set', 'org.gnome.shell', 'favorite-apps',
                                  repr(new_favorites)], text=True, capture_output=True, check=False)
        if changed.returncode:
            print('GNOME dock update failed:', changed.stderr.strip())
        else:
            print('GNOME dock pinned to:', managed_id)
    else:
        print('GNOME dock already points to:', managed_id)


def main() -> int:
    if not ORIGINAL.is_file():
        print(f'Fusion launcher missing: {ORIGINAL}', file=sys.stderr)
        return 1
    if not os.access(ORIGINAL, os.X_OK):
        print(f'Fusion launcher is not executable: {ORIGINAL}', file=sys.stderr)
        return 1
    install_scripts()
    fix_old_desktop_entries()
    create_managed_desktop_entry()
    sync_gnome_favorites()
    print('Done. Close Fusion and start it from the GNOME dock or app menu.')
    print(f'Check log: {HOME / ".cache/fusion-popup-fix.log"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
