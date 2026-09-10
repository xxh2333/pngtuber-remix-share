# -*- coding: utf-8 -*-
"""检查 .pngRemix 文件中 offset 字段的真实字节布局"""
import struct

fpath = r"d:\github projects\pngtuber remix share\.trae\specs\pngtuber-remix-share\小一桌宠by無锁言.pngRemix"
with open(fpath, 'rb') as f:
    data = f.read()

PNG_SIG = b'\x89PNG\r\n\x1a\n'
IEND = b'IEND\xaeB\x60\x82'

# 找所有 PNG
spans = []
s = 0
while True:
    p = data.find(PNG_SIG, s)
    if p == -1:
        break
    e = data.find(IEND, p)
    if e == -1:
        break
    spans.append((p, e + 8))
    s = e + 8

print(f"共 {len(spans)} 张 PNG\n")

# 检查每张 PNG 前的 offset 字段
for ri, (st, en) in enumerate(spans):
    # 取 PNG 前 500 字节
    meta = data[max(0, st - 500):st]
    op = meta.rfind(b'offset')
    if op < 0:
        print(f"[{ri}] no offset found, meta tail: {meta[-50:].hex()}")
        continue

    # 打印 offset 周围的完整字节
    start = max(0, op - 20)
    chunk = meta[start:op + 40]
    print(f"[{ri}] PNG@{st}, offset@meta[{op}] (abs {st - len(meta) + op})")
    print(f"    bytes around offset:")
    for i in range(0, len(chunk), 4):
        abs_pos = start + i
        raw = chunk[i:i+4]
        fval = struct.unpack('<f', raw)[0] if len(raw) == 4 else 0
        ival = int.from_bytes(raw, 'little', signed=True) if len(raw) == 4 else 0
        label = ""
        if abs_pos == op - start:
            label = " <-- offset starts"
        elif abs_pos == op - start + 6:
            label = " <-- +6 (type?)"
        elif abs_pos == op - start + 10:
            label = " <-- +10"
        elif abs_pos == op - start + 12:
            label = " <-- +12 (current x)"
        elif abs_pos == op - start + 16:
            label = " <-- +16 (current y)"
        print(f"    [{abs_pos:3d}] {raw.hex():8s}  float={fval:12.2f}  int={ival:12d}{label}")
    
    # 也检查 image_name
    npos = meta.rfind(b'image_name')
    if npos >= 0:
        # 打印 image_name 后面的内容
        tail = meta[npos:npos + 60]
        print(f"    image_name@meta[{npos}]: {tail[:30].hex()}")
        # 找字符串类型码
        tpos = tail[10:30].find(b'\x04\x00\x00\x00')
        if tpos >= 0:
            slen = int.from_bytes(tail[10+tpos+4:10+tpos+8], 'little')
            if 0 < slen < 80:
                raw = tail[10+tpos+8:10+tpos+8+slen]
                for enc in ('utf-8', 'gbk'):
                    try:
                        print(f"    name: {raw.decode(enc)}")
                        break
                    except:
                        pass
    print()
