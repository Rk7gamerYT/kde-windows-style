#!/usr/bin/env python3
"""Keep background app icons in the tray overflow (the ^ arrow), as Windows 11 does.

Plasma shows every active app icon by default. This hides each app icon the first time it
appears; after that the user's choice in the tray settings wins. The tray only reads that list
when Plasma starts, so a new app icon moves to the arrow after a quick Plasma reload, once per app.
Standard library only.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

CONFIG = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')
STATE = Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'kde-windows-style'
SEEN = STATE/'tray-seen.json'
AUTOSTART = CONFIG/'autostart/kde-windows-style-tray.desktop'
# Hardware and system icons (network, battery...) stay visible, as on Windows.
APP_CATEGORIES = {'ApplicationStatus', 'Communications'}


def call(*args):
    result = subprocess.run(args, text=True, capture_output=True, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def item_property(item, name):
    service, _, path = item.partition('/')
    reply = call('gdbus', 'call', '--session', '-d', service, '-o', '/'+path, '-m',
                 'org.freedesktop.DBus.Properties.Get', 'org.kde.StatusNotifierItem', name)
    # gdbus prints (<'value'>,)
    return reply[3:-4] if reply.startswith("(<'") else ''


def app_icons():
    reply = call('gdbus', 'call', '--session', '-d', 'org.kde.StatusNotifierWatcher', '-o', '/StatusNotifierWatcher',
                 '-m', 'org.freedesktop.DBus.Properties.Get', 'org.kde.StatusNotifierWatcher',
                 'RegisteredStatusNotifierItems')
    ids = []
    for item in [part.strip(" '") for part in reply.split('[', 1)[-1].split(']', 1)[0].split(',') if part.strip(" '")]:
        try:
            if item_property(item, 'Category') in APP_CATEGORIES:
                ids.append(item_property(item, 'Id'))
        except (RuntimeError, subprocess.SubprocessError):
            continue  # The app quit while being asked.
    return [i for i in ids if i]


def hide(ids):
    """Add ids to hiddenItems of every system tray, unless the user pinned them as shown."""
    script = '''
    var ids = %s;
    panels().forEach(function(panel) {
        panel.widgets("org.kde.plasma.systemtray").forEach(function(tray) {
            tray.currentConfigGroup = ["General"];
            var hidden = String(tray.readConfig("hiddenItems", "")).split(",").filter(x => x);
            var shown = String(tray.readConfig("shownItems", "")).split(",").filter(x => x);
            ids.forEach(function(id) { if (hidden.indexOf(id) < 0 && shown.indexOf(id) < 0) hidden.push(id); });
            tray.writeConfig("hiddenItems", hidden.join(","));
        });
    });
    ''' % json.dumps(ids)
    call('qdbus6', 'org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', script)


def sync():
    try:
        seen = set(json.loads(SEEN.read_text()))
    except (OSError, ValueError):
        seen = set()
    new = [i for i in app_icons() if i not in seen]
    if not new:
        return False
    hide(new)
    STATE.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(sorted(seen | set(new))))
    print('Na seta da bandeja:', ', '.join(new))
    return True


def sync_quietly():
    try:
        return sync()
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print('Bandeja indisponível agora:', exc, file=sys.stderr)
        return False


def reload_plasma():
    subprocess.run(['systemctl', '--user', 'reset-failed', 'plasma-plasmashell.service'], capture_output=True)
    subprocess.run(['systemctl', '--user', 'restart', 'plasma-plasmashell.service'], capture_output=True, timeout=60)


def watch():
    if sync_quietly():
        reload_plasma()
    monitor = subprocess.Popen(['gdbus', 'monitor', '--session', '-d', 'org.kde.StatusNotifierWatcher'],
                               stdout=subprocess.PIPE, text=True)
    for line in monitor.stdout:
        # Turning the option off removes the autostart entry; stop with it.
        if not AUTOSTART.exists():
            monitor.terminate()
            return
        if 'StatusNotifierItemRegistered' in line or 'StatusNotifierHostRegistered' in line:
            time.sleep(3)  # Let apps starting together register, and a restarting Plasma settle.
            if sync_quietly():
                reload_plasma()


if __name__ == '__main__':
    watch() if '--watch' in sys.argv else sync()
