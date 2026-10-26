#!/usr/bin/python3
"""Optional Ubuntu/Debian dependencies for rebuilding DoorOS-Dolphin."""
import os,subprocess
PACKAGES = ['build-essential', 'cmake', 'ninja-build', 'extra-cmake-modules', 'qt6-base-dev', 'qt6-base-private-dev', 'qt6-tools-dev', 'qt6-tools-dev-tools', 'qt6-l10n-tools', 'libkf6kcmutils-dev', 'libkf6newstuff-dev', 'libkf6coreaddons-dev', 'libkf6i18n-dev', 'libkf6dbusaddons-dev', 'libkf6bookmarks-dev', 'libkf6config-dev', 'libkf6kio-dev', 'libkf6parts-dev', 'libkf6solid-dev', 'libkf6iconthemes-dev', 'libkf6completion-dev', 'libkf6textwidgets-dev', 'libkf6notifications-dev', 'libkf6crash-dev', 'libkf6windowsystem-dev', 'libkf6widgetsaddons-dev', 'libkf6codecs-dev', 'libkf6guiaddons-dev', 'libkf6colorscheme-dev', 'libkf6filemetadata-dev', 'libkf6xmlgui-dev', 'libkf6configwidgets-dev']
if os.geteuid()!=0:
    raise SystemExit('Execute com pkexec ou sudo para instalar as dependências de compilação.')
raise SystemExit(subprocess.run(['apt-get','-y','--no-remove','--no-install-recommends','install',*PACKAGES],env=dict(os.environ,DEBIAN_FRONTEND='noninteractive')).returncode)
