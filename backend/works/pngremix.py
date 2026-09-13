"""PNGTuber Remix .pngRemix / .pngtuber 文件解析与预览合成

真实文件格式（由 Godot 4.3 源码 core/io/marshalls.cpp 与引擎脚本双向核实）：
- 文件不是 JSON，而是 Godot 的 FileAccess.store_var(dict, true) 二进制产物：
  u32 payload 长度 + 一个 Variant(Dictionary)
- 顶层 dict：version / sprites_array / settings_dict / input_array / image_manager_data
- 贴图以 PNG 字节包在 PackedByteArray(image_manager_data[i].runtime_texture) 内

trim 语义（关键，来源 Scripts/AutoLoads/LoadMisc.gd L67-80 等）：
- 导入开 Trim 时，引擎裁掉透明边，并把
  center_shift = trim.min - (原图尺寸 - 裁剪尺寸) / 2
  直接【加进部件 offset 与 image_data.offset】，保存的 runtime_texture 就是裁剪后的图。
- 因此文件里【没有】trim/origin/source_size 字段，Sprite2D 锚点恒为纹理中心；
  渲染方无需（也无法）再手算 trim，offset 已是最终补偿值。

节点变换链（来源 Misc/SpriteObject/sprite_object.tscn、sprite_object.gd get_state、
SpriteObjectClass.gd reparent_obj）：
  SpriteObject(Node2D: position / scale / rotation)
    └ Modifier1(z_index，z_as_relative=true → 沿链累加)
      └ Rotation / Modifier
        └ Sprite2D(position = offset，flip 用 scale ±1，纹理居中)
  reparent 时子 SpriteObject 挂到【父节点的 Sprite2D】下，所以：
  M_节点   = M_父Sprite2D · T(position) · R(rotation) · S(scale)
  M_贴图   = M_节点 · T(offset) · S(flip_h ? -1 : 1, flip_v ? -1 : 1)

clip（CanvasItem.clip_children_mode，Godot 4.7）：1=仅裁后代；2=裁后代且自身也裁。
后代绘制被裁到该节点 Sprite2D【实际绘制的帧四边形】（屏幕空间，多帧部件按当前帧尺寸），
沿父链所有 clip 祖先取交集；多边形顶点须按 TL→TR→BR→BL 绕序，否则填充成自交蝴蝶结。

idle 预览过滤：
- visible=false 跳过
- should_blink=true 且 open_eyes=false 的是【闭眼替件】，跳过
- should_talk=true 且 open_mouth=true 的是【张嘴替件】，跳过
- 文件夹节点不绘制，但其 transform / z 仍在链路上
- 没有任何 sprite 引用的孤立图片垫最底层（PSD 导入等历史数据）

坐标：Godot 2D y 向下，与 PIL 一致，不翻转。
"""
import io
import math
import struct

from PIL import Image, ImageChops, ImageDraw

PNG_SIG = b'\x89PNG\r\n\x1a\n'
IEND = b'IEND\xaeB`\x82'

# ---- Godot Variant 类型码（core/variant/variant.h）----
T_NIL, T_BOOL, T_INT, T_FLOAT, T_STR, T_VEC2, T_VEC2I, T_RECT2, T_RECT2I = range(9)
T_VEC3, T_VEC3I, T_TR2D, T_VEC4, T_VEC4I, T_PLANE, T_QUAT, T_AABB = range(9, 17)
T_BASIS, T_TR3D, T_PROJ, T_COLOR, T_SNAME, T_NPATH, T_RID, T_OBJECT, T_CALL, T_SIG = range(17, 27)
T_DICT, T_ARRAY = 27, 28
PB_BA, PB_I32, PB_I64, PB_F32, PB_F64, PB_STR, PB_V2, PB_V3, PB_COL, PB_V4 = range(29, 39)

_FLAG_64 = 1 << 16
_TYPED_MASK = 0b11 << 16
_TYPED_BUILTIN = 0b01 << 16
_TYPED_CLASS = 0b10 << 16
_TYPED_SCRIPT = 0b11 << 16


class _Reader:
    """Godot 二进制 Variant 解码器（store_var(allow_objects=True) 读路径所需子集）。"""

    __slots__ = ('b', 'i')

    def __init__(self, b: bytes):
        self.b = b
        self.i = 0

    def u32(self):
        v = struct.unpack_from('<I', self.b, self.i)[0]
        self.i += 4
        return v

    def i32(self):
        v = struct.unpack_from('<i', self.b, self.i)[0]
        self.i += 4
        return v

    def u64(self):
        v = struct.unpack_from('<Q', self.b, self.i)[0]
        self.i += 8
        return v

    def f32(self):
        v = struct.unpack_from('<f', self.b, self.i)[0]
        self.i += 4
        return v

    def f64(self):
        v = struct.unpack_from('<d', self.b, self.i)[0]
        self.i += 8
        return v

    def string(self):
        n = self.u32()
        pad = (4 - n % 4) % 4
        raw = self.b[self.i:self.i + n]
        self.i += n + pad
        return raw.rstrip(b'\x00').decode('utf-8', 'replace')

    def var(self, depth=0):
        if depth > 32:
            raise ValueError('Variant 嵌套过深')
        header = self.u32()
        t = header & 0xFF
        wide = bool(header & _FLAG_64)

        if t == T_NIL:
            return None
        if t == T_BOOL:
            return bool(self.u32())
        if t == T_INT:
            return self.u64() if wide else self.i32()
        if t == T_FLOAT:
            return self.f64() if wide else self.f32()
        if t in (T_STR, T_SNAME):
            return self.string()
        if t == T_VEC2:
            return (self.f64(), self.f64()) if wide else (self.f32(), self.f32())
        if t == T_VEC2I:
            return (self.i32(), self.i32())
        if t == T_VEC3:
            return ((self.f64(), self.f64(), self.f64()) if wide
                    else (self.f32(), self.f32(), self.f32()))
        if t in (T_VEC4, T_QUAT, T_PLANE):
            return tuple(self.f64() if wide else self.f32() for _ in range(4))
        if t == T_COLOR:
            return tuple(self.f32() for _ in range(4))
        if t in (T_RECT2, T_TR2D, T_AABB):
            return tuple(self.f64() if wide else self.f32() for _ in range(4 if t == T_RECT2 else (2 if t == T_AABB else 6)))
        if t == T_NPATH:
            n = self.u32() & 0x7FFFFFFF
            sub = self.u32()
            flags = self.u32()
            names = [self.string() for _ in range(n + sub)]
            return ('NodePath', names, bool(flags & 1))
        if t == T_RID:
            return ('RID', self.u64())
        if t == T_OBJECT:
            if header & _FLAG_64:  # OBJECT_AS_ID
                return ('ObjID', self.u64())
            cls = self.string()
            if not cls:
                return None
            count = self.u32()
            props = {}
            for _ in range(count):
                k = self.string()
                props[k] = self.var(depth + 1)
            return ('Obj', cls, props)
        if t == T_CALL:
            return ('Callable',)
        if t == T_SIG:
            return ('Signal', self.string(), self.u64())
        if t == T_DICT:
            count = self.u32() & 0x7FFFFFFF
            out = {}
            for _ in range(count):
                k = self.var(depth + 1)
                out[str(k)] = self.var(depth + 1)
            return out
        if t == T_ARRAY:
            mask = header & _TYPED_MASK
            if mask == _TYPED_BUILTIN:
                self.u32()
            elif mask in (_TYPED_CLASS, _TYPED_SCRIPT):
                self.string()
                if mask == _TYPED_SCRIPT:
                    self.var(depth + 1)
            count = self.u32() & 0x7FFFFFFF
            return [self.var(depth + 1) for _ in range(count)]
        if t == PB_BA:
            n = self.u32()
            raw = bytes(self.b[self.i:self.i + n])
            self.i += n + (4 - n % 4) % 4
            return ('bytes', raw)
        if t == PB_I32:
            n = self.u32()
            v = [self.i32() for _ in range(n)]
            return v
        if t == PB_I64:
            n = self.u32()
            return [self.u64() for _ in range(n)]
        if t == PB_F32:
            n = self.u32()
            return [self.f32() for _ in range(n)]
        if t == PB_F64:
            n = self.u32()
            return [self.f64() for _ in range(n)]
        if t == PB_STR:
            n = self.u32()
            return [self.string() for _ in range(n)]
        if t in (PB_V2, PB_V3, PB_COL, PB_V4):
            n = self.u32()
            comp = {PB_V2: 2, PB_V3: 3, PB_COL: 4, PB_V4: 4}[t]
            rd = self.f64 if (wide and t != PB_COL) else self.f32
            return [tuple(rd() for _ in range(comp)) for _ in range(n)]
        raise ValueError(f'不支持的 Variant 类型 {t} @offset {self.i - 4}')


# ---- 2D 仿射（3x3，对点用列向量；Godot 变换左乘）----

def _mat_identity():
    return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def _mat_mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
                 for i in range(3))


def _mat_translate(x, y):
    return ((1.0, 0.0, x), (0.0, 1.0, y), (0.0, 0.0, 1.0))


def _mat_rotate(rad):
    c, s = math.cos(rad), math.sin(rad)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def _mat_scale(sx, sy):
    return ((sx, 0.0, 0.0), (0.0, sy, 0.0), (0.0, 0.0, 1.0))


def _mat_apply(m, p):
    x, y = p
    return (m[0][0] * x + m[0][1] * y + m[0][2],
            m[1][0] * x + m[1][1] * y + m[1][2])


def _mat_invert(m):
    (a, b, c), (e, f, g) = m[0], m[1]
    det = a * f - b * e
    if abs(det) < 1e-12:
        return _mat_identity()
    return ((f / det, -b / det, (b * g - c * f) / det),
            (-e / det, a / det, (c * e - a * g) / det),
            (0.0, 0.0, 1.0))


def _find_pngs(data: bytes):
    """扫描内嵌 PNG（兜底路径使用），返回 [(start, end_exclusive-ish), ...]。"""
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


def _decode_png(raw: bytes):
    img = Image.open(io.BytesIO(raw))
    img.load()
    return img.convert('RGBA')


def parse_pngremix(data: bytes):
    """完整解析 .pngRemix。

    返回 {'images': {id: {'img','name','offset'}}, 'sprites': [sprite, ...]}
    sprite 字段：sid/parent/image/folder/pos/off/rot/scale/z/clip/visible/
                open_eyes/open_mouth/blink/talk/flip_h/flip_v/hframes/vframes/order
    """
    payload_len = struct.unpack_from('<I', data, 0)[0]
    if not (4 <= payload_len <= len(data) - 4 + 16):
        raise ValueError('不是合法的 pngRemix 文件（payload 长度异常）')
    r = _Reader(data)
    r.u32()
    save = r.var()
    if not isinstance(save, dict) or 'sprites_array' not in save:
        raise ValueError('pngRemix 顶层结构缺少 sprites_array')

    images = {}
    for im in save.get('image_manager_data', []):
        if not isinstance(im, dict):
            continue
        rt = im.get('runtime_texture')
        raw = rt[1] if isinstance(rt, tuple) and rt and rt[0] == 'bytes' else b''
        if not raw:
            rawimg = im.get('image_data')
            raw = rawimg[1] if isinstance(rawimg, tuple) and rawimg and rawimg[0] == 'bytes' else b''
        if not raw:
            continue
        off = im.get('offset', (0.0, 0.0)) or (0.0, 0.0)
        try:
            images[int(im['id'])] = {
                'img': _decode_png(raw),
                'name': str(im.get('image_name', '')),
                'offset': (float(off[0]), float(off[1])),
            }
        except Exception:
            continue

    sprites = []
    for order, sp in enumerate(save.get('sprites_array', [])):
        if not isinstance(sp, dict):
            continue
        states = sp.get('states') or []
        st = states[0] if states and isinstance(states[0], dict) else {}

        def g(key, default):
            return st.get(key, default)

        pos = g('position', (0.0, 0.0)) or (0.0, 0.0)
        off = g('offset', (0.0, 0.0)) or (0.0, 0.0)
        scale = g('scale', (1.0, 1.0)) or (1.0, 1.0)
        sid_raw = sp.get('sprite_id')
        pid_raw = sp.get('parent_id')
        sprites.append({
            'order': order,
            'sid': int(sid_raw) if sid_raw is not None else None,
            'parent': int(pid_raw) if pid_raw is not None else 0,
            'image': int(sp.get('image_id') or 0),
            'folder': bool(g('folder', False)),
            'pos': (float(pos[0]), float(pos[1])),
            'off': (float(off[0]), float(off[1])),
            'rot': float(g('rotation', 0.0) or 0.0),
            'scale': (float(scale[0]), float(scale[1])),
            'z': int(g('z_index', 0) or 0),
            'clip': int(g('clip', 0) or 0),
            'visible': bool(g('visible', True)),
            'open_eyes': bool(g('open_eyes', True)),
            'open_mouth': bool(g('open_mouth', False)),
            'blink': bool(g('should_blink', False)),
            'talk': bool(g('should_talk', False)),
            'flip_h': bool(g('flip_sprite_h', False)),
            'flip_v': bool(g('flip_sprite_v', False)),
            'hframes': max(1, int(g('hframes', 1) or 1)),
            'vframes': max(1, int(g('vframes', 1) or 1)),
        })

    return {'images': images, 'sprites': sprites}


def _build_transforms(model):
    """沿场景树挂仿射矩阵、全局 z、clip 祖先链；返回可见待绘图层列表。"""
    sprites = model['sprites']
    images = model['images']
    by_id = {s['sid']: s for s in sprites if s['sid'] is not None}
    children = {}
    for s in sprites:
        children.setdefault(s['parent'] if s['parent'] in by_id else 0, []).append(s)
    for v in children.values():
        v.sort(key=lambda s: s['order'])

    dfs = [0]

    def walk(s, m_parent, gz, clip_chain):
        px, py = s['pos']
        sx, sy = s['scale']
        m_node = _mat_mul(m_parent,
                          _mat_mul(_mat_translate(px, py),
                                   _mat_mul(_mat_rotate(s['rot']),
                                            _mat_scale(sx, sy))))
        m_img = _mat_mul(
            m_node,
            _mat_mul(_mat_translate(*s['off']),
                     _mat_scale(-1.0 if s['flip_h'] else 1.0,
                                -1.0 if s['flip_v'] else 1.0)))
        s['m_node'] = m_node
        s['m_img'] = m_img
        s['gz'] = gz + s['z']
        s['clips'] = clip_chain
        s['dfs'] = dfs[0]
        dfs[0] += 1
        my_chain = clip_chain + ([s] if s['clip'] in (1, 2) else [])
        for k in children.get(s['sid'], []):
            walk(k, m_img, s['gz'], my_chain)

    for root in children.get(0, []):
        walk(root, _mat_identity(), 0, [])

    layers = []
    for s in sprites:
        if 'm_img' not in s:
            continue
        if s['folder'] or not s['image'] or s['image'] not in images:
            continue
        if not s['visible']:
            continue
        if s['blink'] and not s['open_eyes']:
            continue
        if s['talk'] and s['open_mouth']:
            continue
        layers.append(s)
    return layers


def render_pngremix_preview(data: bytes, thumb_w: int = 300) -> Image.Image:
    """合成 pngRemix 模型 idle 状态预览图，返回裁剪透明边并缩放到 thumb_w 的 RGBA 图。"""
    model = parse_pngremix(data)
    images = model['images']
    if not images:
        raise ValueError('文件中未解析出内嵌 PNG 图片')

    layers = _build_transforms(model)

    # 孤立图片（没有任何 sprite 引用）垫最底层，用 image_data.offset 定位
    referenced = {s['image'] for s in model['sprites'] if s['image']}
    orphans = []
    for iid, im in images.items():
        if iid in referenced:
            continue
        w, h = im['img'].size
        ox, oy = im['offset']
        orphans.append({
            'm_img': _mat_translate(ox, oy), 'gz': -1 << 30, 'dfs': -iid,
            'clips': [], 'image': iid, 'hframes': 1, 'vframes': 1,
            '_corners': [(ox - w / 2, oy - h / 2), (ox + w / 2, oy - h / 2),
                         (ox - w / 2, oy + h / 2), (ox + w / 2, oy + h / 2)],
        })

    def layer_image(s):
        iid = s['image']
        src = images[iid]['img']
        if s['hframes'] > 1 or s['vframes'] > 1:
            fw, fh = src.width // s['hframes'], src.height // s['vframes']
            src = src.crop((0, 0, fw, fh))  # idle 取第 0 帧
        return src

    # 世界坐标包围盒
    def corners(s):
        if '_corners' in s:
            return s['_corners']
        src = layer_image(s)
        hw, hh = src.width / 2, src.height / 2
        return [_mat_apply(s['m_img'], (x, y))
                for x in (-hw, hw) for y in (-hh, hh)]

    everything = orphans + layers
    box = [c for s in everything for c in corners(s)]
    if not box:
        return next(iter(images.values()))['img']
    min_x = min(c[0] for c in box)
    min_y = min(c[1] for c in box)
    max_x = max(c[0] for c in box)
    max_y = max(c[1] for c in box)
    W = int(math.ceil(max_x - min_x)) + 2
    H = int(math.ceil(max_y - min_y)) + 2
    to_canvas = _mat_translate(-min_x + 1, -min_y + 1)

    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for s in sorted(everything, key=lambda x: (x['gz'], x['dfs'])):
        src = layer_image(s)
        w, h = src.size
        # 输出像素 (ox,oy) → 源像素：A^-1，A = to_canvas · M_img · T(-w/2,-h/2)
        a = _mat_mul(to_canvas,
                     _mat_mul(s['m_img'], _mat_translate(-w / 2, -h / 2)))
        ai = _mat_invert(a)
        layer = src.transform(
            (W, H), Image.Transform.AFFINE,
            (ai[0][0], ai[0][1], ai[0][2], ai[1][0], ai[1][1], ai[1][2]),
            resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
        if s['clips']:
            # 每个 clip 祖先单独成遮罩后相乘（多个 clip 祖先 → 取交集，与 Godot
            # clip_children 沿父链逐层裁剪一致）；无嵌套时只有一个祖先。
            mask = Image.new('L', (W, H), 255)
            for anc in s['clips']:
                aim = images.get(anc['image'])
                if aim is None:
                    continue
                # clip 矩形 = 该 Sprite2D 实际绘制的帧四边形（多帧部件按帧尺寸）
                aw0, ah0 = aim['img'].size
                aw = aw0 // max(1, anc['hframes'])
                ah = ah0 // max(1, anc['vframes'])
                hw, hh = aw / 2, ah / 2
                # 顶点必须按 TL→TR→BR→BL 绕序，否则 ImageDraw 填充会变成
                # 自交的蝴蝶结（两对三角形），误挖眼睛中部。
                local = ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))
                am = _mat_mul(to_canvas, anc['m_img'])
                one = Image.new('L', (W, H), 0)
                ImageDraw.Draw(one).polygon(
                    [_mat_apply(am, p) for p in local], fill=255)
                mask = ImageChops.multiply(mask, one)
            layer.putalpha(ImageChops.multiply(layer.getchannel('A'), mask))
        canvas.alpha_composite(layer)

    bbox = canvas.getbbox()
    if bbox:
        canvas = canvas.crop(bbox)
    if canvas.width > thumb_w:
        canvas = canvas.resize(
            (thumb_w, max(1, round(canvas.height * thumb_w / canvas.width))),
            Image.LANCZOS)
    return canvas
