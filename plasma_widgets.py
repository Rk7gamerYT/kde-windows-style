"""Use Plasma's native scripting API to manage individual widgets."""
import json
import os
from pathlib import Path
import subprocess

NAMES = {
    'org.kde.plasma.digitalclock': 'Relógio digital',
    'org.kde.plasma.analogclock': 'Relógio analógico',
    'org.kde.plasma.kickoff': 'Menu de aplicativos',
    'org.kde.plasma.icontasks': 'Gerenciador de tarefas com ícones',
    'org.kde.plasma.systemtray': 'Bandeja do sistema',
    'org.kde.plasma.folder': 'Visualização de pasta',
    'org.kde.plasma.notes': 'Notas adesivas',
    'org.kde.plasma.showdesktop': 'Mostrar área de trabalho',
    'org.kde.plasma.pager': 'Seletor de áreas de trabalho',
    'org.kde.plasma.weather': 'Previsão do tempo',
    'org.kde.plasma.battery': 'Bateria e energia',
    'org.kde.plasma.volume': 'Volume do áudio',
    'org.kde.plasma.marginsseparator': 'Separador de margens',
    'org.kde.plasma.panelspacer': 'Espaçador do painel',
}


def evaluate(code):
    done = subprocess.run(['qdbus6', 'org.kde.plasmashell', '/PlasmaShell',
                           'org.kde.PlasmaShell.evaluateScript', code],
                          capture_output=True, text=True, timeout=20)
    if done.returncode:
        raise RuntimeError(done.stderr.strip() or done.stdout.strip())
    return done.stdout.strip()


def describe():
    data = json.loads(evaluate('''
        var active = currentActivity();
        var result = {containers: [], catalog: knownWidgetTypes};
        function describe(c, kind) {
            c.currentConfigGroup = [];
            var activity = c.readConfig("activityId", "");
            if (kind === "desktop" && activity && activity !== active) return;
            var g = screenGeometry(c.screen);
            result.containers.push({id:c.id, kind:kind, screen:c.screen,
                rect:[g.x,g.y,g.width,g.height],
                widgets:c.widgets().map(w => ({id:w.id, type:w.type}))});
        }
        desktops().forEach(d => describe(d, "desktop"));
        panels().forEach(p => describe(p, "panel"));
        print(JSON.stringify(result));
    '''))
    data['catalog'] = sorted(set(data['catalog']) - {'org.kde.panel', 'org.kde.desktopcontainment'})
    return data


def container_expression(kind, identifier):
    if kind not in ('desktop', 'panel'):
        raise ValueError('Tipo de área inválido.')
    return ('desktopById' if kind == 'desktop' else 'panelById')+f'({int(identifier)})'


def add(kind, container, plugin):
    if plugin not in describe()['catalog']:
        raise ValueError('Este widget não está instalado no KDE.')
    text = evaluate(f'''var c = {container_expression(kind,container)};
        if (!c) throw new Error("Área não encontrada");
        var w = c.addWidget({json.dumps(plugin)});
        if (!w) throw new Error("O Plasma não conseguiu adicionar o widget");
        print(w.id);''')
    return int(text)


def remove(kind, container, widget):
    evaluate(f'''var c = {container_expression(kind,container)};
        if (!c) throw new Error("Área não encontrada");
        var w = c.widgetById({int(widget)});
        if (!w) throw new Error("Widget não encontrado");
        w.remove();''')


def configure(kind, container, widget):
    evaluate(f'''var c = {container_expression(kind,container)};
        if (!c) throw new Error("Área não encontrada");
        var w = c.widgetById({int(widget)});
        if (!w) throw new Error("Widget não encontrado");
        if (typeof w.showConfigurationInterface === "function") w.showConfigurationInterface();
        else if (typeof w.showConfigurationInteface === "function") w.showConfigurationInteface();
        else throw new Error("Este widget não oferece uma janela de configuração");''')


def move(kind, source, widget, target):
    evaluate(f'''var source = {container_expression(kind,source)};
        var target = {container_expression(kind,target)};
        if (!source || !target) throw new Error("Área não encontrada");
        var w = source.widgetById({int(widget)});
        if (!w) throw new Error("Widget não encontrado");
        target.addWidget(w);''')


def names():
    labels = dict(NAMES)
    roots = [Path('/usr/share/plasma/plasmoids'),
             Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')/'plasma/plasmoids']
    for root in roots:
        for path in root.glob('*/metadata.json'):
            try:
                plugin = json.loads(path.read_text())['KPlugin']
                labels[path.parent.name] = plugin.get('Name[pt_BR]', plugin.get('Name',path.parent.name))
            except (OSError, ValueError, KeyError):
                continue
    return labels
