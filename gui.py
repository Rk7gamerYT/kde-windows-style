#!/usr/bin/env python3
"""Graphical appearance and per-monitor widget manager for Plasma 6."""
import json
import os
from pathlib import Path
import sys

from PySide6.QtCore import QPointF, QProcess, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QIcon, QLinearGradient, QPainter, QPainterPath,
    QPalette, QPen, QRadialGradient)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QInputDialog, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSlider, QStackedWidget, QStyle,
    QStyledItemDelegate, QVBoxLayout, QWidget)

import plasma_widgets as plasma
import dooros

ROOT = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'kde-windows-style/gui.json'
STATE = Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'kde-windows-style'
CACHE = Path(os.environ.get('XDG_CACHE_HOME') or Path.home()/'.cache')/'kde-windows-style'

# Windows 11 (Fluent) design tokens; "mica" is the window backdrop, tinted by the accent.
THEMES = {
    'dark': dict(mica='#202020', tint='#1c2433', card='#2b2b2b', card_hover='#323232', stroke='#1d1d1d',
                 divider='#3a3a3a', text='#ffffff', secondary='#c5c5c5', tertiary='#9a9a9a',
                 control='#2d2d2d', control_hover='#323232', control_stroke='#3c3c3c', control_bottom='#454545',
                 accent='#4cc2ff', accent_hover='#47b1e8', on_accent='#000000', subtle='#0fffffff',
                 subtle_hover='#15ffffff', field='#1f1f1f', disabled='#5d5d5d', track='#9a9a9a',
                 info='#2b2b2b', caution='#433519', success='#393d1b'),
    'light': dict(mica='#f3f3f3', tint='#eef2f9', card='#fbfbfb', card_hover='#f6f6f6', stroke='#e5e5e5',
                  divider='#e5e5e5', text='#1a1a1a', secondary='#5d5d5d', tertiary='#8a8a8a',
                  control='#ffffff', control_hover='#f9f9f9', control_stroke='#e5e5e5', control_bottom='#cccccc',
                  accent='#005fb8', accent_hover='#196ebf', on_accent='#ffffff', subtle='#0a000000',
                  subtle_hover='#10000000', field='#ffffff', disabled='#a0a0a0', track='#8a8a8a',
                  info='#fbfbfb', caution='#fff4ce', success='#dff6dd'),
}


def system_scheme():
    try:
        return 'light' if QGuiApplication.styleHints().colorScheme()==Qt.ColorScheme.Light else 'dark'
    except AttributeError:
        return 'dark'


def chevron(color):
    """Combo box arrows are images in Qt style sheets, so cache one per theme color."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE/f'chevron-{color.strip("#")}.svg'
    if not path.exists():
        path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">'
                        f'<path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="{color}" stroke-width="1.2" '
                        'stroke-linecap="round" stroke-linejoin="round"/></svg>')
    return path.as_posix()


def stylesheet(t):
    return f'''
    QWidget{{color:{t['text']};font-size:14px;}}
    QMainWindow,#mica{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {t['tint']},stop:0.55 {t['mica']},stop:1 {t['mica']});}}
    QScrollArea,#page,#scroll{{background:transparent;border:none;}}
    QLabel{{background:transparent;}}
    QLabel[role="title"]{{font-size:28px;font-weight:600;}}
    QLabel[role="subtitle"]{{font-size:20px;font-weight:600;}}
    QLabel[role="caption"]{{color:{t['secondary']};font-size:12px;}}
    QLabel[role="body"]{{color:{t['secondary']};}}
    QLabel[role="section"]{{font-weight:600;padding-top:8px;}}
    QLabel#appname{{font-size:12px;color:{t['secondary']};}}
    QLabel#keycap{{background:{t['control']};border:1px solid {t['control_stroke']};border-bottom:2px solid {t['control_bottom']};
        border-radius:5px;padding:3px 9px;font-size:13px;font-weight:600;}}
    QLabel#plus{{color:{t['tertiary']};}}
    #card{{background:{t['card']};border:1px solid {t['stroke']};border-radius:8px;}}
    #card:hover{{background:{t['card_hover']};}}
    #infobar{{background:{t['info']};border:1px solid {t['stroke']};border-radius:8px;}}
    #infobar[kind="busy"]{{border-color:{t['accent']};}}
    #infobar[kind="error"]{{background:{t['caution']};}}
    #infobar[kind="ok"]{{background:{t['success']};}}
    QFrame#divider{{background:{t['divider']};max-height:1px;border:none;}}
    QListWidget#nav{{background:transparent;border:none;outline:none;}}
    QPushButton{{background:{t['control']};border:1px solid {t['control_stroke']};border-bottom-color:{t['control_bottom']};
        border-radius:5px;padding:6px 14px;min-height:20px;}}
    QPushButton:hover{{background:{t['control_hover']};}}
    QPushButton:pressed{{color:{t['secondary']};}}
    QPushButton:disabled{{color:{t['disabled']};}}
    QPushButton[primary="true"]{{background:{t['accent']};color:{t['on_accent']};border:1px solid {t['accent']};font-weight:600;}}
    QPushButton[primary="true"]:hover{{background:{t['accent_hover']};}}
    QPushButton[subtle="true"]{{background:transparent;border:none;padding:6px 10px;}}
    QPushButton[subtle="true"]:hover{{background:{t['subtle_hover']};}}
    QComboBox{{background:{t['control']};border:1px solid {t['control_stroke']};border-bottom-color:{t['control_bottom']};
        border-radius:5px;padding:5px 12px;min-height:22px;min-width:150px;}}
    QComboBox:hover{{background:{t['control_hover']};}}
    QComboBox::drop-down{{border:none;width:30px;}}
    QComboBox::down-arrow{{image:url({chevron(t['secondary'])});width:12px;height:12px;}}
    QComboBox QAbstractItemView{{background:{t['card']};border:1px solid {t['stroke']};border-radius:8px;padding:4px;
        selection-background-color:{t['subtle_hover']};selection-color:{t['text']};outline:none;}}
    QListWidget#list{{background:transparent;border:none;outline:none;}}
    QListWidget#list::item{{border-radius:5px;padding:9px 10px;margin:1px 0;}}
    QListWidget#list::item:hover{{background:{t['subtle']};}}
    QListWidget#list::item:selected{{background:{t['subtle_hover']};color:{t['text']};border-left:3px solid {t['accent']};}}
    QSlider::groove:horizontal{{height:4px;background:{t['track']};border-radius:2px;}}
    QSlider::sub-page:horizontal{{background:{t['accent']};border-radius:2px;}}
    QSlider::handle:horizontal{{background:{t['accent']};border:5px solid {t['control']};width:10px;height:10px;
        margin:-8px 0;border-radius:10px;}}
    QSlider::handle:horizontal:hover{{border-width:4px;}}
    QProgressBar{{background:transparent;border:none;max-height:3px;}}
    QProgressBar::chunk{{background:{t['accent']};border-radius:1px;}}
    QPlainTextEdit{{background:{t['field']};border:1px solid {t['stroke']};border-radius:8px;padding:8px;
        font-family:monospace;font-size:12px;color:{t['secondary']};}}
    QScrollBar:vertical{{background:transparent;width:8px;margin:2px;}}
    QScrollBar::handle:vertical{{background:{t['track']};border-radius:2px;min-height:30px;margin:0 2px;}}
    QScrollBar::handle:vertical:hover{{margin:0;border-radius:3px;}}
    QScrollBar::add-line,QScrollBar::sub-line,QScrollBar::add-page,QScrollBar::sub-page{{height:0;background:none;}}
    QToolTip{{background:{t['card']};color:{t['text']};border:1px solid {t['stroke']};padding:4px 8px;}}
    '''


def button(text, callback):
    widget = QPushButton(text)
    if text.startswith('Aplicar'):widget.setProperty('primary',True)
    widget.setCursor(Qt.PointingHandCursor)
    widget.clicked.connect(callback)
    return widget


def label(text, role=None, wrap=True):
    widget = QLabel(text)
    if role:widget.setProperty('role',role)
    widget.setWordWrap(wrap)
    return widget


def icon(name, size=20):
    widget = QLabel(); widget.setFixedSize(size+12, size+12); widget.setAlignment(Qt.AlignCenter)
    theme_icon = QIcon.fromTheme(name)
    if theme_icon.isNull():widget.hide()
    else:widget.setPixmap(theme_icon.pixmap(size, size))
    return widget


def card(title, description='', control=None, icon_name=None):
    """A Windows 11 Settings row: icon, title and description on the left, the control on the right."""
    frame = QFrame(); frame.setObjectName('card')
    row = QHBoxLayout(frame); row.setContentsMargins(16, 12, 16, 12); row.setSpacing(14)
    if icon_name:row.addWidget(icon(icon_name))
    text = QVBoxLayout(); text.setSpacing(1)
    text.addWidget(title if isinstance(title, QWidget) else label(title))
    if description:text.addWidget(label(description, 'caption'))
    row.addLayout(text, 1)
    if control is not None:row.addWidget(control, 0, Qt.AlignVCenter)
    return frame


def panel(*widgets, margins=(16, 14, 16, 14), spacing=10):
    frame = QFrame(); frame.setObjectName('card')
    layout = QVBoxLayout(frame); layout.setContentsMargins(*margins); layout.setSpacing(spacing)
    for widget in widgets:
        if isinstance(widget, QWidget):layout.addWidget(widget)
        else:layout.addLayout(widget)
    return frame


class Toggle(QCheckBox):
    """Windows 11 toggle switch with the QCheckBox API."""
    def __init__(self, text=''):
        super().__init__(text); self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        width = 40+(self.fontMetrics().horizontalAdvance(self.text())+12 if self.text() else 0)
        return QSize(width, 24)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, _event):
        t = THEMES[QApplication.instance().property('scheme') or 'dark']
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        track = QRectF(0.5, (self.height()-20)/2+0.5, 39, 19)
        on, hover = self.isChecked(), self.underMouse()
        if on:
            p.setPen(Qt.NoPen); p.setBrush(QColor(t['accent_hover'] if hover else t['accent']))
        else:
            p.setPen(QPen(QColor(t['secondary']), 1)); p.setBrush(QColor(t['subtle_hover'] if hover else t['subtle']))
        p.drawRoundedRect(track, 10, 10)
        radius = 6 if hover else 5
        center = QPointF(track.right()-10 if on else track.left()+10, track.center().y())
        p.setPen(Qt.NoPen); p.setBrush(QColor(t['on_accent'] if on else t['secondary']))
        p.drawEllipse(center, radius, radius)
        if self.text():
            p.setPen(QColor(t['text'] if self.isEnabled() else t['disabled']))
            p.drawText(QRectF(52, 0, self.width()-52, self.height()), Qt.AlignVCenter, self.text())


class NavDelegate(QStyledItemDelegate):
    """Settings-style navigation: rounded highlight and an accent pill on the selected page."""
    def paint(self, p, option, index):
        t = THEMES[QApplication.instance().property('scheme') or 'dark']
        p.save(); p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect).adjusted(4, 2, -4, -2)
        selected, hover = option.state & QStyle.State_Selected, option.state & QStyle.State_MouseOver
        if selected or hover:
            p.setPen(Qt.NoPen); p.setBrush(QColor(t['subtle_hover'] if selected else t['subtle']))
            p.drawRoundedRect(rect, 5, 5)
        if selected:
            p.setBrush(QColor(t['accent']))
            p.drawRoundedRect(QRectF(rect.left(), rect.center().y()-8, 3, 16), 1.5, 1.5)
        index.data(Qt.DecorationRole).paint(p, int(rect.left()+14), int(rect.center().y()-9), 18, 18)
        p.setPen(QColor(t['text'] if option.state & QStyle.State_Enabled else t['disabled']))
        p.drawText(rect.adjusted(46, 0, 0, 0), Qt.AlignVCenter, index.data(Qt.DisplayRole))
        p.restore()

    def sizeHint(self, _option, _index):
        return QSize(220, 40)


class TaskbarPreview(QWidget):
    """Live preview of the bottom bar with the chosen opacity and theme."""
    def __init__(self, window):
        super().__init__(); self.window = window
        self.setMinimumHeight(170); self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        area = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath(); clip.addRoundedRect(area, 8, 8); p.setClipPath(clip)
        dark = self.window.theme.currentData()!='light'
        sky = QLinearGradient(area.topLeft(), area.bottomRight())
        sky.setColorAt(0, QColor('#0b1a3d' if dark else '#b9d4f6')); sky.setColorAt(1, QColor('#0a2a6b' if dark else '#7aa9ee'))
        p.fillRect(area, sky)
        for cx, cy, r, color in [(0.5, 1.05, 0.62, '#2f7cf6'), (0.38, 0.95, 0.42, '#5aa2ff'), (0.64, 1.0, 0.38, '#1d5ce0')]:
            bloom = QRadialGradient(QPointF(area.width()*cx, area.height()*cy), area.width()*r)
            c = QColor(color); c.setAlpha(210 if dark else 170); bloom.setColorAt(0, c)
            c.setAlpha(0); bloom.setColorAt(1, c); p.fillRect(area, bloom)
        small = self.window.taskbar_size.currentData()=='small'
        bar = QRectF(area.left(), area.bottom()-(34 if small else 40), area.width(), 34 if small else 40)
        base = QColor('#1c1c1c' if dark else '#f3f3f3'); base.setAlphaF(self.window.opacity.value()/100)
        p.fillRect(bar, base)
        p.setPen(QPen(QColor(255, 255, 255, 30) if dark else QColor(0, 0, 0, 25), 1)); p.drawLine(bar.topLeft(), bar.topRight())
        size, gap, count = (22 if small else 26), 8, 6
        x = area.center().x()-(count*size+(count-1)*gap)/2; y = bar.center().y()-size/2
        if self.window.taskbar_align.currentData()=='left':x = area.left()+10
        colors = ['#0078d4', '#f2c94c', '#2d9cdb', '#eb5757', '#27ae60', '#9b51e0']
        for i, color in enumerate(colors):
            cell = QRectF(x+i*(size+gap), y, size, size)
            if i==0:
                p.setPen(Qt.NoPen); p.setBrush(QColor('#4cc2ff' if dark else '#0067c0'))
                for dx in (0, 1):
                    for dy in (0, 1):p.drawRoundedRect(QRectF(cell.left()+4+dx*size*0.38, cell.top()+4+dy*size*0.38, size*0.33, size*0.33), 1.5, 1.5)
                continue
            p.setPen(Qt.NoPen); p.setBrush(QColor(color)); p.drawRoundedRect(cell.adjusted(3, 3, -3, -3), 5, 5)
        p.setPen(QColor('#ffffff' if dark else '#1a1a1a')); font = p.font(); font.setPixelSize(11); p.setFont(font)
        p.drawText(QRectF(bar.right()-74, bar.top(), 64, bar.height()), Qt.AlignRight|Qt.AlignVCenter, '21:30\n26/10/2026')


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('KDE Windows Style')
        self.resize(1000, 720)
        self.setMinimumSize(760, 560)
        self.setWindowIcon(QIcon.fromTheme('preferences-desktop-theme'))
        try:
            self.prefs = json.loads(CONFIG.read_text())
        except (OSError, ValueError):
            self.prefs = {}
        self.process = None
        self.containers = []
        self.labels = plasma.names()
        body = QWidget(); body.setObjectName('mica')
        outer = QHBoxLayout(body); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        outer.addWidget(self.sidebar())
        content = QVBoxLayout(); content.setContentsMargins(8, 20, 0, 16); content.setSpacing(10)
        self.tabs = QStackedWidget()
        for page in [self.appearance_page(), self.widgets_page(), self.shortcuts_page(), self.dooros_page()]:
            self.tabs.addWidget(self.scroll(page))
        self.nav.currentRowChanged.connect(self.tabs.setCurrentIndex)
        content.addWidget(self.tabs, 1)
        content.addWidget(self.status_area())
        outer.addLayout(content, 1)
        self.setCentralWidget(body)
        self.refresh_widgets(silent=True)

    def sidebar(self):
        side = QWidget(); side.setFixedWidth(270)
        layout = QVBoxLayout(side); layout.setContentsMargins(12, 18, 8, 16); layout.setSpacing(6)
        head = QHBoxLayout(); head.setContentsMargins(10, 0, 0, 10); head.setSpacing(10)
        head.addWidget(icon('preferences-desktop-theme', 24))
        names = QVBoxLayout(); names.setSpacing(0)
        name = QLabel('KDE Windows Style'); name.setStyleSheet('font-weight:600;')
        names.addWidget(name); app = QLabel('Seu KDE, do seu jeito'); app.setObjectName('appname'); names.addWidget(app)
        head.addLayout(names, 1); layout.addLayout(head)
        self.nav = QListWidget(); self.nav.setObjectName('nav'); self.nav.setItemDelegate(NavDelegate(self.nav))
        self.nav.setMouseTracking(True); self.nav.setCursor(Qt.PointingHandCursor)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for text, name in [('Aparência', 'preferences-desktop-color'), ('Widgets por monitor', 'video-display'),
                           ('Menus e atalhos', 'preferences-desktop-keyboard-shortcut'), ('DoorOS-Dolphin', 'system-file-manager')]:
            self.nav.addItem(QListWidgetItem(QIcon.fromTheme(name), text))
        self.nav.setCurrentRow(0)
        layout.addWidget(self.nav, 1)
        self.ui_theme = QComboBox()
        for text, data in [('Usar tema do sistema', 'system'), ('Claro', 'light'), ('Escuro', 'dark')]:self.ui_theme.addItem(text, data)
        self.ui_theme.setCurrentIndex(max(0, self.ui_theme.findData(self.prefs.get('ui_theme', 'system'))))
        self.ui_theme.setToolTip('Tema desta janela. Não muda o KDE.')
        self.ui_theme.currentIndexChanged.connect(self.change_ui_theme)
        layout.addWidget(label('Tema do app', 'caption')); layout.addWidget(self.ui_theme)
        return side

    def scroll(self, page):
        area = QScrollArea(); area.setObjectName('scroll'); area.setWidgetResizable(True); area.setFrameShape(QFrame.NoFrame)
        page.setObjectName('page'); area.setWidget(page); area.viewport().setAutoFillBackground(False)
        return area

    def page(self, title, subtitle=''):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 8, 28, 16); layout.setSpacing(6)
        page.setMaximumWidth(1000)
        layout.addWidget(label(title, 'title'))
        if subtitle:layout.addWidget(label(subtitle, 'body'))
        layout.addSpacing(12)
        return page, layout

    def status_area(self):
        box = QWidget(); layout = QVBoxLayout(box); layout.setContentsMargins(28, 0, 28, 0); layout.setSpacing(8)
        self.infobar = QFrame(); self.infobar.setObjectName('infobar')
        bar = QVBoxLayout(self.infobar); bar.setContentsMargins(0, 0, 0, 0); bar.setSpacing(0)
        self.progress = QProgressBar(); self.progress.setRange(0, 0); self.progress.setTextVisible(False); self.progress.hide()
        bar.addWidget(self.progress)
        row = QHBoxLayout(); row.setContentsMargins(14, 10, 10, 10); row.setSpacing(12)
        self.status_icon = icon('dialog-information', 16); row.addWidget(self.status_icon)
        self.status = label('Pronto para configurar. Nenhuma alteração é feita ao abrir o app.')
        row.addWidget(self.status, 1)
        self.details = Toggle('Detalhes')
        self.details.toggled.connect(lambda visible: self.log.setVisible(visible))
        row.addWidget(self.details); bar.addLayout(row)
        layout.addWidget(self.infobar)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(140); self.log.hide()
        layout.addWidget(self.log)
        return box

    def set_status(self, text, kind='info'):
        self.status.setText(text)
        names = dict(info='dialog-information', busy='view-refresh', ok='dialog-ok-apply', error='dialog-warning')
        self.status_icon.setPixmap(QIcon.fromTheme(names[kind]).pixmap(16, 16))
        self.infobar.setProperty('kind', kind); self.infobar.style().unpolish(self.infobar); self.infobar.style().polish(self.infobar)

    def change_ui_theme(self):
        self.prefs['ui_theme'] = self.ui_theme.currentData(); self.save_prefs()
        apply_theme(QApplication.instance(), self.prefs['ui_theme'])
        self.update()

    def save_prefs(self):
        try:
            CONFIG.parent.mkdir(parents=True,exist_ok=True)
            temporary=CONFIG.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.prefs))
            temporary.replace(CONFIG)
        except OSError as exc:self.log.appendPlainText(str(exc))

    def appearance_page(self):
        page, layout = self.page('Aparência', 'Visual familiar, transparência na medida e widgets em cada tela.')
        self.opacity = QSlider(Qt.Horizontal); self.opacity.setRange(50, 100); self.opacity.setMinimumWidth(220)
        self.opacity.setValue(max(50,min(100,int(self.prefs.get('opacity',88)))))
        self.opacity.setCursor(Qt.PointingHandCursor)
        self.theme = QComboBox(); self.theme.addItem('Escuro', 'dark'); self.theme.addItem('Claro', 'light')
        self.theme.setCurrentIndex(1 if self.prefs.get('theme')=='light' else 0)
        self.preview = TaskbarPreview(self)
        self.opacity.valueChanged.connect(self.update_opacity_label)
        self.theme.currentIndexChanged.connect(self.preview.update)
        self.taskbar_align = self.choice([('Centro', 'center'), ('Esquerda', 'left')], 'taskbar_align', 'center')
        self.taskbar_size = self.choice([('Padrão', 'normal'), ('Pequeno', 'small')], 'taskbar_size', 'normal')
        for combo in (self.taskbar_align, self.taskbar_size):combo.currentIndexChanged.connect(self.preview.update)
        layout.addWidget(panel(self.preview, margins=(8, 8, 8, 8)))
        layout.addWidget(label('Barra de tarefas', 'section'))
        self.opacity_label = label('', wrap=False)
        slider = QWidget(); row = QVBoxLayout(slider); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(2)
        row.addWidget(self.opacity)
        hints = QHBoxLayout(); hints.addWidget(label('Mais transparente', 'caption', False)); hints.addStretch()
        hints.addWidget(label('Mais sólida', 'caption', False)); row.addLayout(hints)
        layout.addWidget(card(self.opacity_label, '88% é uma transparência leve. 100% deixa o fundo sólido.', slider, 'preferences-desktop-effects'))
        layout.addWidget(card('Alinhamento', 'No centro, como no Windows 11, ou à esquerda, como no Windows 10.', self.taskbar_align, 'format-justify-center'))
        layout.addWidget(card('Tamanho dos ícones', 'Pequeno deixa a barra com 40 px em vez de 48 px.', self.taskbar_size, 'zoom-fit-height'))
        self.win11_tray = Toggle(); self.win11_tray.setChecked(self.prefs.get('tray', 'win11')=='win11')
        layout.addWidget(card('Bandeja do Windows 11', 'Wi-Fi, som e bateria num só botão de configurações rápidas, sino de notificações '
                              'ao lado do relógio e ícones extras atrás da seta.', self.win11_tray, 'preferences-system-notifications'))
        layout.addWidget(label('Personalização', 'section'))
        layout.addWidget(card('Modo de cor', 'Tema claro ou escuro para o Plasma e os aplicativos.', self.theme, 'preferences-desktop-color'))
        self.style=QComboBox(); self.style.addItem('Win11OS · comunidade','win11'); self.style.addItem('Breeze · KDE','breeze')
        self.style.setCurrentIndex(max(0,self.style.findData(self.prefs.get('style','win11'))))
        layout.addWidget(card('Estilo do Plasma', 'Painéis, menus e decoração das janelas.', self.style, 'preferences-desktop-theme'))
        self.icons=QComboBox(); self.icons.addItem('Win11 · comunidade','win11'); self.icons.addItem('Fluent · comunidade','fluent'); self.icons.addItem('Manter os ícones atuais','keep')
        self.icons.setCurrentIndex(max(0,self.icons.findData(self.prefs.get('icon_theme','win11'))))
        layout.addWidget(card('Ícones', 'Ícones de pastas, aplicativos e sistema.', self.icons, 'preferences-desktop-icons'))
        self.launcher=QComboBox();self.launcher.addItem('Menu11 Next · Windows 11','menu11');self.launcher.addItem('Menu nativo do KDE · Kickoff','kickoff')
        self.launcher.setCurrentIndex(max(0,self.launcher.findData(self.prefs.get('launcher','menu11'))))
        layout.addWidget(card('Menu Iniciar', 'Menu centralizado com pesquisa, fixados e recomendados.', self.launcher, 'start-here'))
        self.recommended = Toggle(); self.recommended.setChecked(self.prefs.get('recommended', True))
        layout.addWidget(card('Mostrar Recomendados', 'Arquivos recentes abaixo dos aplicativos fixados no menu Iniciar.', self.recommended, 'document-open-recent'))
        layout.addWidget(label('Janelas e menus', 'section'))
        self.decoration = self.choice([('Win11OS · Windows 11', 'win11'), ('Breeze · KDE', 'breeze')], 'decoration', 'win11')
        layout.addWidget(card('Bordas das janelas', 'Cantos arredondados e botões minimizar, maximizar e fechar à direita.', self.decoration, 'preferences-system-windows-actions'))
        self.menu_opacity = self.choice([('Acrílico · translúcido', 85), ('Leve', 95), ('Sólido', 100)], 'menu_opacity', 85)
        layout.addWidget(card('Menus de contexto', 'Menus do botão direito com fundo desfocado, como no Windows 11. Vale para apps abertos depois de aplicar.',
                              self.menu_opacity, 'application-menu'))
        self.layout_options = Toggle()
        self.layout_options.setChecked(not (STATE/'original').exists())
        layout.addWidget(card('Layout, menu Iniciar e atalhos', 'Reorganiza a barra e ativa os atalhos do Windows. '
                              'Desligado, só cores, ícones, bordas, menus e opacidade mudam.', self.layout_options, 'preferences-system-windows'))
        # These live in the taskbar layout, so changing them needs the layout step.
        for combo in (self.launcher, self.taskbar_align, self.taskbar_size):
            combo.currentIndexChanged.connect(lambda _index:self.layout_options.setChecked(True))
        for toggle in (self.recommended, self.win11_tray):toggle.toggled.connect(lambda _on:self.layout_options.setChecked(True))
        row = QHBoxLayout(); row.setContentsMargins(0, 14, 0, 0); row.setSpacing(8)
        row.addWidget(button('Aplicar aparência', self.apply_style))
        row.addWidget(button('Restaurar visual anterior', self.restore_style)); row.addStretch()
        layout.addLayout(row); layout.addStretch()
        self.update_opacity_label()
        return page

    def choice(self, items, key, default):
        combo = QComboBox()
        for text, data in items:combo.addItem(text, data)
        combo.setCurrentIndex(max(0, combo.findData(self.prefs.get(key, default))))
        return combo

    def update_opacity_label(self):
        value = self.opacity.value()
        self.opacity_label.setText(f'<b>{value}% de opacidade</b> · {100-value}% de transparência')
        self.preview.update()

    def shortcuts_page(self):
        page, layout = self.page('Menus e atalhos', 'Menu Iniciar centralizado, com pesquisa de aplicativos, e os atalhos que você já conhece do Windows.')
        keys = [('Win', 'Abrir menu Iniciar'), ('Win E', 'Arquivos (Dolphin)'), ('Win R', 'Executar / pesquisar (KRunner)'),
                ('Win I', 'Configurações do KDE'), ('Win D', 'Mostrar área de trabalho'), ('Win Tab', 'Visão geral'),
                ('Alt Tab', 'Alternar janelas'), ('Alt F4', 'Fechar janela'), ('Win Shift S', 'Capturar região (Spectacle)'),
                ('Print', 'Abrir Spectacle')]
        frame = QFrame(); frame.setObjectName('card')
        grid = QGridLayout(frame); grid.setContentsMargins(16, 10, 16, 10); grid.setHorizontalSpacing(18); grid.setVerticalSpacing(0)
        for row, (combo, action) in enumerate(keys):
            caps = QHBoxLayout(); caps.setSpacing(4); caps.setContentsMargins(0, 7, 0, 7)
            for i, key in enumerate(combo.split()):
                if i:plus = QLabel('+'); plus.setObjectName('plus'); caps.addWidget(plus)
                cap = QLabel(key); cap.setObjectName('keycap'); caps.addWidget(cap)
            caps.addStretch()
            grid.addLayout(caps, row*2, 0); grid.addWidget(label(action, wrap=False), row*2, 1)
            if row<len(keys)-1:
                line = QFrame(); line.setObjectName('divider'); line.setFixedHeight(1); grid.addWidget(line, row*2+1, 0, 1, 2)
        grid.setColumnStretch(1, 1)
        layout.addWidget(frame)
        layout.addWidget(label('Para ativar este conjunto, ligue “Layout, menu Iniciar e atalhos” em Aparência. '
                               'Conflitos com outros aplicativos aparecem nos detalhes, sem sobrescrever seus atalhos.', 'caption'))
        layout.addSpacing(8)
        layout.addWidget(card('Atalhos do KDE', 'Revise ou personalize qualquer atalho.',
                              button('Abrir', lambda: QProcess.startDetached('systemsettings',['kcm_keys'])), 'preferences-desktop-keyboard-shortcut'))
        layout.addStretch(); return page

    def dooros_page(self):
        page, layout = self.page('DoorOS-Dolphin', 'Gerenciador de arquivos com visual do Explorador do Windows 11, abas integradas e navegação personalizada. '
                                 'Fica separado do Dolphin do sistema: você escolhe se quer usá-lo como padrão.')
        self.dooros_status=label('Incluso no pacote e pronto para abrir.' if dooros.installed() else
                                 'Os fontes estão inclusos. Esta cópia ainda precisa ser compilada; pode pedir senha para as dependências.', 'caption')
        hero = QFrame(); hero.setObjectName('card'); row = QHBoxLayout(hero); row.setContentsMargins(16, 16, 16, 16); row.setSpacing(16)
        row.addWidget(icon('system-file-manager', 48))
        text = QVBoxLayout(); text.setSpacing(2); text.addWidget(label('DoorOS-Dolphin', 'subtitle')); text.addWidget(self.dooros_status)
        row.addLayout(text, 1)
        row.addWidget(button('Abrir',lambda:QProcess.startDetached(str(ROOT/'dooros-launch.sh'),[])))
        layout.addWidget(hero)
        layout.addWidget(label('Configuração', 'section'))
        layout.addWidget(card('Preparar e registrar', 'Adiciona o DoorOS-Dolphin ao menu de aplicativos.',
                              button('Preparar',lambda:self.start_process(['--install'],ROOT/'dooros.py')), 'run-build'))
        layout.addWidget(card('Usar como padrão', 'Abre pastas e o atalho Win + E no DoorOS-Dolphin.',
                              button('Usar como padrão',lambda:self.start_process(['--default'],ROOT/'dooros.py')), 'starred'))
        layout.addWidget(card('Voltar ao anterior', 'Devolve pastas e Win + E ao gerenciador de arquivos de antes.',
                              button('Restaurar',lambda:self.start_process(['--restore-default'],ROOT/'dooros.py')), 'edit-undo'))
        layout.addWidget(label('A compilação para Ubuntu 26.04 não inclui a integração opcional com Baloo 26.08. '
                               'O painel de informações e alguns recursos de indexação podem não estar disponíveis.', 'caption'))
        layout.addStretch();return page

    def widgets_page(self):
        page, layout = self.page('Widgets por monitor', 'Escolha uma tela e uma área para ver, configurar, mover ou remover widgets.')
        self.monitor = QComboBox(); self.monitor.setMinimumWidth(230)
        self.area = QComboBox(); self.area.addItem('Área de trabalho', 'desktop'); self.area.addItem('Barra de tarefas', 'panel')
        top = QHBoxLayout(); top.setSpacing(8)
        top.addWidget(self.monitor,1); top.addWidget(self.area); top.addWidget(button('Atualizar',self.refresh_widgets))
        self.area_note = label('', 'caption')
        self.widgets = QListWidget(); self.widgets.setObjectName('list'); self.widgets.setMinimumHeight(200)
        actions = QHBoxLayout(); actions.setSpacing(8)
        actions.addWidget(button('Configurar',self.configure_widget))
        actions.addWidget(button('Mover para outro monitor',self.move_widget))
        actions.addWidget(button('Remover',self.remove_widget)); actions.addStretch()
        layout.addWidget(panel(top, self.area_note, self.widgets, actions))
        layout.addWidget(label('Adicionar widget', 'section'))
        self.catalog = QComboBox(); self.catalog.setMinimumContentsLength(20)
        add = QWidget(); row = QHBoxLayout(add); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(8)
        row.addWidget(self.catalog,1); row.addWidget(button('Adicionar',self.add_widget))
        layout.addWidget(card('Widget instalado no KDE', 'É adicionado à tela e área selecionadas acima.', add, 'list-add'))
        layout.addWidget(label('A lista usa a atividade atual do KDE. Arraste os widgets no modo de edição do Plasma para posicioná-los. '
                               'Se a tela tiver mais de uma barra, o app gerencia a primeira barra listada nela.', 'caption'))
        layout.addStretch()
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
                item=QListWidgetItem(QIcon.fromTheme('plasma'),self.labels.get(w['type'],w['type'])+f"  ·  #{w['id']}")
                item.setData(Qt.UserRole,w); self.widgets.addItem(item)

    def selection(self):
        container=self.container(); item=self.widgets.currentItem()
        if not container or not item:
            self.set_status('Selecione um widget na lista.'); return None,None
        return container,item.data(Qt.UserRole)

    def error(self, exc):
        self.set_status('Não foi possível concluir: '+str(exc), 'error')
        self.log.appendPlainText(str(exc))

    def add_widget(self):
        container=self.container(); plugin=self.catalog.currentData()
        if not container or not plugin:
            self.set_status('Selecione uma tela e uma área válida.'); return
        try:
            plasma.add(container['kind'],container['id'],plugin)
            self.refresh_widgets(); self.set_status('Widget adicionado à tela selecionada.', 'ok')
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
            self.refresh_widgets(); self.set_status('Widget removido.', 'ok')
        except Exception as exc:self.error(exc)

    def move_widget(self):
        container,w=self.selection()
        if not w:return
        targets=[c for c in self.containers if c['kind']==container['kind'] and c['screen']!=container['screen']]
        if not targets:
            self.set_status('Não há outra tela com esse tipo de área.'); return
        choices=[f"Tela {c['screen']+1} · {self.area.currentText()} · #{c['id']}" for c in targets]
        choice,ok=QInputDialog.getItem(self,'Mover widget','Destino:',choices,0,False)
        if not ok:return
        try:
            target=targets[choices.index(choice)]
            plasma.move(container['kind'],container['id'],w['id'],target['id'])
            self.refresh_widgets(); self.set_status('Widget movido com suas configurações.', 'ok')
        except Exception as exc:self.error(exc)

    def apply_style(self):
        args=['--opacity',str(self.opacity.value()),'--theme',self.theme.currentData()]
        args+=['--style',self.style.currentData(),'--launcher',self.launcher.currentData()]
        args+=['--decoration',self.decoration.currentData(),'--menu-opacity',str(self.menu_opacity.currentData())]
        args+=['--taskbar-align',self.taskbar_align.currentData(),'--taskbar-size',self.taskbar_size.currentData()]
        if not self.recommended.isChecked():args.append('--no-recommended')
        args+=['--tray','win11' if self.win11_tray.isChecked() else 'plasma']
        if self.icons.currentData()=='keep':args.append('--no-icons')
        else:args+=['--icon-theme',self.icons.currentData()]
        if not self.layout_options.isChecked():args.append('--appearance-only')
        self.start_process(args)

    def restore_style(self):
        if not (STATE/'original').is_file():
            self.set_status('Ainda não existe um backup do visual original.'); return
        if QMessageBox.question(self,'Restaurar visual','Voltar ao layout do backup original? Widgets e ajustes feitos depois desse backup também serão restaurados.') == QMessageBox.Yes:
            self.start_process(['--restore'])

    def start_process(self,args,program=None):
        if self.process is not None:return
        self.log.clear(); self.progress.show(); self.tabs.setEnabled(False); self.nav.setEnabled(False)
        self.set_status('Aplicando… A barra pode desaparecer brevemente durante o recarregamento do Plasma.', 'busy')
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
        self.progress.hide(); self.tabs.setEnabled(True); self.nav.setEnabled(True)
        if code==0:
            self.set_status('Pronto. Configuração aplicada.', 'ok')
            self.prefs.update(opacity=self.opacity.value(),theme=self.theme.currentData(),icon_theme=self.icons.currentData(),
                              style=self.style.currentData(),launcher=self.launcher.currentData(),
                              decoration=self.decoration.currentData(),menu_opacity=self.menu_opacity.currentData(),
                              taskbar_align=self.taskbar_align.currentData(),taskbar_size=self.taskbar_size.currentData(),
                              recommended=self.recommended.isChecked(),tray='win11' if self.win11_tray.isChecked() else 'plasma')
            self.save_prefs()
            self.layout_options.setChecked(False)
        else:
            self.set_status('A operação não terminou. Abra os detalhes para conferir o motivo.', 'error')
            self.details.setChecked(True)
        self.dooros_status.setText('Incluso e pronto para abrir.' if dooros.installed() else 'Fontes inclusos; compilação pendente nesta cópia.')
        QTimer.singleShot(1200,lambda:self.refresh_widgets(silent=True))

    def closeEvent(self,event):
        if self.process is not None:
            self.set_status('Aguarde a operação terminar antes de fechar.', 'busy'); event.ignore()
        else:event.accept()


def apply_theme(app, choice='system'):
    scheme = system_scheme() if choice=='system' else choice
    t = THEMES[scheme]; app.setProperty('scheme', scheme)
    palette=QPalette()
    for role,color in [(QPalette.Window,t['mica']),(QPalette.WindowText,t['text']),(QPalette.Base,t['field']),
        (QPalette.AlternateBase,t['card']),(QPalette.Text,t['text']),(QPalette.Button,t['control']),
        (QPalette.ButtonText,t['text']),(QPalette.Highlight,t['accent']),(QPalette.HighlightedText,t['on_accent']),
        (QPalette.ToolTipBase,t['card']),(QPalette.ToolTipText,t['text']),(QPalette.PlaceholderText,t['tertiary'])]:
        palette.setColor(role,QColor(color))
    palette.setColor(QPalette.Disabled,QPalette.Text,QColor(t['disabled']))
    palette.setColor(QPalette.Disabled,QPalette.ButtonText,QColor(t['disabled']))
    palette.setColor(QPalette.Disabled,QPalette.WindowText,QColor(t['disabled']))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet(t))


def setup_icons():
    """The bundled Qt has no KDE platform theme, so point it at the user's icon theme from kdeglobals."""
    data=[os.environ.get('XDG_DATA_HOME') or str(Path.home()/'.local/share')]
    data+=(os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share').split(':')
    QIcon.setThemeSearchPaths([*QIcon.themeSearchPaths(),str(Path.home()/'.icons'),*[d+'/icons' for d in data if d]])
    theme=''
    try:
        section=''
        for line in (Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'kdeglobals').read_text().splitlines():
            line=line.strip()
            if line.startswith('['):section=line
            elif section=='[Icons]' and line.startswith('Theme='):theme=line[6:]
    except OSError:pass
    QIcon.setFallbackThemeName('breeze')
    if theme or not QIcon.themeName() or QIcon.themeName()=='hicolor':QIcon.setThemeName(theme or 'breeze')


def create_app():
    app=QApplication(sys.argv); app.setApplicationName('kde-windows-style')
    app.setDesktopFileName('kde-windows-style-apply')
    app.setStyle('Fusion')
    setup_icons()
    font=QFont(); font.setFamilies(['Segoe UI Variable Text','Segoe UI','Inter','Noto Sans',font.family()]); app.setFont(font)
    try:choice=json.loads(CONFIG.read_text()).get('ui_theme','system')
    except (OSError, ValueError):choice='system'
    apply_theme(app,choice)
    try:
        def follow_system(_scheme):
            try:current=json.loads(CONFIG.read_text()).get('ui_theme','system')
            except (OSError, ValueError):current='system'
            if current=='system':apply_theme(app,'system')
        app.styleHints().colorSchemeChanged.connect(follow_system)
    except AttributeError:pass
    return app


def main():
    app=create_app()
    window=Window(); window.show()
    if '--restore' in sys.argv:QTimer.singleShot(300,window.restore_style)
    if '--smoke-test' in sys.argv:QTimer.singleShot(1200,app.quit)
    return app.exec()


if __name__=='__main__':sys.exit(main())
