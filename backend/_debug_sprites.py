# -*- coding: utf-8 -*-
"""检查 sprites_array 中每个 sprite 块的完整字段"""
import re, struct

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

# sprites_array 区段
pos = data.find(b'sprites_array')
sr = data[pos:spans[0][0]]
print(f"sprites_array @ {pos}, length={len(sr)}\n")

# 按 z_index 切分
z_pos = [m.start() for m in re.finditer(re.escape(b'z_index'), sr)]
print(f"找到 {len(z_pos)} 个 z_index\n")

for i, zp in enumerate(z_pos):
    blk_end = z_pos[i + 1] if i + 1 < len(z_pos) else len(sr)
    blk = sr[zp:blk_end]
    
    # z_index 值
    z = struct.unpack('<f', blk[12:16])[0]
    
    # 找所有字符串字段（15 00 00 00 + len + name）
    fields = {}
    for m in re.finditer(b'\x15\x00\x00\x00', blk):
        mp = m.start()
        if mp + 8 > len(blk): continue
        slen = int.from_bytes(blk[mp+4:mp+8], 'little')
        if 0 < slen < 40:
            raw_name = blk[mp+8:mp+8+slen]
            try:
                fname = raw_name.decode('ascii')
            except:
                continue
            val_start = mp + 8 + slen
            val_start_aligned = (val_start + 3) & ~3
            if val_start_aligned + 20 <= len(blk):
                tail = blk[val_start_aligned:val_start_aligned+20]
                fields[fname] = tail.hex()
    
    # 也找非 15 开头的字段名
    all_fields = {}
    for m in re.finditer(b'\x15\x00\x00\x00', blk):
        mp = m.start()
        if mp + 8 > len(blk): continue
        slen = int.from_bytes(blk[mp+4:mp+8], 'little')
        if 0 < slen < 40:
            raw_name = blk[mp+8:mp+8+slen]
            try:
                fname = raw_name.decode('ascii')
            except:
                continue
            val_start = mp + 8 + slen
            val_start_aligned = (val_start + 3) & ~3
            if val_start_aligned + 20 <= len(blk):
                tail = blk[val_start_aligned:val_start_aligned+20]
                all_fields[fname] = tail
    
    print(f"=== Sprite [{i}] z={z} blk_len={len(blk)} ===")
    for fn, tail in all_fields.items():
        # 尝试解释值
        type_code = int.from_bytes(tail[0:4], 'little') if len(tail) >= 4 else 0
        val_desc = f"type={type_code}"
        if type_code == 5 and len(tail) >= 12:  # Vector2
            vx = struct.unpack('<f', tail[4:8])[0]
            vy = struct.unpack('<f', tail[8:12])[0]
            val_desc = f"Vec2({vx:.1f}, {vy:.1f})"
        elif type_code == 2 and len(tail) >= 8:  # float
            v = struct.unpack('<f', tail[4:8])[0]
            val_desc = f"float={v:.1f}"
        elif type_code == 1 and len(tail) >= 8:  # bool
            v = int.from_bytes(tail[4:8], 'little')
            val_desc = f"bool={v}"
        elif type_code == 4:  # string
            slen2 = int.from_bytes(tail[4:8], 'little') if len(tail) >= 8 else 0
            if 0 < slen2 < 80:
                raw = tail[8:8+slen2]
                for enc in ('utf-8', 'gbk'):
                    try:
                        val_desc = f"str={raw.decode(enc)}"
                        break
                    except:
                        pass
        print(f"  {fn}: {val_desc}  ({tail[:16].hex()})")
    
    # 也打印整个块的 hex dump 前 100 字节
    if len(blk) <= 200:
        print(f"  full hex: {blk.hex()}")
    else:
        print(f"  first 200 bytes: {blk[:200].hex()}")
    print()
