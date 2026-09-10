# -*- coding: utf-8 -*-
"""提取所有 sprite 的 position/offset/z_index/image_id，并理解树结构"""
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

z_pos = [m.start() for m in re.finditer(re.escape(b'z_index'), sr)]

def read_field(blk, fname):
    """读取一个字段值"""
    fp = blk.find(fname.encode())
    if fp < 0:
        return None
    # 找 15 00 00 00 前缀（在字段名之前）
    # 字段名后可能对齐到 4 字节
    val_start = fp + len(fname)
    # 对齐到 4 字节
    val_start_aligned = (val_start + 3) & ~3
    if val_start_aligned + 8 > len(blk):
        return None
    type_code = int.from_bytes(blk[val_start_aligned:val_start_aligned+4], 'little')
    if type_code == 5:  # Vec2
        if val_start_aligned + 12 > len(blk):
            return None
        vx = struct.unpack('<f', blk[val_start_aligned+4:val_start_aligned+8])[0]
        vy = struct.unpack('<f', blk[val_start_aligned+8:val_start_aligned+12])[0]
        return (vx, vy)
    elif type_code == 2:  # float
        if val_start_aligned + 8 > len(blk):
            return None
        v = struct.unpack('<f', blk[val_start_aligned+4:val_start_aligned+8])[0]
        return v
    elif type_code == 1:  # bool
        if val_start_aligned + 8 > len(blk):
            return None
        v = int.from_bytes(blk[val_start_aligned+4:val_start_aligned+8], 'little')
        return v
    elif type_code == 4:  # string
        if val_start_aligned + 8 > len(blk):
            return None
        slen = int.from_bytes(blk[val_start_aligned+4:val_start_aligned+8], 'little')
        if 0 < slen < 80:
            raw = blk[val_start_aligned+8:val_start_aligned+8+slen]
            for enc in ('utf-8', 'gbk'):
                try:
                    return raw.decode(enc)
                except:
                    pass
    return None

def read_field_raw(blk, fname):
    """直接在字段名后搜索类型码，不要求 15 前缀"""
    fp = 0
    while True:
        p = blk.find(fname.encode(), fp)
        if p < 0:
            return None
        # 字段名后对齐到 4 字节
        val_start = p + len(fname)
        val_start_aligned = (val_start + 3) & ~3
        if val_start_aligned + 8 <= len(blk):
            type_code = int.from_bytes(blk[val_start_aligned:val_start_aligned+4], 'little')
            if type_code in (1, 2, 4, 5):
                if type_code == 5:
                    vx = struct.unpack('<f', blk[val_start_aligned+4:val_start_aligned+8])[0]
                    vy = struct.unpack('<f', blk[val_start_aligned+8:val_start_aligned+12])[0]
                    return (vx, vy)
                elif type_code == 2:
                    v = struct.unpack('<f', blk[val_start_aligned+4:val_start_aligned+8])[0]
                    return v
                elif type_code == 1:
                    v = int.from_bytes(blk[val_start_aligned+4:val_start_aligned+8], 'little')
                    return v
                elif type_code == 4:
                    slen = int.from_bytes(blk[val_start_aligned+4:val_start_aligned+8], 'little')
                    if 0 < slen < 80:
                        raw = blk[val_start_aligned+8:val_start_aligned+8+slen]
                        for enc in ('utf-8', 'gbk'):
                            try:
                                return raw.decode(enc)
                            except:
                                pass
        fp = p + 1

# 提取所有 sprite 信息
print("idx | z    | position         | offset           | image_id  | folder | oe | om | sprite_name")
print("----|------|------------------|------------------|-----------|--------|----|----|------------")

for i, zp in enumerate(z_pos):
    blk_end = z_pos[i + 1] if i + 1 < len(z_pos) else len(sr)
    blk = sr[zp:blk_end]
    
    z = struct.unpack('<f', blk[12:16])[0]
    pos = read_field_raw(blk, 'position')
    off = read_field_raw(blk, 'offset')
    folder = read_field_raw(blk, 'folder')
    oe = read_field_raw(blk, 'open_eyes')
    om = read_field_raw(blk, 'open_mouth')
    
    # image_id
    iid = blk.find(b'image_id')
    img_id = None
    if iid >= 0:
        # image_id 是 8 字符字段名
        cand_start = iid + 8 + 4  # 跳过字段名(8) + 类型(4)
        if cand_start + 4 <= len(blk):
            cand = blk[cand_start:cand_start+4]
            if cand != b'\x00\x00\x00\x00':
                img_id = cand.hex()
    
    # sprite_name
    sname = read_field_raw(blk, 'sprite_name')
    
    pos_str = f"({pos[0]:.1f}, {pos[1]:.1f})" if pos else "None"
    off_str = f"({off[0]:.1f}, {off[1]:.1f})" if off else "None"
    folder_str = str(folder) if folder is not None else "?"
    oe_str = str(oe) if oe is not None else "?"
    om_str = str(om) if om is not None else "?"
    id_str = img_id if img_id else "None"
    sname_str = sname if sname else "None"
    
    print(f"{i:3d} | {z:4.0f} | {pos_str:16s} | {off_str:16s} | {id_str:9s} | {folder_str:6s} | {oe_str:2s} | {om_str:2s} | {sname_str}")
