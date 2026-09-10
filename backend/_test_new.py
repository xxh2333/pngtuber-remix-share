# -*- coding: utf-8 -*-
"""用新代码生成预览对比"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pngtuber_share.settings')

from works.pngremix import render_pngremix_preview

files = [
    r"d:\github projects\pngtuber remix share\.trae\specs\pngtuber-remix-share\小一桌宠by無锁言.pngRemix",
    r"D:\桌宠\srx之子.pngRemix",
]

outdir = r"d:\github projects\pngtuber remix share\backend\media\_test"
os.makedirs(outdir, exist_ok=True)

for fpath in files:
    if not os.path.exists(fpath):
        print(f"SKIP (not found): {fpath}")
        continue
    with open(fpath, 'rb') as f:
        data = f.read()
    img = render_pngremix_preview(data)
    name = os.path.basename(fpath).replace('.pngRemix', '')
    out = os.path.join(outdir, f"new_{name}.png")
    img.save(out)
    print(f"{name}: {img.size} -> {out}")
