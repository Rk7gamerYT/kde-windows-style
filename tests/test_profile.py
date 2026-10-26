import gzip
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('profile_script', Path(__file__).resolve().parents[1]/'profile.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ProfileTests(unittest.TestCase):
    def test_variant_preserves_empty_array_type(self):
        self.assertEqual(p.variant_argument('(@a(ai) [],)'), '@a(ai) []')

    def test_variant_preserves_multistroke_shortcuts(self):
        text='([([268435525, 0, 0, 0],), ([67108939, 67108931, 0, 0],)],)'
        self.assertEqual(p.variant_argument(text), text[1:-2])
        with self.assertRaises(ValueError):
            p.variant_argument('unexpected')

    def test_backup_restore_preserves_configs_and_existing_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); config=root/'config'; config.mkdir()
            (config/'kdeglobals').write_bytes(b'original settings\n')
            owned=root/'theme'; owned.mkdir()
            (owned/'original').write_bytes(b'original theme')
            new=root/'new-menu.desktop'
            with patch.object(p, 'CONFIG', config), patch.object(p, 'STATE', root/'state'), \
                 patch.object(p, 'OWNED', [owned,new]), patch.object(p, 'stop_plasma'), \
                 patch.object(p, 'start_plasma'), patch.object(p, 'snapshot_shortcuts', return_value=[]), \
                 patch.object(p, 'set_shortcuts'), patch.object(p, 'run'), patch.object(p,'install_menu'):
                backup=p.backup()
                (config/'kdeglobals').write_text('changed')
                (config/'kwinrc').write_text('new')
                (owned/'original').unlink()
                (owned/'new').touch()
                new.touch()
                p.restore(backup)
                self.assertEqual((config/'kdeglobals').read_bytes(),b'original settings\n')
                self.assertFalse((config/'kwinrc').exists())
                self.assertEqual((owned/'original').read_bytes(),b'original theme')
                self.assertFalse((owned/'new').exists())
                self.assertFalse(new.exists())

    def test_restore_rejects_foreign_paths_before_stopping_plasma(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'manifest.json').write_text(json.dumps({'owned':[{'path':'/different'}]}))
            with patch.object(p,'stop_plasma') as stop:
                with self.assertRaises(RuntimeError):p.restore(root)
                stop.assert_not_called()

    def test_svg_keeps_panel_elements_with_light_transparency(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'panel.svgz'
            source.write_bytes(gzip.compress(b'<svg xmlns="http://www.w3.org/2000/svg"><rect id="center" width="10" height="10"/></svg>'))
            svg=ET.fromstring(p.panel_svg(source,88))
            self.assertEqual(svg.get('opacity'),'0.88')
            self.assertEqual(svg[0].get('id'),'center')

    def test_desktop_exec_escapes_spaces_and_shell_characters(self):
        result=p.desktop_exec(['/path with spaces/tool', 'a$b%`"'])
        self.assertIn('"/path with spaces/tool"',result)
        self.assertIn('\\$',result)
        self.assertIn('%%',result)
        self.assertIn('\\`',result)

    def test_conflicting_shortcut_is_not_stolen(self):
        calls=[]
        def fake_accel(method,*args):
            calls.append((method,args))
            if method=='action':return "(['unrelated', 'launch', 'Other', 'Launch'],)"
            return '()'
        with patch.object(p,'SHORTCUTS',[('kwin','Overview',[p.META|p.TAB])]), patch.object(p,'accel',side_effect=fake_accel):
            p.set_shortcuts()
        assignments=[args for method,args in calls if method=='setForeignShortcutKeys']
        self.assertTrue(all(args[1]=='[]' for args in assignments))

    def test_unassigned_shortcut_variant_is_accepted(self):
        calls=[]
        def fake(method,*args):
            calls.append((method,args))
            return '(@as [],)' if method=='action' else '()'
        with patch.object(p,'SHORTCUTS',[('kwin','Overview',[p.META|p.TAB])]), patch.object(p,'accel',side_effect=fake):
            p.set_shortcuts()
        self.assertIn(('setForeignShortcutKeys',(p.action('kwin','Overview'),'[([285212673, 0, 0, 0],)]')),calls)

    def test_panel_order_is_persisted_only_while_shell_is_stopped(self):
        calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'state'
            def record(*args,**kwargs):calls.append(args);return ''
            with patch.object(p.sys,'argv',['profile.py','--no-icons','--style','breeze']), \
                 patch.object(p,'STATE',state),patch.object(p,'prerequisites'), \
                 patch.object(p,'backup',return_value=Path(tmp)/'backup'),patch.object(p,'install_menu'), \
                 patch.object(p,'install_theme'),patch.object(p,'write_config'),patch.object(p,'set_shortcuts'), \
                 patch.object(p,'install_decoration'), \
                 patch.object(p,'apply_panel',return_value={'id':3,'order':'28;6;8;23;24'}), \
                 patch.object(p,'run',side_effect=record), \
                 patch.object(p,'stop_plasma',side_effect=lambda:calls.append(('stop',))), \
                 patch.object(p,'start_plasma',side_effect=lambda:calls.append(('start',))):
                p.main()
        order_call=next(i for i,args in enumerate(calls) if 'AppletOrder' in args)
        self.assertLess(calls.index(('stop',)),order_call)
        self.assertLess(order_call,calls.index(('start',)))
        self.assertEqual(calls[order_call][-1],'28;6;8;23;24')


class DecorationTests(unittest.TestCase):
    def test_decoration_is_installed_under_its_own_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            written={}
            with patch.object(p,'DATA',Path(tmp)), \
                 patch.object(p,'write_config',side_effect=lambda f,g,k,v:written.__setitem__((f,g,k),v)):
                p.install_decoration(dark=True)
            for variant in ['dark','light']:
                theme=Path(tmp)/'aurorae/themes'/('KDEWindowsWin11-'+variant)
                self.assertTrue((theme/('KDEWindowsWin11-'+variant+'rc')).is_file())
                self.assertIn('Name=KDEWindowsWin11-'+variant,(theme/'metadata.desktop').read_text())
            self.assertEqual(written[('kwinrc','org.kde.kdecoration2','theme')],'__aurorae__svg__KDEWindowsWin11-dark')
            self.assertEqual(written[('kwinrc','org.kde.kdecoration2','library')],'org.kde.kwin.aurorae')

    def test_old_backups_do_not_touch_breezerc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); config=root/'config'; config.mkdir(); backup=root/'backup'; backup.mkdir()
            (config/'breezerc').write_text('[Style]\nMenuOpacity=60\n')
            (backup/'manifest.json').write_text(json.dumps({'owned':[],'shortcuts':[]}))
            with patch.object(p,'CONFIG',config),patch.object(p,'OWNED',[]),patch.object(p,'stop_plasma'), \
                 patch.object(p,'start_plasma'),patch.object(p,'set_shortcuts'),patch.object(p,'run'),patch.object(p,'install_menu'):
                p.restore(backup)
            self.assertTrue((config/'breezerc').exists())


class QuickSettingsTests(unittest.TestCase):
    def test_quick_settings_widget_is_installed_with_runnable_status_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(p,'DATA',Path(tmp)):
                p.install_quicksettings()
            target=Path(tmp)/'plasma/plasmoids'/p.QUICK_SETTINGS
            meta=json.loads((target/'metadata.json').read_text())
            self.assertEqual(meta['KPlugin']['Id'],p.QUICK_SETTINGS)
            self.assertTrue(os.access(target/'contents/code/status.sh',os.X_OK))
            self.assertIn(p.QUICK_SETTINGS,[path.name for path in p.OWNED])
