# -*- coding: utf-8 -*-
"""生成不同合成方式的对比预览"""
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

# 解析资源
resources = []
for ri, (st, en) in enumerate(spans):
    img = Image.open(io.BytesIO(data[st:en])).convert('RGBA')
    meta = data[max(0, st-300):st]
    ox = oy = 0.0
    op = meta.rfind(b'offset')
    if op >= 0:
        ox = struct.unpack('<f', meta[op+12:op+16])[0]
        oy = struct.unpack('<f', meta[op+16:op+20])[0]
    name = ""
    npos = meta.rfind(b'image_name')
    if npos >= 0:
        tail = meta[npos+10:npos+10+200]
        tpos = tail.find(b'\x04\x00\x00\x00')
        if tpos >= 0:
            slen = int.from_bytes(tail[tpos+4:tpos+8], 'little')
            if 0 < slen < 80:
                raw = tail[tpos+8:tpos+8+slen]
                for enc in ('utf-8','gbk'):
                    try: name = raw.decode(enc); break
                    except: pass
    win_start = spans[ri-1][0] if ri > 0 else max(0, st-400)
    win = data[win_start:st]
    h = None
    idm = win.rfind(b'\x69\x64\x00\x00')
    if idm >= 0:
        cand = win[idm+8:idm+12]
        if cand != b'\x00\x00\x00\x00':
            h = cand.hex()
    resources.append({'img': img, 'x': ox, 'y': oy, 'hash': h, 'name': name, 'ri': ri})

by_hash = {r['hash']: r for r in resources if r['hash']}

# 解析 sprites
pos = data.find(b'sprites_array')
sr = data[pos:spans[0][0]]
z_pos = [m.start() for m in re.finditer(re.escape(b'z_index'), sr)]

def read_field_raw(blk, fname):
    fp = 0
    while True:
        p = blk.find(fname.encode(), fp)
        if p < 0: return None
        val_start = p + len(fname)
        val_start_aligned = (val_start + 3) & ~3
        if val_start_aligned + 8 <= len(blk):
            type_code = int.from_bytes(blk[val_start_aligned:val_start_aligned+4], 'little')
            if type_code == 5 and val_start_aligned + 12 <= len(blk):
                vx = struct.unpack('<f', blk[val_start_aligned+4:val_start_aligned+8])[0]
                vy = struct.unpack('<f', blk[val_start_aligned+8:val_start_aligned+12])[0]
                return (vx, vy)
            elif type_code == 1:
                return int.from_bytes(blk[val_start_aligned+4:val_start_aligned+8], 'little')
        fp = p + 1

sprites = []
for i, zp in enumerate(z_pos):
    blk_end = z_pos[i+1] if i+1 < len(z_pos) else len(sr)
    blk = sr[zp:blk_end]
    z = struct.unpack('<f', blk[12:16])[0]
    sp_pos = read_field_raw(blk, 'position')
    sp_off = read_field_raw(blk, 'offset')
    folder = read_field_raw(blk, 'folder')
    oe = read_field_raw(blk, 'open_eyes')
    om = read_field_raw(blk, 'open_mouth')
    iid = blk.find(b'image_id')
    img_id = None
    if iid >= 0:
        cand_start = iid + 8 + 4
        if cand_start + 4 <= len(blk):
            cand = blk[cand_start:cand_start+4]
            if cand != b'\x00\x00\x00\x00':
                img_id = cand.hex()
    sprites.append({'idx': i, 'z': z, 'pos': sp_pos, 'off': sp_off,
                    'folder': folder, 'oe': oe, 'om': om, 'hash': img_id})

# 确定树结构：通过 parent_id 反推
# 用试探法：对每个 sprite，找哪个 parent 使得 parent_abs + pos + off = resource_offset
def find_parent(si):
    """找 sprite si 的父节点：使得 parent_abs + pos + off ≈ resource_offset"""
    sp = sprites[si]
    if not sp['pos'] or not sp['off'] or not sp['hash'] or sp['hash'] not in by_hash:
        return None
    r = by_hash[sp['hash']]
    target_x, target_y = r['x'], r['y']
    px, py = sp['pos']
    ox, oy = sp['off']
    needed_parent_x = target_x - px - ox
    needed_parent_y = target_y - py - oy
    # 在所有 sprite 中找 abs_pos ≈ (needed_parent_x, needed_parent_y) 的
    for pi in range(si):
        psp = sprites[pi]
        if not psp['pos'] or not psp['off']:
            continue
        # parent 的 abs = parent's resource offset (if it has a hash)
        if psp['hash'] and psp['hash'] in by_hash:
            pr = by_hash[psp['hash']]
            if abs(pr['x'] - needed_parent_x) < 1 and abs(pr['y'] - needed_parent_y) < 1:
                return pi
        elif psp['folder'] == 1:
            # folder 的 abs = (0, 0)
            if abs(needed_parent_x) < 1 and abs(needed_parent_y) < 1:
                return pi
    return None

# 构建树
for i in range(len(sprites)):
    parent = find_parent(i)
    sprites[i]['parent'] = parent

print("Tree structure:")
for i, sp in enumerate(sprites):
    parent_str = str(sp['parent']) if sp['parent'] is not None else "None"
    print(f"  [{i}] parent={parent_str} z={sp['z']:.0f} folder={sp['folder']} hash={sp['hash']} oe={sp['oe']} om={sp['om']}")

# 方式1：当前代码（resource offset 作为左上角，z=0 按 idx 排序）
def render_v1():
    cut = 10  # first state cut
    layers = []
    for j in range(cut):
        r = resources[j]
        layers.append({'img': r['img'], 'x': r['x'], 'y': r['y'], 'z': 0.0, 'idx': j})
    layers.sort(key=lambda s: (s['z'], s['idx']))
    return compose(layers)

# 方式2：resource offset 作为中心，减去半宽半高
def render_v2():
    cut = 10
    layers = []
    for j in range(cut):
        r = resources[j]
        cx, cy = r['x'], r['y']
        tx = cx - r['img'].width / 2
        ty = cy - r['img'].height / 2
        layers.append({'img': r['img'], 'x': tx, 'y': ty, 'z': 0.0, 'idx': j})
    layers.sort(key=lambda s: (s['z'], s['idx']))
    return compose(layers)

# 方式3：resource offset 作为中心，y 翻转
def render_v3():
    cut = 10
    layers = []
    for j in range(cut):
        r = resources[j]
        cx = r['x'] - r['img'].width / 2
        cy = -r['y'] - r['img'].height / 2  # y flip
        layers.append({'img': r['img'], 'x': cx, 'y': cy, 'z': 0.0, 'idx': j})
    layers.sort(key=lambda s: (s['z'], s['idx']))
    return compose(layers)

# 方式4：用 sprite 树 + z_index，排除 oe=0/om=1
def render_v4():
    layers = []
    for sp in sprites:
        if sp['folder'] == 1:
            continue
        if not sp['hash'] or sp['hash'] not in by_hash:
            continue
        if sp['om'] == 1 or sp['oe'] == 0:
            continue
        r = by_hash[sp['hash']]
        # 用 resource offset 作为中心，y 翻转
        cx = r['x'] - r['img'].width / 2
        cy = -r['y'] - r['img'].height / 2
        layers.append({'img': r['img'], 'x': cx, 'y': cy, 'z': sp['z'], 'idx': sp['idx']})
    layers.sort(key=lambda s: (s['z'], s['idx']))
    return compose(layers)

# 方式5：用 sprite 树 + z_index，resource offset 作为左上角（当前逻辑但用 sprite z 排序）
def render_v5():
    layers = []
    for sp in sprites:
        if sp['folder'] == 1:
            continue
        if not sp['hash'] or sp['hash'] not in by_hash:
            continue
        if sp['om'] == 1 or sp['oe'] == 0:
            continue
        r = by_hash[sp['hash']]
        layers.append({'img': r['img'], 'x': r['x'], 'y': r['y'], 'z': sp['z'], 'idx': sp['idx']})
    layers.sort(key=lambda s: (s['z'], s['idx']))
    return compose(layers)

def compose(layers):
    if not layers:
        return Image.new('RGBA', (1, 1))
    coords = [(l['x'], l['y'], l['x'] + l['img'].width, l['y'] + l['img'].height) for l in layers]
    min_x = min(c[0] for c in coords)
    min_y = min(c[1] for c in coords)
    max_x = max(c[2] for c in coords)
    max_y = max(c[3] for c in coords)
    w = int(max_x - min_x) + 1
    h = int(max_y - min_y) + 1
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for l in layers:
        canvas.alpha_composite(l['img'], (int(l['x'] - min_x), int(l['y'] - min_y)))
    if w > 300:
        ratio = 300 / w
        canvas = canvas.resize((300, max(1, int(h * ratio))), Image.LANCZOS)
    return canvas

outdir = r"d:\github projects\pngtuber remix share\backend\media\_test"
import os
os.makedirs(outdir, exist_ok=True)

for name, fn in [("v1_current_topleft", render_v1),
                  ("v2_center", render_v2),
                  ("v3_center_yflip", render_v3),
                  ("v4_sprite_z_center_yflip", render_v4),
                  ("v5_sprite_z_topleft", render_v5)]:
    img = fn()
    out = os.path.join(outdir, f"compare_{name}.png")
    img.save(out)
    print(f"{name}: {img.size} -> {out}")
