#!/usr/bin/env python3
"""A reversible Windows-inspired profile for KDE Plasma 6. Standard library only."""
import argparse
import ast
from datetime import datetime
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from community_assets import archive as community_archive, ASSETS

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')
STATE = Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'kde-windows-style'
THEME = 'kde-windows-style'
ICON_NAME = 'KDEWindowsFluent'
ICON_REF = 'c8a244f571ef8fb47812bdc9dbce76546cedce69'
ICON_SHA256 = '07b6b593ab557e07f0a7cdb232cda99214af13fb74ad6ce1e77d666057647767'
FILES = ['plasma-org.kde.plasma.desktop-appletsrc', 'plasmashellrc', 'plasmarc', 'kdeglobals', 'kwinrc', 'breezerc']
# Backups made before breezerc was managed only cover these files, so restoring them leaves breezerc alone.
LEGACY_FILES = FILES[:5]
MENU = ['kde-windows-style-apply.desktop', 'kde-windows-style-restore.desktop',
        'kde-windows-style-settings.desktop', 'kde-windows-style-screenshot.desktop']
OWNED = [DATA/'plasma/desktoptheme'/THEME]
OWNED += [DATA/'icons'/name for name in [ICON_NAME, ICON_NAME+'-light', ICON_NAME+'-dark',
                                        '.'+ICON_NAME+'-base', '.'+ICON_NAME+'-light-base', '.'+ICON_NAME+'-dark-base']]
OWNED += [DATA/'applications'/name for name in MENU]
OWNED += [DATA/'icons'/name for name in ['KDEWindowsWin11','KDEWindowsWin11-dark']]
OWNED += [DATA/'color-schemes'/name for name in ['KDEWindowsWin11Dark.colors','KDEWindowsWin11Light.colors']]
OWNED += [DATA/'plasma/plasmoids/menu.11.next',DATA/'kde-windows-style/start-menu-icon.svg']
DECORATION = 'KDEWindowsWin11'
OWNED += [DATA/'aurorae/themes'/(DECORATION+suffix) for suffix in ['-dark', '-light']]
# Taskbar widgets of this project, in assets/<name>: id is org.kdewindowsstyle.<name>.
WIDGETS = ['quicksettings', 'weather', 'search', 'taskview']
QUICK_SETTINGS = 'org.kdewindowsstyle.quicksettings'
OWNED += [DATA/'plasma/plasmoids'/('org.kdewindowsstyle.'+name) for name in WIDGETS]
TRAY_AUTOSTART = CONFIG/'autostart/kde-windows-style-tray.desktop'
OWNED += [TRAY_AUTOSTART]
META, ALT, CTRL, SHIFT = 0x10000000, 0x08000000, 0x04000000, 0x02000000
TAB, F4, ESC = 0x01000001, 0x01000033, 0x01000000
UP, DOWN, PGUP, PGDOWN, SCREENSAVER = 0x01000013, 0x01000015, 0x01000016, 0x01000017, 0x010000ba
SHORTCUTS = [
    ('kwin', 'Walk Through Windows', [ALT | TAB]),
    ('kwin', 'Overview', [META | TAB, META | ord('W')]),
    ('kwin', 'Show Desktop', [META | ord('D')]),
    ('kwin', 'Window Close', [ALT | F4]),
    # Win+Up/Down maximize and minimize as on Windows; the tile actions give up those keys.
    ('kwin', 'Window Quick Tile Top', []),
    ('kwin', 'Window Quick Tile Bottom', []),
    ('kwin', 'Window Maximize', [META | UP, META | PGUP]),
    ('kwin', 'Window Minimize', [META | DOWN, META | PGDOWN]),
    ('ksmserver', 'Lock Session', [META | ord('L'), SCREENSAVER]),
    ('org.kde.plasma-systemmonitor.desktop', '_launch', [CTRL | SHIFT | ESC, META | ESC]),
    ('org.kde.dolphin.desktop', '_launch', [META | ord('E')]),
    ('org.kde.krunner.desktop', '_launch', [META | ord('R'), ALT | ord(' '), ALT | 0x01000031]),
    ('systemsettings.desktop', '_launch', [META | ord('I')]),
    ('org.kde.spectacle.desktop', 'RecordRegion', [META | SHIFT | ord('R')]),
    ('org.kde.spectacle.desktop', '_launch', [0x01000009]),
    ('org.kde.spectacle.desktop', 'RectangularRegionScreenShot', [META | SHIFT | ord('S')]),
]


def run(*args, check=True):
    result = subprocess.run([str(x) for x in args], text=True, capture_output=True, timeout=180)
    if check and result.returncode:
        raise RuntimeError(f'{args[0]}: {result.stderr.strip() or result.stdout.strip()}')
    return result.stdout.strip()


def script(text):
    return run('qdbus6', 'org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', text)


def accel(method, *args):
    return run('gdbus', 'call', '--session', '--dest', 'org.kde.kglobalaccel',
               '--object-path', '/kglobalaccel', '--method', 'org.kde.KGlobalAccel.'+method, *args)


def action(component, name):
    return json.dumps([component, name, component, name])


def variant_argument(reply):
    """Unwrap gdbus's single output tuple, preserving nested GVariant type hints."""
    if not reply.startswith('(') or not reply.endswith(',)'):
        raise ValueError('Resposta D-Bus inesperada: '+reply)
    return reply[1:-2]


def snapshot_shortcuts():
    return [{'id': action(c, n), 'keys': variant_argument(accel('shortcutKeys', action(c, n)))}
            for c, n, _ in SHORTCUTS]


def set_shortcuts(saved=None):
    if saved is not None:
        for entry in saved:
            accel('setForeignShortcutKeys', entry['id'], entry['keys'])
        return
    targets = {(c, n) for c, n, _ in SHORTCUTS}
    # Remove our target actions first so Meta+Tab can move from cycling to overview.
    for c, n, _ in SHORTCUTS:
        accel('doRegister', action(c, n))
        accel('setForeignShortcutKeys', action(c, n), '[]')
    for c, n, keys in SHORTCUTS:
        available = []
        for key in keys:
            owners = ast.literal_eval(accel('action', str(key)).replace('@as ', ''))[0]
            if owners and tuple(owners[:2]) not in targets:
                print(f'Atalho {key} reservado por {owners[0]}: mantido, sem sobrescrever.')
                continue
            available.append(f'([{key}, 0, 0, 0],)')
        accel('setForeignShortcutKeys', action(c, n), '['+', '.join(available)+']')


def write_config(file, group, key, value):
    run('kwriteconfig6', '--file', str(CONFIG/file), '--group', group, '--key', key, str(value))


def stop_plasma():
    run('systemctl', '--user', 'stop', 'plasma-plasmashell.service')


def start_plasma():
    # Applying twice in a row restarts Plasma often enough to hit systemd's start limit.
    run('systemctl', '--user', 'reset-failed', 'plasma-plasmashell.service', check=False)
    run('systemctl', '--user', 'start', 'plasma-plasmashell.service')


def backup():
    location = STATE/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    location.mkdir(parents=True)
    shortcuts = snapshot_shortcuts()
    stop_plasma()
    try:
        for name in FILES:
            source = CONFIG/name
            if source.exists():
                shutil.copy2(source, location/name)
        entries = []
        for i, source in enumerate(OWNED):
            if source.is_symlink():
                raise RuntimeError(f'Destino é um link simbólico: {source}')
            entries.append({'path': str(source), 'exists': source.exists(), 'directory': source.is_dir()})
            if source.is_dir():
                shutil.copytree(source, location/'owned'/str(i), symlinks=True)
            elif source.is_file():
                (location/'owned').mkdir(exist_ok=True)
                shutil.copy2(source, location/'owned'/str(i))
        (location/'manifest.json').write_text(json.dumps({'owned': entries, 'files': FILES, 'shortcuts': shortcuts}, indent=2))
    finally:
        start_plasma()
    (STATE/'latest').write_text(str(location))
    print('Backup:', location)
    return location


def restore(location):
    location = Path(location).resolve()
    manifest = json.loads((location/'manifest.json').read_text())
    entries=manifest['owned']
    if [entry['path'] for entry in entries] != [str(path) for path in OWNED[:len(entries)]]:
        raise RuntimeError('Backup não corresponde aos caminhos deste usuário.')
    manifest['owned']=entries+[{'path':str(path),'exists':False,'directory':False} for path in OWNED[len(entries):]]
    stop_plasma()
    try:
        for name in manifest.get('files', LEGACY_FILES):
            source, target = location/name, CONFIG/name
            if source.exists():
                shutil.copy2(source, target)
            else:
                target.unlink(missing_ok=True)
        for i, entry in enumerate(manifest['owned']):
            target = Path(entry['path'])
            if target.is_symlink():
                raise RuntimeError(f'Destino é um link simbólico: {target}')
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)
            if entry['exists']:
                target.parent.mkdir(parents=True, exist_ok=True)
                source = location/'owned'/str(i)
                if entry['directory']:
                    shutil.copytree(source, target, symlinks=True)
                else:
                    shutil.copy2(source, target)
        set_shortcuts(manifest['shortcuts'])
        run('qdbus6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure')
    finally:
        start_plasma()
    # Restoring appearance must not uninstall the graphical configuration app.
    install_menu()
    print('Perfil anterior restaurado de:', location)


def panel_svg(source, opacity):
    raw = gzip.decompress(source.read_bytes()) if source.suffix == '.svgz' else source.read_bytes()
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    svg = ET.fromstring(raw)
    svg.set('opacity', str(opacity/100))
    return ET.tostring(svg, encoding='utf-8', xml_declaration=True)


def install_theme(opacity, dark, style="breeze"):
    base = Path('/usr/share/plasma/desktoptheme/default/widgets/panel-background.svgz')
    if not base.is_file():
        raise RuntimeError('Tema Breeze não encontrado. Instale plasma-workspace e breeze.')
    theme = DATA/'plasma/desktoptheme'/THEME
    if theme.exists():
        shutil.rmtree(theme)
    if style == 'win11':
        with tempfile.TemporaryDirectory() as temp:
            with tarfile.open(community_archive('win11-plasma')) as tar:
                tar.extractall(temp, filter='data')
            source=Path(temp)/('Win11OS-kde-'+ASSETS['win11-plasma'][1])/'plasma/desktoptheme'/('Win11OS-dark' if dark else 'Win11OS-light')
            shutil.copytree(source,theme,symlinks=True)
            base=theme/'widgets/panel-background.svg'
            if not base.is_file():
                base=theme/'widgets/panel-background.svgz'
    (theme/'widgets').mkdir(parents=True, exist_ok=True)
    panel_data=panel_svg(base, opacity)
    (theme/'widgets/panel-background.svgz').unlink(missing_ok=True)
    (theme/'widgets/panel-background.svg').write_bytes(panel_data)
    (theme/'metadata.json').write_text(json.dumps({'KPlugin': {'Id': THEME, 'Name': 'KDE Windows Style',
        'Description': 'Breeze com painel levemente translúcido', 'Version': '1.0.0',
        'License': 'GPL-3.0' if style=='win11' else 'LGPL', 'Authors': [{'Name': 'yeyushengfan258' if style=='win11' else 'KDE Visual Design Group'}, {'Name': 'Rk7gamerYT'}]},
        'X-Plasma-API': '5.0'}, indent=2))
    (theme/'plasmarc').write_text('[Settings]\nFallbackTheme=default\n[BlurBehindEffect]\nenabled=true\n'
                                '[ContrastEffect]\nenabled=false\n[AdaptiveTransparency]\nenabled=false\n')
    scheme = 'BreezeDark' if dark else 'BreezeLight'
    colors = Path('/usr/share/color-schemes')/(scheme+'.colors')
    if colors.exists() and style != 'win11':
        shutil.copy2(colors, theme/'colors')
    if style=='win11':
        scheme='KDEWindowsWin11'+('Dark' if dark else 'Light')
        color_file=DATA/'color-schemes'/(scheme+'.colors')
        color_file.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(theme/'colors',color_file)
    run('plasma-apply-colorscheme', scheme)
    run('plasma-apply-desktoptheme', THEME)


def install_decoration(dark):
    """Win11OS window borders (Aurorae): rounded corners and wide Windows 11 caption buttons."""
    ref=ASSETS['win11-plasma'][1]
    with tempfile.TemporaryDirectory() as temp:
        with tarfile.open(community_archive('win11-plasma')) as tar:
            tar.extractall(temp, filter='data')
        for variant in ['dark', 'light']:
            source=Path(temp)/('Win11OS-kde-'+ref)/'aurorae'/('Win11OS-'+variant)
            name=DECORATION+'-'+variant
            target=DATA/'aurorae/themes'/name
            if target.exists():shutil.rmtree(target)
            shutil.copytree(source, target)
            # Aurorae finds the layout as <theme name>rc, so the renamed copy needs a renamed rc file.
            (target/('Win11OS-'+variant+'rc')).rename(target/(name+'rc'))
            meta=target/'metadata.desktop'
            meta.write_text(meta.read_text().replace('Win11OS-'+variant, name))
    theme=DECORATION+('-dark' if dark else '-light')
    write_config('kwinrc', 'org.kde.kdecoration2', 'library', 'org.kde.kwin.aurorae')
    write_config('kwinrc', 'org.kde.kdecoration2', 'theme', '__aurorae__svg__'+theme)
    write_config('kwinrc', 'org.kde.kdecoration2', 'BorderSize', 'Normal')
    write_config('kwinrc', 'org.kde.kdecoration2', 'BorderSizeAuto', 'false')
    print('Bordas de janela Win11OS instaladas, de yeyushengfan258 (GPL-3.0).')


def apply_decoration(style, dark):
    if style=='win11':
        install_decoration(dark)
    else:
        # Breeze with the thin outline Windows 11 draws around windows.
        write_config('kwinrc', 'org.kde.kdecoration2', 'library', 'org.kde.breeze')
        write_config('kwinrc', 'org.kde.kdecoration2', 'theme', 'Breeze')
        write_config('kwinrc', 'org.kde.kdecoration2', 'BorderSize', 'Tiny')
        write_config('kwinrc', 'org.kde.kdecoration2', 'BorderSizeAuto', 'false')
    # Minimize, maximize and close on the right, as on Windows.
    write_config('kwinrc', 'org.kde.kdecoration2', 'ButtonsOnLeft', '')
    write_config('kwinrc', 'org.kde.kdecoration2', 'ButtonsOnRight', 'IAX')


def apply_menus(opacity):
    """Context menus of Qt apps: translucent with blur behind, like Windows 11 acrylic menus."""
    write_config('breezerc', 'Style', 'MenuOpacity', opacity)
    write_config('kwinrc', 'Plugins', 'blurEnabled', 'true')


def install_icons():
    marker = DATA/'icons'/ICON_NAME/'kde-windows-style-version'
    if marker.is_file() and marker.read_text().strip() == ICON_REF and (DATA/'icons'/(ICON_NAME+'-dark')/'index.theme').is_file():
        print('Ícones Fluent já instalados; mantendo a versão verificada.')
        return
    bundled=ROOT/'vendor/fluent-icons.tar.gz'
    cache = Path(os.environ.get('XDG_CACHE_HOME') or Path.home()/'.cache')/'kde-windows-style'
    cache.mkdir(parents=True, exist_ok=True)
    archive = bundled if bundled.is_file() else cache/(ICON_REF+'.tar.gz')
    if bundled.is_file() and hashlib.sha256(bundled.read_bytes()).hexdigest()!=ICON_SHA256:
        raise RuntimeError('Arquivo Fluent incluso corrompido.')
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != ICON_SHA256:
        temporary = archive.with_suffix('.download')
        run('curl', '-fL', '--retry', '3', '-o', temporary,
            f'https://github.com/vinceliuice/Fluent-icon-theme/archive/{ICON_REF}.tar.gz')
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != ICON_SHA256:
            temporary.unlink(missing_ok=True)
            raise RuntimeError('Checksum dos ícones Fluent inválido.')
        temporary.replace(archive)
    with tempfile.TemporaryDirectory() as temp:
        with tarfile.open(archive) as tar:
            tar.extractall(temp, filter='data')
        installer = Path(temp)/('Fluent-icon-theme-'+ICON_REF)/'install.sh'
        print('Instalando ícones Fluent (GPL-3.0), versão fixada e checksum verificado...')
        run('bash', installer, '-d', DATA/'icons', '-n', ICON_NAME, 'standard')
    marker.write_text(ICON_REF)


def install_win11_icons():
    name='KDEWindowsWin11'
    marker=DATA/'icons'/name/'kde-windows-style-version'
    ref=ASSETS['win11-icons'][1]
    if marker.is_file() and marker.read_text().strip()==ref:
        print('Ícones Win11 já instalados.')
        return
    with tempfile.TemporaryDirectory() as temp:
        with tarfile.open(community_archive('win11-icons')) as tar:
            tar.extractall(temp, filter='data')
        source=Path(temp)/('Win11-icon-theme-'+ref)
        index=source/'src/index.theme'
        index.write_text(index.read_text().replace('Win11',name))
        print('Instalando Win11 icon theme, de yeyushengfan258 (GPL-3.0)...')
        run('bash',source/'install.sh','-d',DATA/'icons','-n',name)
    marker.write_text(ref)


def install_menu11():
    archive=ROOT/'vendor/menu11-next.tar.gz'
    digest='4a55c4e5b8756a1056334dce18a456c44b90c8883796dd353a9787d9970e9a6a'
    if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest()!=digest:
        raise RuntimeError('Menu11 Next incluso ausente ou corrompido.')
    target=DATA/'plasma/plasmoids/menu.11.next'
    with tempfile.TemporaryDirectory() as temp:
        with tarfile.open(archive) as tar:
            tar.extractall(temp,filter='data')
        meta=json.loads((Path(temp)/'metadata.json').read_text())
        if meta['KPlugin']['Id']!='menu.11.next':raise RuntimeError('Pacote Menu11 inesperado.')
        if target.exists():shutil.rmtree(target)
        shutil.copytree(temp,target)
    # The bundled translations still use the old dittomenu domain; Plasma looks them up by plugin id.
    for mo in target.glob('contents/locale/*/LC_MESSAGES/*.mo'):
        mo.rename(mo.with_name('plasma_applet_menu.11.next.mo'))
    patch_menu11_search(target/'contents/ui/MenuRepresentation.qml')
    # Fuller pt_BR translation of the menu, using Windows 11 wording (assets/menu11-locale/*.po).
    for mo in (ROOT/'assets/menu11-locale').glob('*.mo'):
        locale=target/'contents/locale'/mo.stem/'LC_MESSAGES'
        locale.mkdir(parents=True,exist_ok=True)
        shutil.copy2(mo,locale/'plasma_applet_menu.11.next.mo')
    print('Menu11 Next 1.3 instalado, de Eisteed.')


def install_widgets():
    for name in WIDGETS:
        target=DATA/'plasma/plasmoids'/('org.kdewindowsstyle.'+name)
        if target.exists():shutil.rmtree(target)
        shutil.copytree(ROOT/'assets'/name, target)
    (DATA/'plasma/plasmoids'/QUICK_SETTINGS/'contents/code/status.sh').chmod(0o755)


def default_city():
    """The city of the system time zone, e.g. America/Sao_Paulo -> Sao Paulo."""
    try:
        zone=run('timedatectl', 'show', '-p', 'Timezone', '--value')
    except (RuntimeError, OSError, subprocess.SubprocessError):
        zone=os.environ.get('TZ', '')
    return zone.rsplit('/', 1)[-1].replace('_', ' ') if '/' in zone else ''


def tray_overflow(enabled):
    """Start (or stop) keeping background app icons behind the tray arrow, now and at every login."""
    if not enabled:
        # The running watcher notices the missing entry and exits.
        TRAY_AUTOSTART.unlink(missing_ok=True)
        return
    TRAY_AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
    TRAY_AUTOSTART.write_text('[Desktop Entry]\nType=Application\nName=KDE Windows Style: bandeja\n'
                              f'Exec={desktop_exec(["python3", ROOT/"tray_overflow.py", "--watch"])}\n'
                              'NoDisplay=true\nX-KDE-autostart-phase=2\n')
    run('python3', ROOT/'tray_overflow.py', check=False)
    if subprocess.run(['pgrep', '-f', 'tray_overflow.py --watch'], capture_output=True).returncode:
        subprocess.Popen(['python3', str(ROOT/'tray_overflow.py'), '--watch'], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# The taskbar Search box (assets/search) leaves this flag and opens Start; Start then shows its
# search page right away, with the Apps/Files/Settings filters, like Windows 11 Search.
MENU11_SEARCH_PATCH = [
    ('    property bool searching: (searchField.text != "")\n',
     '    property bool searchMode: false\n'
     '    property bool searching: (searchField.text != "") || searchMode\n'),
    # The popup window only takes items, so the probe sits with the menu's own data source.
    ('        Plasma5Support.DataSource {\n            id: executable\n',
     '        Plasma5Support.DataSource {\n'
     '            id: searchModeProbe\n'
     '            engine: "executable"\n'
     '            onNewData: (source, data) => {\n'
     '                disconnectSource(source);\n'
     '                if ((data["stdout"] || "").trim() === "search") root.searchMode = true;\n'
     '            }\n'
     '        }\n\n'
     '        Plasma5Support.DataSource {\n            id: executable\n'),
    ('            reset();\n            rootItem.loadFolders();',
     '            reset();\n'
     '            searchModeProbe.connectSource(\'f="$XDG_RUNTIME_DIR/kde-windows-style-search"; [ -e "$f" ] && rm -f "$f" && echo search # \' + Date.now());\n'
     '            rootItem.loadFolders();'),
    ('        searchDebounce.stop();\n        rootItem.pluginResults = [];',
     '        searchDebounce.stop();\n        root.searchMode = false;\n        rootItem.pluginResults = [];'),
    ('                    if (root.searching) {\n                        searchField.clear();',
     '                    if (searchField.text !== "") {\n                        searchField.clear();'),
    ('                            return i18n("No results for \\"%1\\"", searchField.text);',
     '                            if (searchField.text === "") return i18n("Digite para pesquisar aplicativos, arquivos e configurações");\n'
     '                            return i18n("No results for \\"%1\\"", searchField.text);'),
]


def patch_menu11_search(qml):
    text=qml.read_text()
    if any(old not in text for old, _ in MENU11_SEARCH_PATCH):
        print('Aviso: esta versão do Menu11 não aceita a abertura direta na pesquisa.')
        return
    for old, new in MENU11_SEARCH_PATCH:
        text=text.replace(old, new, 1)
    qml.write_text(text)


def install_start_icon():
    target=DATA/'kde-windows-style/start-menu-icon.svg'
    with tarfile.open(community_archive('win11-icons')) as tar:
        suffix='/src/apps/scalable/distributor-logo-windows.svg'
        members=[entry for entry in tar.getmembers() if entry.name.endswith(suffix) and entry.isfile()]
        if len(members)!=1:raise RuntimeError('Ícone Iniciar não encontrado no pacote Win11.')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(tar.extractfile(members[0]).read())
    return target.as_uri()


def desktop_exec(args):
    def quote(text):
        for char in ('\\', '"', '`', '$'):
            text = text.replace(char, '\\'+char)
        return '"'+text.replace('%', '%%')+'"'
    return ' '.join(quote(str(arg)) for arg in args)


def install_menu():
    apps = DATA/'applications'
    apps.mkdir(parents=True, exist_ok=True)
    commands = [
        ('KDE Windows Style', [ROOT/'launch.sh'], 'preferences-desktop-theme', False),
        ('Restaurar estilo anterior do KDE', [ROOT/'launch.sh', '--restore'], 'edit-undo', False),
        ('Configurações do KDE', ['systemsettings'], 'preferences-system', False),
        ('Capturar região da tela', ['spectacle', '-r', '-b', '-c'], 'spectacle', False),
    ]
    for filename, (title, command, icon, terminal) in zip(MENU, commands):
        content = (f'[Desktop Entry]\nType=Application\nName={title}\nExec={desktop_exec(command)}\n'
                   f'Icon={icon}\nTerminal={str(terminal).lower()}\nCategories=Settings;\n')
        if filename.endswith('screenshot.desktop'):
            content += 'NoDisplay=true\n'
        (apps/filename).write_text(content)
    if shutil.which('update-desktop-database'):
        run('update-desktop-database', apps)
    if shutil.which('kbuildsycoca6'):
        run('kbuildsycoca6', '--noincremental')


def apply_panel(launcher='menu11', align='center', size='normal', recommended=True, tray='win11',
                weather=True, city='', fahrenheit=False, search=True, taskview=True):
    if launcher=='menu11':install_menu11()
    install_widgets()
    icon=install_start_icon()
    menu_type='menu.11.next' if launcher=='menu11' else 'org.kde.plasma.kickoff'
    result = script('''
    var ps = panels();
    var panel = ps.find(p => p.location === "bottom") || ps[0] || new Panel;
    panel.location = "bottom"; panel.height = %d; var center = %s;
    panel.alignment = "left"; panel.hiding = "none"; panel.lengthMode = "fill";
    panel.floating = false; panel.opacity = "translucent";
    function ensure(type) {
        return panel.widgets().find(w => w.type === type) || panel.addWidget(type);
    }
    var menu = ensure(%s);
    panel.widgets().forEach(function(w) {
        if (["menu.11.next","org.kde.plasma.kickoff","org.kde.plasma.kicker","org.kde.plasma.kickerdash"].indexOf(w.type)>=0 && w.id!==menu.id) w.remove();
    });
    menu.currentConfigGroup = ["General"];
    menu.writeConfig("icon", %s);
    if (menu.type === "menu.11.next") {
        // Windows 11 opens Start just above the Start button: centered with a centered taskbar, at the
        // left edge with a left-aligned one. 6x3 pinned grid, recommended files below, user and power at the bottom.
        menu.writeConfig("displayPosition", center ? 2 : 0); menu.writeConfig("showAtCenter", center);
        menu.writeConfig("numberColumns", 6); menu.writeConfig("numberRows", 3);
        menu.writeConfig("showRecentDocs", %s); menu.writeConfig("showRecentApps", false);
        menu.writeConfig("viewUser", true); menu.writeConfig("labels2lines", false);
    }
    var tasks = ensure("org.kde.plasma.icontasks");
    // Windows 11 centers Start and the app icons, so the task list only takes the space it needs.
    tasks.currentConfigGroup = ["General"]; tasks.writeConfig("fill", false);
    panel.widgets().forEach(function(w) {
        if (["org.kde.plasma.pager","org.kde.plasma.marginsseparator","org.kde.plasma.panelspacer"].indexOf(w.type)>=0) w.remove();
    });
    var left = center ? panel.addWidget("org.kde.plasma.panelspacer") : null;
    var right = panel.addWidget("org.kde.plasma.panelspacer");
    var tray = ensure("org.kde.plasma.systemtray");
    var clock = ensure("org.kde.plasma.digitalclock");
    // Small time over date, as on the Windows 11 taskbar, instead of a font scaled to the panel height.
    clock.currentConfigGroup = ["Appearance"]; clock.writeConfig("showDate", true);
    clock.writeConfig("dateDisplayFormat", 2); clock.writeConfig("dateFormat", "shortDate");
    clock.writeConfig("autoFontAndSize", false); clock.writeConfig("fontSize", 9);
    clock.writeConfig("showSeconds", 0);
    var win11Tray = %s;
    // Windows 11 groups network, sound and battery in one quick settings button and puts the
    // notification bell after the clock; Plasma's own tray icons for those are left out to avoid duplicates.
    var grouped = ["org.kde.plasma.networkmanagement", "org.kde.plasma.volume", "org.kde.plasma.battery",
                   "org.kde.plasma.bluetooth", "org.kde.plasma.notifications"];
    tray.currentConfigGroup = ["General"];
    var extra = String(tray.readConfig("extraItems", "")).split(",").filter(x => x);
    var known = String(tray.readConfig("knownItems", "")).split(",").filter(x => x);
    extra = extra.filter(x => !win11Tray || grouped.indexOf(x) < 0);
    if (!win11Tray) grouped.forEach(x => { if (extra.indexOf(x) < 0 && known.indexOf(x) >= 0) extra.push(x); });
    tray.writeConfig("extraItems", extra.join(","));
    var shown = String(tray.readConfig("shownItems", "")).split(",").filter(x => x && grouped.indexOf(x) < 0);
    // The input language stays visible next to the clock, as on Windows.
    if (win11Tray && shown.indexOf("org.kde.plasma.keyboardlayout") < 0) shown.push("org.kde.plasma.keyboardlayout");
    tray.writeConfig("shownItems", shown.join(","));
    // Like Windows 11, other KDE tray widgets wait behind the arrow too; the user can pin any of them back.
    var overflow = ["org.kde.plasma.clipboard", "org.kde.kscreen", "org.kde.plasma.manage-inputmethod",
                    "org.kde.plasma.devicenotifier", "org.kde.plasma.printmanager", "org.kde.plasma.mediacontroller",
                    "org.kde.kdeconnect", "org.kde.plasma.vault", "org.kde.plasma.weather", "org.kde.kupapplet",
                    "org.kde.plasma.keyboardindicator"];
    var hidden = String(tray.readConfig("hiddenItems", "")).split(",").filter(x => x && (win11Tray || overflow.indexOf(x) < 0));
    if (win11Tray) overflow.forEach(x => { if (hidden.indexOf(x) < 0 && shown.indexOf(x) < 0) hidden.push(x); });
    tray.writeConfig("hiddenItems", hidden.join(","));
    panel.widgets().forEach(function(w) {
        if ((w.type === %s || w.type === "org.kde.plasma.notifications") && !win11Tray) w.remove();
    });
    var quick = win11Tray ? ensure(%s) : null;
    var bell = win11Tray ? ensure("org.kde.plasma.notifications") : null;
    var desktop = ensure("org.kde.plasma.showdesktop");
    var items = %s;
    function optional(type, wanted) {
        if (wanted) return ensure(type);
        panel.widgets().forEach(w => { if (w.type === type) w.remove(); });
        return null;
    }
    var weather = optional("org.kdewindowsstyle.weather", items.weather);
    if (weather) {
        weather.currentConfigGroup = ["General"];
        if (items.city) weather.writeConfig("city", items.city);
        weather.writeConfig("fahrenheit", items.fahrenheit);
    }
    var search = optional("org.kdewindowsstyle.search", items.search);
    var taskview = optional("org.kdewindowsstyle.taskview", items.taskview);
    var all = panel.widgets();
    // Windows 11: weather at the far left, then Start, Search, Task view and the apps in the middle.
    // With a left-aligned taskbar the weather moves next to the tray.
    var apps = [menu.id].concat(search ? [search.id] : []).concat(taskview ? [taskview.id] : []).concat([tasks.id]);
    var start = (center ? (weather ? [weather.id] : []).concat([left.id]) : []).concat(apps).concat([right.id])
        .concat(!center && weather ? [weather.id] : []);
    var end = [tray.id].concat(quick ? [quick.id] : []).concat([clock.id]).concat(bell ? [bell.id] : []).concat([desktop.id]);
    var fixed = start.concat(end);
    var removed = ["org.kde.plasma.pager","org.kde.plasma.marginsseparator","org.kde.plasma.panelspacer",
                   "menu.11.next","org.kde.plasma.kickoff","org.kde.plasma.kicker","org.kde.plasma.kickerdash",
                   "org.kdewindowsstyle.weather","org.kdewindowsstyle.search","org.kdewindowsstyle.taskview"];
    var middle = all.filter(w => fixed.indexOf(w.id) < 0 && removed.indexOf(w.type) < 0);
    panel.currentConfigGroup = ["General"];
    var order = start.concat(middle.map(w => w.id)).concat(end).join(";");
    panel.writeConfig("AppletOrder", order);
    print(JSON.stringify({id:panel.id, order:order, opacity:panel.opacity, height:panel.height}));
    ''' % (40 if size=='small' else 48, json.dumps(align=='center'), json.dumps(menu_type), json.dumps(icon),
           json.dumps(recommended), json.dumps(tray=='win11'), json.dumps(QUICK_SETTINGS), json.dumps(QUICK_SETTINGS),
           json.dumps({'weather': weather, 'city': city or default_city(), 'fahrenheit': fahrenheit,
                       'search': search, 'taskview': taskview})))
    print('Painel configurado:', result)
    return json.loads(result)


def prerequisites(icons):
    if os.geteuid() == 0:
        raise RuntimeError('Execute como seu usuário normal, sem sudo.')
    if 'KDE' not in os.environ.get('XDG_CURRENT_DESKTOP', '').upper().split(':'):
        raise RuntimeError('Entre numa sessão KDE Plasma 6 antes de aplicar o perfil.')
    required = ['qdbus6', 'gdbus', 'kwriteconfig6', 'plasmashell', 'systemctl',
                'plasma-apply-desktoptheme', 'plasma-apply-colorscheme', 'dolphin', 'krunner', 'systemsettings', 'spectacle'] + (['curl'] if icons and not (ROOT/'vendor/win11-icons.tar.gz').is_file() else [])
    missing = [name for name in required if not shutil.which(name)]
    if missing:
        raise RuntimeError('Comandos ausentes: '+', '.join(missing)+'. No Ubuntu, confira plasma-workspace, qt6-tools-dev-tools, libglib2.0-bin e curl.')
    version = run('plasmashell', '--version')
    if not version.startswith('plasmashell 6.'):
        raise RuntimeError('Este perfil requer Plasma 6: '+version)
    run('systemctl', '--user', 'is-active', 'plasma-plasmashell.service')
    script('print("Plasma pronto")')


def main():
    parser = argparse.ArgumentParser(description='Visual Windows no KDE Plasma 6, com backup e restauração.')
    parser.add_argument('--restore', nargs='?', const='original', metavar='BACKUP')
    parser.add_argument('--install-menu', action='store_true')
    parser.add_argument('--appearance-only', action='store_true', help='atualizar tema e opacidade sem mudar layout e atalhos')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--no-icons', action='store_true', help='manter os ícones atuais e não baixar Fluent')
    parser.add_argument('--opacity', type=int, default=88, help='opacidade da barra: 50 a 100 (padrão: 88)')
    parser.add_argument('--theme', choices=['dark', 'light'], default='dark')
    parser.add_argument('--style', choices=['win11','breeze'], default='win11')
    parser.add_argument('--icon-theme', choices=['win11','fluent'], default='win11')
    parser.add_argument('--launcher', choices=['menu11','kickoff'], default='menu11')
    parser.add_argument('--decoration', choices=['win11','breeze'], default='win11', help='bordas e botões das janelas')
    parser.add_argument('--menu-opacity', type=int, default=85, help='opacidade dos menus de contexto: 50 a 100 (padrão: 85)')
    parser.add_argument('--taskbar-align', choices=['center','left'], default='center')
    parser.add_argument('--taskbar-size', choices=['normal','small'], default='normal', help='48 px ou 40 px')
    parser.add_argument('--no-recommended', action='store_true', help='esconder a seção Recomendados do menu Iniciar')
    parser.add_argument('--tray', choices=['win11','plasma'], default='win11',
                        help='win11: configurações rápidas e sino de notificações como no Windows 11')
    parser.add_argument('--no-weather', action='store_true', help='sem o clima na barra')
    parser.add_argument('--weather-city', default='', help='cidade do clima (padrão: a do fuso horário)')
    parser.add_argument('--fahrenheit', action='store_true')
    parser.add_argument('--no-search', action='store_true', help='sem a caixa Pesquisar')
    parser.add_argument('--no-taskview', action='store_true', help='sem o botão Visão de tarefas')
    args = parser.parse_args()
    if not 50 <= args.opacity <= 100:
        parser.error('--opacity deve ficar entre 50 e 100')
    if not 50 <= args.menu_opacity <= 100:
        parser.error('--menu-opacity deve ficar entre 50 e 100')
    if args.dry_run:
        print(f'Plano: backup; painel inferior de {40 if args.taskbar_size=="small" else 48} px alinhado '
              f'{"ao centro" if args.taskbar_align=="center" else "à esquerda"}, opacidade {args.opacity}%; tema {args.theme}; '
              f'bordas {args.decoration}; menus com {args.menu_opacity}% de opacidade; '
              f'ícones {"atuais" if args.no_icons else "Fluent"}; menu e atalhos Windows. Nenhuma alteração.\n'
              f'Restauração: {args.restore or "não solicitada"}')
        return
    prerequisites(not args.no_icons and not args.restore)
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE/'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.install_menu:
            install_menu()
            print('Entradas adicionadas ao menu do KDE.')
            return
        if args.restore:
            location = (STATE/args.restore).read_text().strip() if args.restore in ('latest', 'original') else args.restore
            restore(location)
            return
        location = backup()
        try:
            install_menu()
            if not args.no_icons:
                if args.icon_theme=='win11':
                    install_win11_icons()
                    icon_theme='KDEWindowsWin11'+('-dark' if args.theme=='dark' else '')
                else:
                    install_icons()
                    icon_theme=ICON_NAME+('-dark' if args.theme=='dark' else '-light')
                write_config('kdeglobals', 'Icons', 'Theme', icon_theme)
            install_theme(args.opacity, args.theme == 'dark',args.style)
            apply_decoration(args.decoration, args.theme == 'dark')
            apply_menus(args.menu_opacity)
            if not args.appearance_only:
                write_config('kdeglobals', 'KDE', 'SingleClick', 'false')
                write_config('kwinrc', 'ModifierOnlyShortcuts', 'Meta', 'org.kde.plasmashell,/PlasmaShell,org.kde.PlasmaShell,activateLauncherMenu')
                panel_state = apply_panel(args.launcher, args.taskbar_align, args.taskbar_size, not args.no_recommended, args.tray,
                                          not args.no_weather, args.weather_city, args.fahrenheit,
                                          not args.no_search, not args.no_taskview)
                tray_overflow(args.tray == 'win11')
                panel_id = panel_state['id']
                panel_order = panel_state['order']
                set_shortcuts()
            else:
                panel_order = None
                panel_id = int(script('var p=panels().find(p=>p.location==="bottom") || panels()[0]; if(!p) throw new Error("Nenhuma barra encontrada"); print(p.id);'))
            run('qdbus6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure')
            # Some Plasma versions apply opacity live but omit its persistent key.
            stop_plasma()
            try:
                run('kwriteconfig6', '--file', CONFIG/'plasmashellrc', '--group', 'PlasmaViews',
                    '--group', f'Panel {panel_id}', '--key', 'panelOpacity', '2')
                if panel_order is not None:
                    run('kwriteconfig6', '--file', CONFIG/'plasma-org.kde.plasma.desktop-appletsrc',
                        '--group', 'Containments', '--group', str(panel_id), '--group', 'General',
                        '--key', 'AppletOrder', panel_order)
            finally:
                start_plasma()
        except (Exception, KeyboardInterrupt):
            print('Falha ao aplicar; restaurando o backup automaticamente...', file=sys.stderr)
            restore(location)
            raise
        if not (STATE/'original').exists():
            (STATE/'original').write_text(str(location))
        print('Pronto! Menu Iniciar, barra levemente translúcida, bordas, menus, ícones e atalhos aplicados.')
        print('Desfazer: '+desktop_exec([ROOT/'kde-windows-style.sh', '--restore']))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Operação cancelada.', file=sys.stderr)
        sys.exit(130)
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print('Erro:', exc, file=sys.stderr)
        sys.exit(1)
