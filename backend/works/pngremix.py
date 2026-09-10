"""PNGTuber Plus .pngRemix / .pngtuber 文件解析与预览合成

二进制格式（v1.4.5 逆向）：
- 非 ZIP，文件头为二进制头部，含 version / sprites_array 等
- 内嵌多张 PNG（以标准 PNG 签名开头，IEND 结尾）
- sprites_array 区段（第一张 PNG 之前）记录每个 sprite 实例的完整属性

节点树（对应源码 spriteObject.tscn / spriteObject.gd）：
  Node2D(position) → WobbleOrigin → DragOrigin → Sprite2D(position=offset)
- 子 sprite 被 reparent 到【父节点的 Sprite2D】下（reparent_obj）
- 父 Sprite2D 的 position 即父 offset，会沿变换链传递给所有后代
- 因此纹理世界中心 = 沿父链对每个节点（含自身、含 folder）累加 (position + offset)

clip 字段（源码 set_clip_children_mode，Godot CanvasItem.ClipChildrenMode）：
- 0=禁用；1=CLIP_CHILDREN_ONLY（自身不绘制，裁剪后代）；
  2=CLIP_CHILDREN_AND_DRAW（自身绘制，后代纹理被裁剪到自身纹理 alpha 区域内）
- 裁剪对整棵后代子树生效（i15 脸、i18 窄眼为 2）

坐标系统：
- Godot 2D，y 轴向下（与 PIL 一致），不翻转 y 轴
- 合成时减去半宽半高，把中心坐标转为左上角坐标

预览合成策略（idle 常态）：
- 仅绘制 open_eyes=1（睁眼件/常驻件）且 open_mouth=0（非张嘴说话件）
- visible=0 的手动隐藏图层跳过
- 按 z_index 排序（z_as_relative=false，为全局层级）
- 后代按 clip 祖先的纹理 alpha 做遮罩裁剪
- 无 image_id 的孤立 PNG 资源（背景件）置于最底层
- 无 sprite 数据时回退：所有资源按文件顺序合成
"""
import io
import re
import struct

from PIL import Image, ImageChops

PNG_SIG = b'\x89PNG\r\n\x1a\n'
IEND = b'IEND\xaeB\x60\x82'


def _read_cstr(tail: bytes, tpos: int) -> str:
    """类型码 04 后的字符串：04 00 00 00 + len(4) + utf8/gbk 字节"""
    slen = int.from_bytes(tail[tpos + 4:tpos + 8], 'little')
    if not (0 < slen < 80):
        return ""
    raw = tail[tpos + 8:tpos + 8 + slen]
    for enc in ('utf-8', 'gbk'):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return ""


def _find_pngs(data: bytes):
    """返回 [(start, end), ...] 所有内嵌 PNG 的起止位置"""
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
    return spans


def _iter_fields(blk: bytes, marker: int):
    """枚举 Godot 二进制风格字段。

    结构：marker(4) + name_len(4) + name(\0 填充到 4 对齐) + type(4) + value...
    产出 (name, type, value_start)
    """
    tag = bytes([marker]) + b'\x00\x00\x00'
    i = 0
    while True:
        m = blk.find(tag, i)
        if m < 0:
            return
        i = m + 4
        name_len = int.from_bytes(blk[m + 4:m + 8], 'little')
        if not (0 < name_len < 40):
            continue
        try:
            name = blk[m + 8:m + 8 + name_len].rstrip(b'\x00').decode('ascii')
        except Exception:
            continue
        if not name or not all(c.isalnum() or c == '_' for c in name):
            continue
        name_total = (name_len + 3) & ~3
        yield name, m + 8 + name_total


def _read_field(blk: bytes, marker: int, want: str, default=None):
    """读取指定字段的值（按 marker 类型解析）。"""
    for name, vp in _iter_fields(blk, marker):
        if name != want or vp + 4 > len(blk):
            continue
        t = int.from_bytes(blk[vp:vp + 4], 'little')
        if marker == 0x15:
            if t == 1 and vp + 8 <= len(blk):  # bool
                return int.from_bytes(blk[vp + 4:vp + 8], 'little')
            if t == 2 and vp + 8 <= len(blk):  # int
                return struct.unpack('<i', blk[vp + 4:vp + 8])[0]
            if t == 3 and vp + 8 <= len(blk):  # float
                return round(struct.unpack('<f', blk[vp + 4:vp + 8])[0], 3)
            if t == 5 and vp + 12 <= len(blk):  # Vector2
                return (round(struct.unpack('<f', blk[vp + 4:vp + 8])[0], 3),
                        round(struct.unpack('<f', blk[vp + 8:vp + 12])[0], 3))
        else:  # marker == 0x04：ID / 字符串等
            if t in (2, 0x10002, 0x10003) and vp + 8 <= len(blk):  # int / ID
                return struct.unpack('<i', blk[vp + 4:vp + 8])[0]
            if t == 1 and vp + 8 <= len(blk):  # bool
                return int.from_bytes(blk[vp + 4:vp + 8], 'little')
    return default


def parse_pngremix(data: bytes):
    """解析 pngRemix 文件。

    返回 (resources, sprites)：
    - resources: [{'img','x','y','hash','name'}]
    - sprites:   [{'idx','id','parent','z','hash','oe','om','visible',
                   'pos':(x,y) 本地节点坐标, 'off':(x,y) 纹理绘制偏移,
                   'world':(wx,wy) 世界纹理中心坐标}]
    """
    spans = _find_pngs(data)
    if not spans:
        raise ValueError("文件中未找到内嵌 PNG 图片")

    resources = []
    for ri, (st, en) in enumerate(spans):
        img = Image.open(io.BytesIO(data[st:en])).convert('RGBA')

        # offset / image_name：PNG 前 300 字节（元数据紧邻 PNG）
        meta = data[max(0, st - 300):st]
        ox = oy = 0.0
        op = meta.rfind(b'offset')
        if op >= 0:
            ox = struct.unpack('<f', meta[op + 12:op + 16])[0]
            oy = struct.unpack('<f', meta[op + 16:op + 20])[0]
        name = ""
        npos = meta.rfind(b'image_name')
        if npos >= 0:
            tail = meta[npos + 10:npos + 10 + 200]
            tpos = tail.find(b'\x04\x00\x00\x00')
            if tpos >= 0:
                name = _read_cstr(tail, tpos)

        # 资源 id 哈希：窗口从上一张 PNG 起点开始（id 字段在元数据尾部）
        win_start = spans[ri - 1][0] if ri > 0 else max(0, st - 400)
        win = data[win_start:st]
        h = None
        idm = win.rfind(b'\x69\x64\x00\x00')  # "id\0\0"
        if idm >= 0:
            cand = win[idm + 8:idm + 12]
            if cand != b'\x00\x00\x00\x00':
                h = cand.hex()

        resources.append({'img': img, 'x': ox, 'y': oy, 'hash': h, 'name': name})

    # sprites_array 区段（第一张 PNG 之前）
    pos = data.find(b'sprites_array')
    if pos == -1:
        return resources, []
    sr = data[pos:spans[0][0]]
    z_pos = [m.start() for m in re.finditer(re.escape(b'z_index'), sr)]

    sprites = []
    for i, zp in enumerate(z_pos):
        # block 从上一个字段名起点(zp-8) 到下一个 block 字段名起点
        blk_end = z_pos[i + 1] - 8 if i + 1 < len(z_pos) else len(sr)
        blk = sr[zp - 8:blk_end]

        z = _read_field(blk, 0x15, 'z_index', 0) or 0
        position = _read_field(blk, 0x15, 'position') or (0.0, 0.0)
        offset = _read_field(blk, 0x15, 'offset') or (0.0, 0.0)
        oe = _read_field(blk, 0x15, 'open_eyes', 1)
        om = _read_field(blk, 0x15, 'open_mouth', 0)
        visible = _read_field(blk, 0x15, 'visible', 1)
        clip = _read_field(blk, 0x15, 'clip', 0) or 0

        sprite_id = _read_field(blk, 0x04, 'sprite_id')
        parent_id = _read_field(blk, 0x04, 'parent_id')
        image_id = _read_field(blk, 0x04, 'image_id')

        h = None
        if image_id:  # 0 / None 表示无图片（文件夹节点）
            h = struct.pack('<i', image_id).hex()

        sprites.append({
            'idx': i,
            'id': sprite_id,
            'parent': parent_id,
            'z': float(z),
            'hash': h,
            'oe': int(oe) if oe is not None else 1,
            'om': int(om) if om is not None else 0,
            'visible': int(visible) if visible is not None else 1,
            'clip': int(clip),
            'pos': (float(position[0]), float(position[1])),
            'off': (float(offset[0]), float(offset[1])),
        })

    # 世界坐标：子节点挂在父节点的 Sprite2D（其 position = 父 offset）下，
    # 故纹理世界中心 = 沿父链对每个节点（含自身、含 folder/root）累加 (pos + off)
    by_id = {s['id']: s for s in sprites if s['id'] is not None}
    for s in sprites:
        ax = ay = 0.0
        clips = []
        seen = set()
        cur = s
        while cur and cur['id'] is not None and cur['id'] not in seen:
            seen.add(cur['id'])
            ax += cur['pos'][0] + cur['off'][0]
            ay += cur['pos'][1] + cur['off'][1]
            pid = cur['parent']
            cur = by_id.get(pid) if pid not in (None, -1) else None
            # clip 祖先：从父级开始向上收集（自身不裁剪自身）
            if cur is not None and cur['clip']:
                clips.append(cur['id'])
        s['world'] = (ax, ay)
        s['clip_ancestors'] = clips

    return resources, sprites


def _center_to_topleft(cx: float, cy: float, img: Image.Image) -> tuple[float, float]:
    """世界中心坐标（Godot y-down）→ PIL 左上角坐标"""
    return cx - img.width / 2, cy - img.height / 2


def render_pngremix_preview(data: bytes, thumb_w: int = 300) -> Image.Image:
    """合成 pngRemix 模型的 idle 状态预览图，返回缩放后的 PIL Image。

    失败时回退：返回第一张内嵌 PNG。
    """
    resources, sprites = parse_pngremix(data)
    by_hash = {r['hash']: r for r in resources if r['hash']}
    by_id = {s['id']: s for s in sprites if s['id'] is not None}

    layers = []

    # 构建渲染顺序：Godot z_as_relative=true，按树遍历排序
    # 每个父节点内按 z_index 排序子节点，整棵子树作为一组渲染
    children_by_parent = {}
    for sp in sprites:
        pid = sp['parent']
        children_by_parent.setdefault(pid, []).append(sp)

    draw_order = []

    def visit_tree(sid, depth=0):
        """深度优先遍历，子节点按 z_index 排序"""
        if sid is None:
            return
        sp = by_id.get(sid)
        if sp is None:
            return
        # 跳过隐藏/闭眼/张嘴件
        if sp['hash'] and sp['hash'] in by_hash:
            if sp['oe'] != 0 and sp['om'] != 1 and sp['visible'] != 0:
                if sp['clip'] != 1:
                    draw_order.append(sp)
        # 递归子节点（按 z_index 排序）
        kids = children_by_parent.get(sid, [])
        for kid in sorted(kids, key=lambda s: s['z']):
            visit_tree(kid['id'], depth + 1)

    # 从 root 的子节点开始
    root_kids = children_by_parent.get(None, [])
    for kid in sorted(root_kids, key=lambda s: s['z']):
        visit_tree(kid['id'])

    # 按树遍历顺序构建图层
    for sp in draw_order:
        r = by_hash[sp['hash']]
        tx, ty = _center_to_topleft(sp['world'][0], sp['world'][1], r['img'])
        clips = [by_id[cid] for cid in sp.get('clip_ancestors', [])
                 if cid in by_id and by_id[cid]['hash'] in by_hash]
        layers.append({'img': r['img'], 'x': tx, 'y': ty,
                       'z': 0.0, 'idx': sp['idx'], 'clips': clips})

    # 无 image_id 的孤立资源（背景件）置于最底层
    for ri, r in enumerate(resources):
        if not r['hash']:
            tx, ty = _center_to_topleft(r['x'], r['y'], r['img'])
            layers.insert(0, {'img': r['img'], 'x': tx, 'y': ty,
                              'z': -999.0, 'idx': -1 - ri})

    # 兜底：无 sprite 数据时用所有资源
    if not layers:
        for j, r in enumerate(resources):
            tx, ty = _center_to_topleft(r['x'], r['y'], r['img'])
            layers.append({'img': r['img'], 'x': tx, 'y': ty,
                           'z': 0.0, 'idx': j})

    if not layers:
        return resources[0]['img'] if resources else Image.new('RGBA', (1, 1))

    # 层已按树遍历顺序排列（背景件已 insert 到最前）

    coords = [(l['x'], l['y'],
               l['x'] + l['img'].width, l['y'] + l['img'].height)
              for l in layers]
    min_x = min(c[0] for c in coords)
    min_y = min(c[1] for c in coords)
    max_x = max(c[2] for c in coords)
    max_y = max(c[3] for c in coords)
    w = int(max_x - min_x) + 1
    h = int(max_y - min_y) + 1

    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for l in layers:
        img = l['img']
        clip_ancs = l.get('clips')
        if clip_ancs:
            # clip 祖先裁剪：Godot set_clip_children_mode 裁剪到祖先纹理 rect
            img = img.copy()
            lx, ly = l['x'] - min_x, l['y'] - min_y
            mask = None
            for a in clip_ancs:
                ra = by_hash[a['hash']]
                ax0 = a['world'][0] - ra['img'].width / 2 - min_x
                ay0 = a['world'][1] - ra['img'].height / 2 - min_y
                # 矩形裁剪（Godot clip = CanvasItem.get_rect()）
                m = Image.new('L', (img.width, img.height), 0)
                from PIL import ImageDraw
                draw = ImageDraw.Draw(m)
                rx0 = int(round(ax0 - lx))
                ry0 = int(round(ay0 - ly))
                draw.rectangle([rx0, ry0,
                                rx0 + ra['img'].width - 1,
                                ry0 + ra['img'].height - 1], fill=255)
                mask = m if mask is None else ImageChops.multiply(mask, m)
            img.putalpha(ImageChops.multiply(img.getchannel('A'), mask))
        canvas.alpha_composite(img,
                               (int(round(l['x'] - min_x)),
                                int(round(l['y'] - min_y))))

    # 裁剪透明边距，只保留有内容的区域
    bbox = canvas.getbbox()
    if bbox:
        canvas = canvas.crop(bbox)

    w, h = canvas.size
    if w > thumb_w:
        ratio = thumb_w / w
        canvas = canvas.resize((thumb_w, max(1, int(h * ratio))), Image.LANCZOS)
    return canvas
