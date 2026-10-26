"""Bundle and run DoorOS-Dolphin separately from the distribution's Dolphin."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')
STATE=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'kde-windows-style'
SOURCE_REF='a5b4f9186ed146f1e7804fada86cde8277a0df97'
SOURCE_SHA='833608dc001aab5a5a47cd9fa6c3a303436fb45ccc43bbcd850e2573106bbab1'
DESKTOP='kde-windows-style-dooros.desktop'
# Windows 11 Explorer look for the integrated window, applied on top of SOURCE_REF.
PATCH=ROOT/'vendor/dooros-dolphin-windows11.patch'


def binary():return ROOT/'vendor/dooros-dolphin/usr/bin/dolphin'


def installed():return binary().is_file() and os.access(binary(),os.X_OK)


def build(install_deps=False):
    if install_deps:
        subprocess.run(['pkexec','--disable-internal-agent','/usr/bin/python3','-I',str(ROOT/'build-deps.py')],check=True)
    source_archive=ROOT/'vendor/dooros-dolphin-source.tar.gz'
    if not source_archive.exists() or hashlib.sha256(source_archive.read_bytes()).hexdigest()!=SOURCE_SHA:
        raise RuntimeError('Fontes DoorOS-Dolphin ausentes ou com checksum inválido. Use o pacote completo.')
    work=STATE/'build-dooros'
    source=work/'source'
    work.mkdir(parents=True,exist_ok=True)
    patch=hashlib.sha256(PATCH.read_bytes()).hexdigest()
    marker=source/'.kde-windows-style-patch'
    if (source/'CMakeLists.txt').exists() and (not marker.is_file() or marker.read_text()!=patch):
        shutil.rmtree(source)
    if not (source/'CMakeLists.txt').exists():
        source.mkdir(exist_ok=True)
        with tarfile.open(source_archive) as tar:
            tar.extractall(work/'extract',filter='data')
        roots=[p for p in (work/'extract').iterdir() if p.is_dir()]
        if len(roots)!=1:raise RuntimeError('Estrutura inesperada nos fontes DoorOS.')
        shutil.copytree(roots[0],source,dirs_exist_ok=True)
        shutil.rmtree(work/'extract')
        subprocess.run(['patch','-p1','--forward','--batch','-d',str(source),'-i',str(PATCH)],check=True)
        marker.write_text(patch)
    commands=[
        ['cmake','-S',str(source),'-B',str(work/'build'),'-G','Ninja',
         '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_INSTALL_PREFIX=/usr','-DBUILD_TESTING=OFF',
         '-DCMAKE_DISABLE_FIND_PACKAGE_PackageKitQt6=ON','-DCMAKE_DISABLE_FIND_PACKAGE_KF6Baloo=ON',
         '-DCMAKE_DISABLE_FIND_PACKAGE_KF6BalooWidgets=ON','-DCMAKE_DISABLE_FIND_PACKAGE_KF6UserFeedback=ON',
         '-DCMAKE_INSTALL_RPATH=$ORIGIN/../lib:$ORIGIN/../lib/x86_64-linux-gnu'],
        ['cmake','--build',str(work/'build'),'--parallel','2'],
    ]
    for command in commands:
        print('Executando:', ' '.join(command),flush=True)
        subprocess.run(command,check=True)
    stage=work/'stage'
    if stage.exists():shutil.rmtree(stage)
    subprocess.run(['cmake','--install',str(work/'build')],env=dict(os.environ,DESTDIR=str(stage)),check=True)
    target=ROOT/'vendor/dooros-dolphin'
    previous=target.with_name('dooros-dolphin.previous')
    if previous.exists():shutil.rmtree(previous)
    if target.exists():target.rename(previous)
    try:
        shutil.move(str(stage),str(target))
        # Do not export the upstream Dolphin D-Bus activation service to the system.
        services=target/'usr/share/dbus-1/services'
        if services.exists():shutil.rmtree(services)
        subprocess.run(['strip','--strip-unneeded',str(binary())],check=False)
    except BaseException:
        if target.exists():shutil.rmtree(target)
        if previous.exists():previous.rename(target)
        raise
    if previous.exists():shutil.rmtree(previous)
    (target/'BUILD.json').write_text(json.dumps({'source':SOURCE_REF,'patch':PATCH.name,'platform':'Ubuntu 26.04 x86_64','baloo_information_panel':False},indent=2))
    print('DoorOS-Dolphin compilado separadamente, sem substituir o Dolphin do sistema.',flush=True)


def install():
    if not installed():build(install_deps=True)
    import profile as style
    apps=DATA/'applications';apps.mkdir(parents=True,exist_ok=True)
    entry=(f'[Desktop Entry]\nType=Application\nName=DoorOS-Dolphin\nGenericName=Gerenciador de arquivos\n'
           f'Exec={style.desktop_exec([ROOT/"dooros-launch.sh"])} %U\nIcon=system-file-manager\n'
           'Terminal=false\nCategories=System;FileTools;FileManager;\nMimeType=inode/directory;\n')
    (apps/DESKTOP).write_text(entry)
    if shutil.which('update-desktop-database'):subprocess.run(['update-desktop-database',str(apps)],check=True)
    print('DoorOS-Dolphin disponível no menu de aplicativos.',flush=True)


def open_window(paths):
    if not installed():raise RuntimeError('DoorOS-Dolphin ainda não foi preparado.')
    prefix=binary().parents[1]
    env=dict(os.environ)
    env['XDG_DATA_DIRS']=str(prefix/'share')+':'+env.get('XDG_DATA_DIRS','/usr/local/share:/usr/share')
    env['LD_LIBRARY_PATH']=':'.join(str(prefix/p) for p in ['lib/x86_64-linux-gnu','lib64','lib'])+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    for key in ['QT_PLUGIN_PATH','QT_QPA_PLATFORMTHEME','QT_STYLE_OVERRIDE']:env.pop(key,None)
    os.execve(str(binary()),[str(binary()),'--new-window',*paths],env)


def set_default(restore=False):
    import profile as style
    STATE.mkdir(parents=True,exist_ok=True)
    saved=STATE/'dolphin-default.json'
    if restore:
        if not saved.exists():raise RuntimeError('Não há troca de gerenciador padrão registrada.')
        original=json.loads(saved.read_text())
        subprocess.run(['xdg-mime','default',original['desktop'],'inode/directory'],check=True)
        for entry in original['shortcuts']:style.accel('setForeignShortcutKeys',entry['id'],entry['keys'])
        print('Gerenciador de arquivos anterior restaurado.')
        return
    install()
    ids=[style.action('org.kde.dolphin.desktop','_launch'),style.action(DESKTOP,'_launch')]
    if not saved.exists():
        old=subprocess.check_output(['xdg-mime','query','default','inode/directory'],text=True).strip() or 'org.kde.dolphin.desktop'
        saved.write_text(json.dumps({'desktop':old,'shortcuts':[{'id':id,'keys':style.variant_argument(style.accel('shortcutKeys',id))} for id in ids]},indent=2))
    subprocess.run(['xdg-mime','default',DESKTOP,'inode/directory'],check=True)
    style.accel('setForeignShortcutKeys',ids[0],'[]')
    style.accel('doRegister',ids[1])
    style.accel('setForeignShortcutKeys',ids[1],'[([268435525, 0, 0, 0],)]')
    print('DoorOS-Dolphin definido como padrão para pastas e Win+E.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',action='store_true');parser.add_argument('--install-deps',action='store_true')
    parser.add_argument('--install',action='store_true');parser.add_argument('--default',action='store_true')
    parser.add_argument('--restore-default',action='store_true');parser.add_argument('--open',action='store_true')
    parser.add_argument('paths',nargs='*');args=parser.parse_args()
    try:
        if args.build:build(args.install_deps)
        elif args.default:set_default()
        elif args.restore_default:set_default(True)
        elif args.open:open_window(args.paths)
        else:install()
    except (RuntimeError,OSError,subprocess.SubprocessError) as exc:
        print('Erro:',exc,file=sys.stderr);sys.exit(1)
