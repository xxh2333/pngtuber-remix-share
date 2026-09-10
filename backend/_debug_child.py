# -*- coding: utf-8 -*-
"""搜索 sprite 块中的 children/child_count/parent 等字段，找树结构编码"""
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

pos = data.find(b'sprites_array')
sr = data[pos:spans[0][0]]
z_pos = [m.start() for m in re.finditer(re.escape(b'z_index'), sr)]

# 搜索所有 sprite 块中的 "child" / "parent" / "count" / "depth" 相关字段
search_terms = [b'child', b'parent', b'depth', b'count', b'sibling', b'tree', b'nested', b'level', b'sprite_name', b'state_name']

for i, zp in enumerate(z_pos):
    blk_end = z_pos[i+1] if i+1 < len(z_pos) else len(sr)
    blk = sr[zp:blk_end]
    
    found = {}
    for term in search_terms:
        p = 0
        while True:
            idx = blk.find(term, p)
            if idx < 0: break
            # 看这个位置前后的内容
            context = blk[max(0,idx-4):idx+30]
            found[term.decode()] = context.hex()
            p = idx + 1
    
    z = struct.unpack('<f', blk[12:16])[0]
    print(f"Sprite [{i}] z={z:.0f} len={len(blk)}")
    for k, v in found.items():
        print(f"  {k}: {v}")
    print()
