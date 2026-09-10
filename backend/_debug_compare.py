# -*- coding: utf-8 -*-
"""对比 sprite position+offset 与 resource-side offset"""
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

# 解析资源侧 offset 和 hash
resources = []
for ri, (st, en) in enumerate(spans):
    img = Image.open(io.BytesIO(data[st:en])).convert('RGBA')
    meta = data[max(0, st-300):st]
    ox = oy = 0.0
    op = meta.rfind(b'offset')
    if op >= 0:
        ox = struct.unpack('<f', meta[op+12:op+16])[0]
        oy = struct.unpack('<f', meta[op+16:op+20])[0]
    # hash
    win_start = spans[ri-1][0] if ri > 0 else max(0, st-400)
    win = data[win_start:st]
    h = None
    idm = win.rfind(b'\x69\x64\x00\x00')
    if idm >= 0:
        cand = win[idm+8:idm+12]
        if cand != b'\x00\x00\x00\x00':
            h = cand.hex()
    resources.append({'img': img, 'x': ox, 'y': oy, 'hash': h, 'ri': ri})

by_hash = {r['hash']: r for r in resources if r['hash']}

# 解析 sprite 数据
pos = data.find(b'sprites_array')
sr = data[pos:spans[0][0]]
z_pos = [m.start() for m in re.finditer(re.escape(b'z_index'), sr)]

def read_field_raw(blk, fname):
    fp = 0
    while True:
        p = blk.find(fname.encode(), fp)
        if p < 0:
            return None
        val_start = p + len(fname)
        val_start_aligned = (val_start + 3) & ~3
        if val_start_aligned + 8 <= len(blk):
            type_code = int.from_bytes(blk[val_start_aligned:val_start_aligned+4], 'little')
            if type_code == 5 and val_start_aligned + 12 <= len(blk):
                vx = struct.unpack('<f', blk[val_start_aligned+4:val_start_aligned+8])[0]
                vy = struct.unpack('<f', blk[val_start_aligned+8:val_start_aligned+12])[0]
                return (vx, vy)
            elif type_code == 1:
                v = int.from_bytes(blk[val_start_aligned+4:val_start_aligned+8], 'little')
                return v
        fp = p + 1

# 构建树结构：folder=true 的 sprite 包含后续 leaves 直到下一个 folder
# 但需要追踪嵌套
print("sprite | z  | position         | offset           | pos+off         | res_offset      | diff            | match")
print("-------|----|------------------|------------------|-----------------|-----------------|-----------------|------")

for i, zp in enumerate(z_pos):
    blk_end = z_pos[i+1] if i+1 < len(z_pos) else len(sr)
    blk = sr[zp:blk_end]
    
    z = struct.unpack('<f', blk[12:16])[0]
    sprite_pos = read_field_raw(blk, 'position')
    sprite_off = read_field_raw(blk, 'offset')
    folder = read_field_raw(blk, 'folder')
    
    # image_id
    iid = blk.find(b'image_id')
    img_id = None
    if iid >= 0:
        cand_start = iid + 8 + 4
        if cand_start + 4 <= len(blk):
            cand = blk[cand_start:cand_start+4]
            if cand != b'\x00\x00\x00\x00':
                img_id = cand.hex()
    
    if sprite_pos and sprite_off and img_id and img_id in by_hash:
        r = by_hash[img_id]
        px, py = sprite_pos
        ox, oy = sprite_off
        sum_x, sum_y = px + ox, py + oy
        rx, ry = r['x'], r['y']
        dx, dy = sum_x - rx, sum_y - ry
        match = "YES" if abs(dx) < 0.1 and abs(dy) < 0.1 else "NO"
        print(f"  {i:4d} | {z:2.0f} | ({px:8.1f},{py:8.1f}) | ({ox:8.1f},{oy:8.1f}) | ({sum_x:8.1f},{sum_y:8.1f}) | ({rx:8.1f},{ry:8.1f}) | ({dx:8.1f},{dy:8.1f}) | {match}")
    elif folder == 1:
        print(f"  {i:4d} | {z:2.0f} | FOLDER")
    else:
        pos_str = f"({sprite_pos[0]:.1f},{sprite_pos[1]:.1f})" if sprite_pos else "None"
        off_str = f"({sprite_off[0]:.1f},{sprite_off[1]:.1f})" if sprite_off else "None"
        print(f"  {i:4d} | {z:2.0f} | {pos_str:16s} | {off_str:16s} | img_id={img_id}")
