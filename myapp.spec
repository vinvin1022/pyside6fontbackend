# -*- mode: python ; coding: utf-8 -*-
#import os
#from PyInstaller.utils.hooks import collect_submodules, collect_data_files

#project_dir = os.path.abspath('.')

# 收集所有 Flask 和依赖子模块
#hiddenimports = (
#    collect_submodules('flask') +
#    collect_submodules('jinja2') +
#    collect_submodules('werkzeug') +
#    collect_submodules('click') +
#    collect_submodules('markupsafe') +
#    collect_submodules('itsdangerous') +
#    ['flask_cors', 'gunicorn', 'gunicorn.app.base', 'gunicorn.app.wsgiapp', 'gevent']
#)



a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('backend/web', 'backend/web')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='myapp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 打包时关闭upx测试
    console=False,  # 调试时建议打开控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='myapp',
)

app = BUNDLE(
    coll,
    name='myapp.app',
    icon=None,
    bundle_identifier=None,
)
