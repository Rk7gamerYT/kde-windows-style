"""Pinned community assets, verified before extraction or execution."""
import hashlib
import os
from pathlib import Path
import subprocess

ASSETS = {
    'win11-icons': ('yeyushengfan258/Win11-icon-theme','a5b460a407da143b32f19a503d7fcebb3edf2371','358479b3113a96604eecf6a94ee099f72e8d46431242c7766c80c51db8bc981a'),
    'win11-plasma': ('yeyushengfan258/Win11OS-kde','9f021c3e71da7baf59a0614ab858d53b1e455fd5','6b463a31acbee8023a51dc79b74c4284b0969a3165445cf73b1ad590c8767d40'),
}


def archive(name):
    repo,ref,digest=ASSETS[name]
    cache=Path(os.environ.get('XDG_CACHE_HOME') or Path.home()/'.cache')/'kde-windows-style'
    cache.mkdir(parents=True,exist_ok=True)
    bundled=Path(__file__).resolve().parent/'vendor'/(name+'.tar.gz')
    if bundled.is_file():
        if hashlib.sha256(bundled.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Arquivo incluso corrompido: '+name)
        return bundled
    path=cache/(name+'-'+ref+'.tar.gz')
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        temporary=path.with_suffix('.download')
        subprocess.run(['curl','-fL','--retry','3','-o',str(temporary),f'https://github.com/{repo}/archive/{ref}.tar.gz'],check=True)
        if hashlib.sha256(temporary.read_bytes()).hexdigest()!=digest:
            temporary.unlink(missing_ok=True)
            raise RuntimeError('Checksum inválido para '+name)
        temporary.replace(path)
    return path
