from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tray_overflow as t


def fake_call(*args):
    if 'RegisteredStatusNotifierItems' in args:
        return "(<['org.kde.StatusNotifierItem-1-1/StatusNotifierItem', ':1.9/org/ayatana/NotificationItem/steam']>,)"
    item=args[args.index('-d')+1]+args[args.index('-o')+1]
    values={'org.kde.StatusNotifierItem-1-1/StatusNotifierItem':{'Id':'discord','Category':'ApplicationStatus'},
            ':1.9/org/ayatana/NotificationItem/steam':{'Id':'steam','Category':'Hardware'}}
    return "(<'%s'>,)" % values[item][args[-1]]


class TrayOverflowTests(unittest.TestCase):
    def test_only_app_icons_are_listed(self):
        with patch.object(t,'call',side_effect=fake_call):
            self.assertEqual(t.app_icons(),['discord'])

    def test_each_app_is_hidden_only_the_first_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(t,'STATE',Path(tmp)),patch.object(t,'SEEN',Path(tmp)/'seen.json'), \
                 patch.object(t,'app_icons',return_value=['discord']),patch.object(t,'hide') as hide:
                self.assertTrue(t.sync())
                self.assertFalse(t.sync())
                hide.assert_called_once_with(['discord'])


if __name__=='__main__':
    unittest.main()
