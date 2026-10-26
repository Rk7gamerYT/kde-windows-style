"""Unpack the included Qt/Python wheels without pip, venv, root, or network."""
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent


def setup():
    if sys.version_info < (3,12):raise RuntimeError('O pacote requer Python 3.12 ou mais recente.')
    source=ROOT/'vendor/wheels'
    manifest=json.loads((source/'SHA256SUMS.json').read_text())
    signature=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    target=ROOT/'.runtime'
    with (ROOT/'.runtime.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        marker=target/'bundle-version'
        if marker.is_file() and marker.read_text()==signature:return
        if target.is_symlink():raise RuntimeError('O caminho do runtime é um link simbólico.')
        with tempfile.TemporaryDirectory(dir=ROOT,prefix='.runtime-build-') as temp:
            for name,digest in manifest.items():
                if Path(name).name!=name:raise RuntimeError('Nome inválido no manifesto de dependências.')
                wheel=source/name
                if hashlib.sha256(wheel.read_bytes()).hexdigest()!=digest:
                    raise RuntimeError('Dependência inclusa corrompida: '+name)
                with zipfile.ZipFile(wheel) as archive:
                    for entry in archive.namelist():
                        if Path(entry).is_absolute() or '..' in Path(entry).parts:raise RuntimeError('Caminho inseguro no wheel.')
                    archive.extractall(temp)
            (Path(temp)/'bundle-version').write_text(signature)
            if target.exists():shutil.rmtree(target)
            shutil.move(temp,target)


if __name__=='__main__':
    try:setup()
    except (OSError,ValueError,RuntimeError,zipfile.BadZipFile) as exc:
        print('Erro ao preparar dependências inclusas:',exc,file=sys.stderr);sys.exit(1)
