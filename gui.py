#!/usr/bin/env python3
"""Graphical appearance and per-monitor widget manager for Plasma 6."""
import json
import os
from pathlib import Path
import sys

from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout, QGroupBox,
    QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSlider, QTabWidget,
    QVBoxLayout, QWidget)

import plasma_widgets as plasma
import dooros

ROOT = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'kde-windows-style/gui.json'
STATE = Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'kde-windows-style'


def button(text, callback):
    widget = QPushButton(text)
    if text.startswith('Aplicar'):widget.setProperty('primary',True)
    widget.clicked.connect(callback)
    return widget


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('KDE Windows Style')
        self.resize(860, 720)
        self.setMinimumSize(680, 580)
        self.setWindowIcon(QIcon.fromTheme('preferences-desktop-theme'))
        try:
            self.prefs = json.loads(CONFIG.read_text())
        except (OSError, ValueError):
            self.prefs = {}
        self.process = None
        self.containers = []
        self.labels = plasma.names()
        body = QWidget(); layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 24, 28, 24); layout.setSpacing(16)
        title = QLabel('Seu KDE, do seu jeito')
        title.setStyleSheet('font-size: 25px; font-weight: 600;')
        layout.addWidget(title)
        subtitle = QLabel('Visual familiar, transparência na medida e widgets em cada tela.')
        subtitle.setStyleSheet('color: #aab6c6;')
        layout.addWidget(subtitle)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.appearance_page(), 'Aparência')
        self.tabs.addTab(self.widgets_page(), 'Widgets por monitor')
        self.tabs.addTab(self.shortcuts_page(), 'Menus e atalhos')
        self.tabs.addTab(self.dooros_page(), 'DoorOS-Dolphin')
        layout.addWidget(self.tabs, 1)
        self.status = QLabel('Pronto para configurar. Nenhuma alteração é feita ao abrir o app.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.progress = QProgressBar(); self.progress.setRange(0, 0); self.progress.hide()
        layout.addWidget(self.progress)
        self.details = QCheckBox('Mostrar detalhes da aplicação')
        self.details.toggled.connect(lambda visible: self.log.setVisible(visible))
        layout.addWidget(self.details)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(130); self.log.hide()
        layout.addWidget(self.log)
        self.setCentralWidget(body)
        self.refresh_widgets(silent=True)

    def appearance_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setSpacing(18)
        group = QGroupBox('Barra de tarefas'); form = QVBoxLayout(group)
        self.opacity_label = QLabel()
        form.addWidget(self.opacity_label)
        self.opacity = QSlider(Qt.Horizontal); self.opacity.setRange(50, 100)
        self.opacity.setValue(max(50,min(100,int(self.prefs.get('opacity',88)))))
        self.opacity.setTickPosition(QSlider.TicksBelow); self.opacity.setTickInterval(10)
        self.opacity.valueChanged.connect(self.update_opacity_label)
        form.addWidget(self.opacity)
        hints = QHBoxLayout(); hints.addWidget(QLabel('Mais transparente'))
        hints.addStretch(); hints.addWidget(QLabel('Mais sólida')); form.addLayout(hints)
        hint = QLabel('88% é uma transparência leve. 100% deixa o fundo sólido. Clique em Aplicar para atualizar.')
        hint.setWordWrap(True); hint.setStyleSheet('color: #aab6c6;'); form.addWidget(hint)
        layout.addWidget(group)
        form = QFormLayout()
        self.theme = QComboBox(); self.theme.addItem('Escuro', 'dark'); self.theme.addItem('Claro', 'light')
        self.theme.setCurrentIndex(1 if self.prefs.get('theme')=='light' else 0)
        form.addRow('Tema', self.theme); layout.addLayout(form)
        form=QFormLayout()
        self.style=QComboBox(); self.style.addItem('Win11OS · comunidade','win11'); self.style.addItem('Breeze · KDE','breeze')
        self.style.setCurrentIndex(max(0,self.style.findData(self.prefs.get('style','win11'))))
        form.addRow('Estilo do Plasma',self.style)
        self.icons=QComboBox(); self.icons.addItem('Win11 · comunidade','win11'); self.icons.addItem('Fluent · comunidade','fluent'); self.icons.addItem('Manter os ícones atuais','keep')
        self.icons.setCurrentIndex(max(0,self.icons.findData(self.prefs.get('icon_theme','win11'))))
        form.addRow('Ícones',self.icons)
        self.launcher=QComboBox();self.launcher.addItem('Menu11 Next · Windows 11','menu11');self.launcher.addItem('Menu nativo do KDE · Kickoff','kickoff')
        self.launcher.setCurrentIndex(max(0,self.launcher.findData(self.prefs.get('launcher','menu11'))))
        form.addRow('Menu Iniciar',self.launcher);layout.addLayout(form)
        self.layout_options = QCheckBox('Configurar também o layout da barra, menu Iniciar e atalhos')
        self.layout_options.setChecked(not (STATE/'original').exists()); layout.addWidget(self.layout_options)
        self.launcher.currentIndexChanged.connect(lambda _index:self.layout_options.setChecked(True))
        row = QHBoxLayout()
        row.addWidget(button('Aplicar aparência', self.apply_style))
        row.addWidget(button('Restaurar visual anterior', self.restore_style))
        layout.addLayout(row); layout.addStretch()
        self.update_opacity_label()
        return page

    def update_opacity_label(self):
        value = self.opacity.value()
        self.opacity_label.setText(f'<b>{value}% de opacidade</b> · {100-value}% de transparência')

    def shortcuts_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        text = QLabel('<b>Menu Iniciar na esquerda, com pesquisa de aplicativos.</b><br><br>'
            'Win · Abrir menu Iniciar<br>Win + E · Arquivos (Dolphin)<br>'
            'Win + R · Executar / pesquisar (KRunner)<br>Win + I · Configurações do KDE<br>'
            'Win + D · Mostrar área de trabalho<br>Win + Tab · Visão geral<br>'
            'Alt + Tab · Alternar janelas<br>Alt + F4 · Fechar janela<br>'
            'Win + Shift + S · Capturar região (Spectacle)<br>Print · Abrir Spectacle')
        text.setWordWrap(True); text.setStyleSheet('line-height: 1.5;'); layout.addWidget(text)
        note = QLabel('Para ativar este conjunto, marque a opção de configurar layout, menu e atalhos na aba Aparência. '
                      'Conflitos com outros aplicativos aparecem nos detalhes, sem sobrescrever seus atalhos.')
        note.setWordWrap(True); layout.addWidget(note)
        layout.addWidget(button('Abrir configurações de atalhos do KDE',
                                lambda: QProcess.startDetached('systemsettings',['kcm_keys'])))
        layout.addStretch(); return page

    def dooros_page(self):
        page=QWidget(); layout=QVBoxLayout(page)
        title=QLabel('<b>Gerenciador de arquivos com visual Windows 11</b>')
        layout.addWidget(title)
        text=QLabel('DoorOS-Dolphin, do seu projeto, com abas integradas e navegação personalizada. '
                    'Ele fica separado do Dolphin do sistema. Você escolhe se quer usá-lo como padrão.')
        text.setWordWrap(True); layout.addWidget(text)
        self.dooros_status=QLabel('Incluso no pacote e pronto para abrir.' if dooros.installed() else
                                 'Os fontes estão inclusos. Esta cópia ainda precisa ser compilada; pode pedir senha para as dependências.')
        self.dooros_status.setWordWrap(True);layout.addWidget(self.dooros_status)
        layout.addWidget(button('Preparar / registrar DoorOS-Dolphin',lambda:self.start_process(['--install'],ROOT/'dooros.py')))
        layout.addWidget(button('Abrir DoorOS-Dolphin',lambda:QProcess.startDetached(str(ROOT/'dooros-launch.sh'),[])))
        layout.addWidget(button('Usar DoorOS-Dolphin como padrão e no Win+E',lambda:self.start_process(['--default'],ROOT/'dooros.py')))
        layout.addWidget(button('Voltar ao gerenciador de arquivos anterior',lambda:self.start_process(['--restore-default'],ROOT/'dooros.py')))
        note=QLabel('A compilação para Ubuntu 26.04 não inclui a integração opcional com Baloo 26.08. '
                    'O painel de informações e alguns recursos de indexação podem não estar disponíveis.')
        note.setWordWrap(True);note.setStyleSheet('color: #aab6c6;');layout.addWidget(note)
        layout.addStretch();return page

    def widgets_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        top = QHBoxLayout()
        self.monitor = QComboBox(); self.monitor.setMinimumWidth(230)
        self.area = QComboBox(); self.area.addItem('Área de trabalho', 'desktop'); self.area.addItem('Barra de tarefas', 'panel')
        top.addWidget(self.monitor,1); top.addWidget(self.area); top.addWidget(button('Atualizar',self.refresh_widgets))
        layout.addLayout(top)
        self.area_note = QLabel(); self.area_note.setWordWrap(True); layout.addWidget(self.area_note)
        self.widgets = QListWidget(); layout.addWidget(self.widgets,1)
        actions = QHBoxLayout()
        actions.addWidget(button('Configurar',self.configure_widget))
        actions.addWidget(button('Mover para outro monitor',self.move_widget))
        actions.addWidget(button('Remover',self.remove_widget))
        layout.addLayout(actions)
        group = QGroupBox('Adicionar um widget instalado no KDE'); row = QHBoxLayout(group)
        self.catalog = QComboBox(); self.catalog.setMinimumContentsLength(20)
        row.addWidget(self.catalog,1); row.addWidget(button('Adicionar',self.add_widget)); layout.addWidget(group)
        hint = QLabel('A lista usa a atividade atual do KDE. Arraste os widgets no modo de edição do Plasma para posicioná-los. '
                      'Se a tela tiver mais de uma barra, o app gerencia a primeira barra listada nela.')
        hint.setWordWrap(True); hint.setStyleSheet('color: #aab6c6;'); layout.addWidget(hint)
        self.monitor.currentIndexChanged.connect(self.show_widgets)
        self.area.currentIndexChanged.connect(self.show_widgets)
        return page

    def refresh_widgets(self, _checked=False, silent=False):
        try:
            data = plasma.describe()
            self.containers = data['containers']
            old = self.monitor.currentData()
            self.monitor.blockSignals(True); self.monitor.clear()
            monitors = {}
            for c in self.containers:
                label = f"Tela {c['screen']+1}"
                for screen in QApplication.screens():
                    rect=screen.geometry()
                    if [rect.x(),rect.y(),rect.width(),rect.height()]==c['rect']:
                        label=screen.name()+f' · {rect.width()} × {rect.height()}'
                monitors[c['screen']] = label
            for screen,label in sorted(monitors.items()):self.monitor.addItem(label,screen)
            index=self.monitor.findData(old)
            if index>=0:self.monitor.setCurrentIndex(index)
            self.monitor.blockSignals(False)
            selected=self.catalog.currentData()
            self.catalog.clear()
            for plugin in sorted(data['catalog'],key=lambda p:self.labels.get(p,p).casefold()):
                self.catalog.addItem(self.labels.get(plugin,plugin),plugin)
            index=self.catalog.findData(selected)
            if index>=0:self.catalog.setCurrentIndex(index)
            self.show_widgets()
        except Exception as exc:
            if not silent:self.error(exc)
            self.area_note.setText('Não foi possível consultar o Plasma. Clique em Atualizar quando o desktop estiver pronto.')

    def container(self):
        return next((c for c in self.containers if c['screen']==self.monitor.currentData()
                     and c['kind']==self.area.currentData()),None)

    def show_widgets(self):
        self.widgets.clear(); container=self.container()
        self.area_note.setText('Widgets nesta tela:' if container else
                               'Esta tela não tem uma barra. Selecione Área de trabalho ou crie uma barra pelo editor do KDE.')
        if container:
            for w in container['widgets']:
                item=QListWidgetItem(self.labels.get(w['type'],w['type'])+f"  ·  #{w['id']}")
                item.setData(Qt.UserRole,w); self.widgets.addItem(item)

    def selection(self):
        container=self.container(); item=self.widgets.currentItem()
        if not container or not item:
            self.status.setText('Selecione um widget na lista.'); return None,None
        return container,item.data(Qt.UserRole)

    def error(self, exc):
        self.status.setText('Não foi possível concluir: '+str(exc))
        self.log.appendPlainText(str(exc))

    def add_widget(self):
        container=self.container(); plugin=self.catalog.currentData()
        if not container or not plugin:
            self.status.setText('Selecione uma tela e uma área válida.'); return
        try:
            plasma.add(container['kind'],container['id'],plugin)
            self.refresh_widgets(); self.status.setText('Widget adicionado à tela selecionada.')
        except Exception as exc:self.error(exc)

    def configure_widget(self):
        container,w=self.selection()
        if not w:return
        try:plasma.configure(container['kind'],container['id'],w['id'])
        except Exception as exc:self.error(exc)

    def remove_widget(self):
        container,w=self.selection()
        if not w:return
        answer=QMessageBox.question(self,'Remover widget','Remover este widget e suas configurações da tela selecionada?')
        if answer!=QMessageBox.Yes:return
        try:
            plasma.remove(container['kind'],container['id'],w['id'])
            self.refresh_widgets(); self.status.setText('Widget removido.')
        except Exception as exc:self.error(exc)

    def move_widget(self):
        container,w=self.selection()
        if not w:return
        targets=[c for c in self.containers if c['kind']==container['kind'] and c['screen']!=container['screen']]
        if not targets:
            self.status.setText('Não há outra tela com esse tipo de área.'); return
        choices=[f"Tela {c['screen']+1} · {self.area.currentText()} · #{c['id']}" for c in targets]
        choice,ok=QInputDialog.getItem(self,'Mover widget','Destino:',choices,0,False)
        if not ok:return
        try:
            target=targets[choices.index(choice)]
            plasma.move(container['kind'],container['id'],w['id'],target['id'])
            self.refresh_widgets(); self.status.setText('Widget movido com suas configurações.')
        except Exception as exc:self.error(exc)

    def apply_style(self):
        args=['--opacity',str(self.opacity.value()),'--theme',self.theme.currentData()]
        args+=['--style',self.style.currentData(),'--launcher',self.launcher.currentData()]
        if self.icons.currentData()=='keep':args.append('--no-icons')
        else:args+=['--icon-theme',self.icons.currentData()]
        if not self.layout_options.isChecked():args.append('--appearance-only')
        self.start_process(args)

    def restore_style(self):
        if not (STATE/'original').is_file():
            self.status.setText('Ainda não existe um backup do visual original.'); return
        if QMessageBox.question(self,'Restaurar visual','Voltar ao layout do backup original? Widgets e ajustes feitos depois desse backup também serão restaurados.') == QMessageBox.Yes:
            self.start_process(['--restore'])

    def start_process(self,args,program=None):
        if self.process is not None:return
        self.log.clear(); self.progress.show(); self.tabs.setEnabled(False)
        self.status.setText('Aplicando… A barra pode desaparecer brevemente durante o recarregamento do Plasma.')
        self.process=QProcess(self); self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        if program is not None:self.process.start('/usr/bin/python3',[str(program),*args])
        else:self.process.start(str(ROOT/'kde-windows-style.sh'),args)

    def read_output(self):
        if self.process:
            self.log.appendPlainText(bytes(self.process.readAllStandardOutput()).decode(errors='replace').rstrip())

    def process_error(self,error):
        if error==QProcess.FailedToStart:self.finished(-1)

    def finished(self,code,*_args):
        if self.process is None:return
        self.read_output(); self.process.deleteLater(); self.process=None
        self.progress.hide(); self.tabs.setEnabled(True)
        if code==0:
            self.status.setText('Pronto. Configuração aplicada.')
            CONFIG.parent.mkdir(parents=True,exist_ok=True)
            temporary=CONFIG.with_suffix('.tmp')
            temporary.write_text(json.dumps(dict(opacity=self.opacity.value(),theme=self.theme.currentData(),icon_theme=self.icons.currentData(),style=self.style.currentData(),launcher=self.launcher.currentData())))
            temporary.replace(CONFIG)
            self.layout_options.setChecked(False)
        else:
            self.status.setText('A operação não terminou. Abra os detalhes para conferir o motivo.')
            self.details.setChecked(True)
        self.dooros_status.setText('Incluso e pronto para abrir.' if dooros.installed() else 'Fontes inclusos; compilação pendente nesta cópia.')
        QTimer.singleShot(1200,lambda:self.refresh_widgets(silent=True))

    def closeEvent(self,event):
        if self.process is not None:
            self.status.setText('Aguarde a operação terminar antes de fechar.'); event.ignore()
        else:event.accept()


def create_app():
    app=QApplication(sys.argv); app.setApplicationName('kde-windows-style')
    app.setDesktopFileName('kde-windows-style-apply')
    app.setStyle('Fusion')
    palette=QPalette()
    for role,color in [(QPalette.Window,'#141c28'),(QPalette.WindowText,'#edf3fb'),
        (QPalette.Base,'#101722'),(QPalette.AlternateBase,'#1c2736'),(QPalette.Text,'#edf3fb'),
        (QPalette.Button,'#243246'),(QPalette.ButtonText,'#edf3fb'),(QPalette.Highlight,'#257bd9'),
        (QPalette.HighlightedText,'#ffffff')]:palette.setColor(role,QColor(color))
    app.setPalette(palette)
    app.setStyleSheet('QPushButton{padding:8px 12px;border-radius:6px;background:#25384e;border:1px solid #36516f;} QPushButton:hover{background:#355270;} QPushButton:disabled{background:#182433;color:#718197;} QPushButton[primary="true"]{background:#2279d4;border:1px solid #61a5e9;font-weight:600;} QComboBox{padding:7px;} QCheckBox::indicator{width:16px;height:16px;border:1px solid #879cb5;border-radius:3px;background:#101b2c;} QCheckBox::indicator:checked{background:#2782e2;} '
        'QTabWidget::pane{border:1px solid #2b3b50;border-radius:7px;} '
        'QGroupBox{padding-top:16px;margin-top:8px;} QSlider::handle:horizontal{background:#62aaff;width:18px;margin:-5px 0;border-radius:9px;} '
        'QSlider::groove:horizontal{height:7px;background:#30445f;border-radius:3px;}')
    return app


def main():
    app=create_app()
    window=Window(); window.show()
    if '--restore' in sys.argv:QTimer.singleShot(300,window.restore_style)
    if '--smoke-test' in sys.argv:QTimer.singleShot(1200,app.quit)
    return app.exec()


if __name__=='__main__':sys.exit(main())
