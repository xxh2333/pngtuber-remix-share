"""文件上传与预览图生成服务"""
import io
import os
import zipfile
from pathlib import Path

from django.conf import settings
from ninja.errors import HttpError
from PIL import Image

from works.pngremix import render_pngremix_preview, _find_pngs

# AI 模型文件扩展名黑名单
AI_MODEL_EXTENSIONS = {
    '.pt', '.pth', '.onnx', '.h5', '.pb', '.safetensors',
    '.bin', '.ckpt', '.gguf', '.tflite', '.mlmodel', '.ptl',
}

# 允许的图片扩展名
ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

# 支持的模型文件扩展名
MODEL_FILE_EXTENSIONS = {'.zip', '.pngremix', '.pngtuber'}


def _is_ai_model_file(filename: str) -> bool:
    """判断文件是否为 AI 模型文件"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in AI_MODEL_EXTENSIONS


def save_model_file(uploaded_file, user_id: int) -> str:
    """
    保存上传的 PNGTuber 模型文件（ZIP 包或 .pngRemix/.pngtuber 单文件）。
    校验扩展名、MIME，ZIP 包扫描内部 AI 模型文件。
    返回保存后的相对路径（相对 MEDIA_ROOT）。
    """
    filename = uploaded_file.name
    ext = Path(filename).suffix.lower()
    if ext not in MODEL_FILE_EXTENSIONS:
        raise HttpError(400, "仅支持上传 ZIP 或 .pngRemix/.pngtuber 格式文件")

    content = uploaded_file.read()

    if ext == '.zip':
        # 校验是否为有效的 ZIP 文件
        try:
            zf = zipfile.ZipFile(io.BytesIO(content))
            bad_file = zf.testzip()
            if bad_file:
                raise HttpError(400, f"ZIP 文件损坏: {bad_file}")
        except zipfile.BadZipFile:
            raise HttpError(400, "无效的 ZIP 文件")

        # 扫描内部文件，禁止 AI 模型文件
        for name in zf.namelist():
            if _is_ai_model_file(name):
                raise HttpError(400, f"禁止上传 AI 模型文件: {os.path.basename(name)}")
    else:
        # .pngRemix/.pngtuber：校验内含至少一张内嵌 PNG
        if not _find_pngs(content):
            raise HttpError(400, "无效的模型文件：未找到内嵌图片")

    # 保存文件
    user_dir = Path(settings.MEDIA_ROOT) / 'models' / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{Path(filename).stem}_{os.urandom(4).hex()}{ext}"
    save_path = user_dir / safe_name
    save_path.write_bytes(content)

    return f"models/{user_id}/{safe_name}"


# 向后兼容别名
save_model_zip = save_model_file


def _save_thumb(img: Image.Image, base_name: str, user_id: int) -> str:
    """生成并保存宽度 300px 的缩略图，返回相对路径"""
    preview_dir = Path(settings.MEDIA_ROOT) / 'previews' / str(user_id)
    preview_dir.mkdir(parents=True, exist_ok=True)

    thumb_name = f"{base_name}_thumb.png"
    thumb_path = preview_dir / thumb_name

    thumb = img.copy()
    if thumb.mode != 'RGBA':
        thumb = thumb.convert('RGBA')
    if thumb.width > 300:
        ratio = 300 / thumb.width
        thumb = thumb.resize((300, max(1, int(thumb.height * ratio))), Image.LANCZOS)
    thumb.save(thumb_path, format='PNG')

    return f"previews/{user_id}/{thumb_name}"


def generate_preview(model_relative_path: str, user_id: int) -> str:
    """
    从模型文件生成预览图。
    - ZIP：优先 normal.png / default.png / 0.png / idle.png，否则取第一张 PNG
    - .pngRemix/.pngtuber：解析内嵌分层图片合成 idle 状态预览图
    返回预览图的相对路径。
    """
    model_full_path = Path(settings.MEDIA_ROOT) / model_relative_path
    if not model_full_path.exists():
        raise HttpError(404, "模型文件不存在")

    ext = model_full_path.suffix.lower()
    base_name = Path(model_relative_path).stem

    if ext == '.zip':
        preferred_names = {'normal.png', 'default.png', '0.png', 'idle.png'}
        with zipfile.ZipFile(model_full_path, 'r') as zf:
            png_files = [n for n in zf.namelist() if n.lower().endswith('.png')]
            if not png_files:
                raise HttpError(400, "ZIP 包中未找到 PNG 图片")

            source_name = None
            for name in png_files:
                if os.path.basename(name).lower() in preferred_names:
                    source_name = name
                    break
            if not source_name:
                source_name = png_files[0]

            with zf.open(source_name) as f:
                img = Image.open(f)
                img.load()
    else:
        data = model_full_path.read_bytes()
        try:
            img = render_pngremix_preview(data)
        except Exception as e:
            # 兜底：直接取第一张内嵌 PNG
            spans = _find_pngs(data)
            if not spans:
                raise HttpError(400, f"模型文件解析失败：{e}")
            st, en = spans[0]
            img = Image.open(io.BytesIO(data[st:en]))
            img.load()

    return _save_thumb(img, base_name, user_id)
