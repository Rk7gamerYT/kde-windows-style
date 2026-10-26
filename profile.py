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
FILES = ['plasma-org.kde.plasma.desktop-appletsrc', 'plasmashellrc', 'plasmarc', 'kdeglobals', 'kwinrc']
MENU = ['kde-windows-style-apply.desktop', 'kde-windows-style-restore.desktop',
        'kde-windows-style-settings.desktop', 'kde-windows-style-screenshot.desktop']
OWNED = [DATA/'plasma/desktoptheme'/THEME]
OWNED += [DATA/'icons'/name for name in [ICON_NAME, ICON_NAME+'-light', ICON_NAME+'-dark',
                                        '.'+ICON_NAME+'-base', '.'+ICON_NAME+'-light-base', '.'+ICON_NAME+'-dark-base']]
OWNED += [DATA/'applications'/name for name in MENU]
OWNED += [DATA/'icons'/name for name in ['KDEWindowsWin11','KDEWindowsWin11-dark']]
OWNED += [DATA/'color-schemes'/name for name in ['KDEWindowsWin11Dark.colors','KDEWindowsWin11Light.colors']]
OWNED += [DATA/'plasma/plasmoids/menu.11.next',DATA/'kde-windows-style/start-menu-icon.svg']
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
        (location/'manifest.json').write_text(json.dumps({'owned': entries, 'shortcuts': shortcuts}, indent=2))
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
        for name in FILES:
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
    # Fuller pt_BR translation of the menu, using Windows 11 wording (assets/menu11-locale/*.po).
    for mo in (ROOT/'assets/menu11-locale').glob('*.mo'):
        locale=target/'contents/locale'/mo.stem/'LC_MESSAGES'
        locale.mkdir(parents=True,exist_ok=True)
        shutil.copy2(mo,locale/'plasma_applet_menu.11.next.mo')
    print('Menu11 Next 1.3 instalado, de Eisteed.')


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


def apply_panel(launcher='menu11'):
    if launcher=='menu11':install_menu11()
    icon=install_start_icon()
    menu_type='menu.11.next' if launcher=='menu11' else 'org.kde.plasma.kickoff'
    result = script('''
    var ps = panels();
    var panel = ps.find(p => p.location === "bottom") || ps[0] || new Panel;
    panel.location = "bottom"; panel.height = 48;
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
        // Windows 11 opens Start centered just above the taskbar: 6x3 pinned grid, recommended files below.
        menu.writeConfig("displayPosition", 2); menu.writeConfig("showAtCenter", true);
        menu.writeConfig("numberColumns", 6); menu.writeConfig("numberRows", 3);
        menu.writeConfig("showRecentDocs", true); menu.writeConfig("viewUser", true);
    }
    var tasks = ensure("org.kde.plasma.icontasks");
    // Windows 11 centers Start and the app icons, so the task list only takes the space it needs.
    tasks.currentConfigGroup = ["General"]; tasks.writeConfig("fill", false);
    panel.widgets().forEach(function(w) {
        if (["org.kde.plasma.pager","org.kde.plasma.marginsseparator","org.kde.plasma.panelspacer"].indexOf(w.type)>=0) w.remove();
    });
    var left = panel.addWidget("org.kde.plasma.panelspacer");
    var right = panel.addWidget("org.kde.plasma.panelspacer");
    var tray = ensure("org.kde.plasma.systemtray");
    var clock = ensure("org.kde.plasma.digitalclock");
    // Small time over date, as on the Windows 11 taskbar, instead of a font scaled to the panel height.
    clock.currentConfigGroup = ["Appearance"]; clock.writeConfig("showDate", true);
    clock.writeConfig("dateDisplayFormat", 2); clock.writeConfig("dateFormat", "shortDate");
    clock.writeConfig("autoFontAndSize", false); clock.writeConfig("fontSize", 9);
    clock.writeConfig("showSeconds", 0);
    var desktop = ensure("org.kde.plasma.showdesktop");
    var all = panel.widgets();
    var fixed = [left.id, menu.id, tasks.id, right.id, tray.id, clock.id, desktop.id];
    var removed = ["org.kde.plasma.pager","org.kde.plasma.marginsseparator","org.kde.plasma.panelspacer",
                   "menu.11.next","org.kde.plasma.kickoff","org.kde.plasma.kicker","org.kde.plasma.kickerdash"];
    var middle = all.filter(w => fixed.indexOf(w.id) < 0 && removed.indexOf(w.type) < 0);
    panel.currentConfigGroup = ["General"];
    var order = [left.id, menu.id, tasks.id, right.id].concat(middle.map(w => w.id)).concat([tray.id, clock.id, desktop.id]).join(";");
    panel.writeConfig("AppletOrder", order);
    print(JSON.stringify({id:panel.id, order:order, opacity:panel.opacity, height:panel.height}));
    ''' % (json.dumps(menu_type),json.dumps(icon)))
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
    args = parser.parse_args()
    if not 50 <= args.opacity <= 100:
        parser.error('--opacity deve ficar entre 50 e 100')
    if args.dry_run:
        print(f'Plano: backup; painel inferior de 48 px, opacidade {args.opacity}%; tema {args.theme}; '
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
            if not args.appearance_only:
                write_config('kdeglobals', 'KDE', 'SingleClick', 'false')
                write_config('kwinrc', 'org.kde.kdecoration2', 'ButtonsOnLeft', '')
                write_config('kwinrc', 'org.kde.kdecoration2', 'ButtonsOnRight', 'IAX')
                write_config('kwinrc', 'ModifierOnlyShortcuts', 'Meta', 'org.kde.plasmashell,/PlasmaShell,org.kde.PlasmaShell,activateLauncherMenu')
                panel_state = apply_panel(args.launcher)
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
        print('Pronto! Menu Iniciar, barra levemente translúcida, ícones e atalhos aplicados.')
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
