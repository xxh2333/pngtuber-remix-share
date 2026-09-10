# -*- coding: utf-8 -*-
"""全面检查 .pngRemix 的元数据字段和 sprite 位置信息"""
import io, re, struct
from PIL import Image

fpath = r"d:\github projects\pngtuber remix share\.trae\specs\pngtuber-remix-share\小一桌宠by無锁言.pngRemix"
with open(fpath, 'rb') as f:
    data = f.read()

PNG_SIG = b'\x89PNG\r\n\x1a\n'
IEND = b'IEND\xaeB\x60\x82'

spans = []
s = 0
while True:
    p = data.find(PNG_SIG, s)
    if p == -1: break
    e = data.find(IEND, p)
    if e == -1: break
    spans.append((p, e + 8))
    s = e + 8

print(f"=== {len(spans)} 张 PNG ===\n")

# 检查每张 PNG 的完整元数据字段
field_names = [b'image_name', b'trimmed', b'offset', b'id', b'pivot', b'position',
               b'local_pos', b'localPosition', b'rect', b'sprite', b'x', b'y',
               b'width', b'height', b'texture']

for ri, (st, en) in enumerate(spans):
    img = Image.open(io.BytesIO(data[st:en])).convert('RGBA')
    meta = data[max(0, st-600):st]
    
    print(f"--- Resource [{ri}] PNG@{st} size={img.size} ---")
    
    # 找所有已知字段
    for fn in field_names:
        pos = 0
        while True:
            p = meta.find(fn, pos)
            if p < 0: break
            # 打印周围 40 字节
            chunk = meta[p:p+40]
            print(f"  [{fn.decode()}] @{p}: {chunk.hex()}")
            pos = p + 1
    
    # 也搜索未知的字段名（15 00 00 00 + len + name 模式）
    print("  --- all string fields ---")
    for m in re.finditer(b'\x15\x00\x00\x00', meta):
        mp = m.start()
        if mp + 8 > len(meta): continue
        slen = int.from_bytes(meta[mp+4:mp+8], 'little')
        if 0 < slen < 40:
            raw_name = meta[mp+8:mp+8+slen]
            try:
                fname = raw_name.decode('ascii')
                # 看后面的值
            except:
                continue
            val_start = mp + 8 + slen
            # align to 4
            val_start_aligned = (val_start + 3) & ~3
            if val_start_aligned + 20 <= len(meta):
                tail = meta[val_start_aligned:val_start_aligned+20]
                print(f"  field '{fname}' @{mp}: tail={tail.hex()}")
    
    print()
