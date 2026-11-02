# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import sys

# Resolve Windows/Qt dependencies without unrelated tools on the shell PATH.
# In particular, Poppler's icuuc.dll has versioned exports incompatible with
# the Windows ICU API used by Qt, but can shadow the OS DLL during analysis.
windows_dir = Path(os.environ.get('SystemRoot', r'C:\Windows'))
os.environ['PATH'] = os.pathsep.join((
    str(Path(sys.executable).parent),
    str(windows_dir / 'System32'),
    str(windows_dir),
))

# Resolve inputs relative to this spec, even when built from another directory.
project_dir = Path(SPECPATH)
icon_path = project_dir / 'app_icon.ico'
datas = [(str(icon_path), '.'), (str(project_dir / 'assets'), 'assets')]
sample_media = project_dir / 'sample_media'
if sample_media.is_dir():
    datas.append((str(sample_media), 'sample_media'))

a = Analysis(
    [str(project_dir / 'main.py')],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Passing binaries and data directly to EXE creates one file; no COLLECT step.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DualScreenPresenter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)
