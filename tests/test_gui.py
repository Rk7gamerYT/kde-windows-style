"""Route every widget operation to the selected monitor without touching the live desktop."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    from PySide6.QtWidgets import QApplication, QMessageBox
    import gui
except ImportError:
    gui=None


@unittest.skipIf(gui is None,'Run using the bundled Qt runtime')
class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.data={'catalog':['org.kde.plasma.digitalclock'], 'containers':[
            {'id':11,'kind':'desktop','screen':0,'rect':[0,0,1920,1080],'widgets':[{'id':40,'type':'org.kde.plasma.digitalclock'}]},
            {'id':22,'kind':'desktop','screen':1,'rect':[1920,0,1920,1080],'widgets':[{'id':50,'type':'org.kde.plasma.digitalclock'}]},
            {'id':33,'kind':'panel','screen':0,'rect':[0,0,1920,1080],'widgets':[]},
        ]}
        for patcher in [patch.object(gui,'CONFIG',root/'gui.json'),patch.object(gui,'STATE',root),
                        patch.object(gui.plasma,'describe',return_value=self.data),patch.object(gui.dooros,'installed',return_value=True)]:
            patcher.start();self.addCleanup(patcher.stop)
        self.window=gui.Window();self.addCleanup(self.window.close)

    def test_selecting_second_monitor_lists_its_widgets(self):
        self.window.monitor.setCurrentIndex(1)
        self.assertEqual(self.window.widgets.item(0).data(gui.Qt.UserRole)['id'],50)

    def test_add_uses_real_container_id_not_monitor_number(self):
        self.window.monitor.setCurrentIndex(1)
        with patch.object(gui.plasma,'add') as add:self.window.add_widget()
        add.assert_called_once_with('desktop',22,'org.kde.plasma.digitalclock')

    def test_configure_and_remove_are_scoped_to_selection(self):
        self.window.widgets.setCurrentRow(0)
        with patch.object(gui.plasma,'configure') as configure:self.window.configure_widget()
        configure.assert_called_once_with('desktop',11,40)
        with patch.object(gui.QMessageBox,'question',return_value=QMessageBox.Yes), patch.object(gui.plasma,'remove') as remove:
            self.window.remove_widget()
        remove.assert_called_once_with('desktop',11,40)

    def test_move_preserves_widget_identity(self):
        self.window.widgets.setCurrentRow(0)
        with patch.object(gui.QInputDialog,'getItem',return_value=('Tela 2 · Área de trabalho · #22',True)),patch.object(gui.plasma,'move') as move:
            self.window.move_widget()
        move.assert_called_once_with('desktop',11,40,22)

    def test_opacity_only_does_not_reset_layout(self):
        self.window.opacity.setValue(94)
        self.window.layout_options.setChecked(False)
        with patch.object(self.window,'start_process') as start:self.window.apply_style()
        args=start.call_args.args[0]
        self.assertEqual(args[args.index('--opacity')+1],'94')
        self.assertIn('--appearance-only',args)
        self.assertIn('6% de transparência',self.window.opacity_label.text())

    def test_no_panel_on_second_monitor_does_not_fall_back_to_first(self):
        self.window.monitor.setCurrentIndex(1);self.window.area.setCurrentIndex(1)
        self.assertIsNone(self.window.container())
        with patch.object(gui.plasma,'add') as add:self.window.add_widget()
        add.assert_not_called()
