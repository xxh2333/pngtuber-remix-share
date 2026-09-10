import os
from typing import List, Optional

from django.conf import settings
from django.db.models import F, Q, Value, IntegerField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from ninja import Router, File, Form, Query
from ninja.files import UploadedFile
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from works.models import Work, Tag, Like
from works.schemas import (
    WorkCreateIn, WorkUpdateIn, WorkListItemOut, WorkDetailOut,
    WorkRemakeItemOut, PaginatedWorksOut, RemixCreateIn, AuthorOut, TagOut
)
from works.services import save_model_file, generate_preview

router = Router(tags=["works"])


def _get_or_create_tags(tag_names: List[str]) -> List[Tag]:
    """根据标签名列表获取或创建标签"""
    tags = []
    for name in tag_names:
        name = name.strip()
        if name:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
    return tags


def _serialize_work_list_item(work: Work) -> dict:
    return {
        "id": work.id,
        "title": work.title,
        "preview_path": work.preview_path,
        "author": AuthorOut.from_orm(work.author).dict(),
        "tags": [TagOut.from_orm(t).dict() for t in work.tags.all()],
        "views": work.views,
        "likes": work.likes,
        "allow_remix": work.allow_remix,
        "allow_download": work.allow_download,
        "parent_id": work.parent_id,
        "created_at": work.created_at.isoformat(),
    }


def _serialize_work_detail(work: Work, user=None) -> dict:
    remakes = Work.objects.filter(parent=work, is_deleted=False).select_related('author')
    return {
        "id": work.id,
        "title": work.title,
        "description": work.description,
        "author": AuthorOut.from_orm(work.author).dict(),
        "preview_path": work.preview_path,
        "tags": [TagOut.from_orm(t).dict() for t in work.tags.all()],
        "source": work.source,
        "allow_remix": work.allow_remix,
        "allow_download": work.allow_download,
        "parent_id": work.parent_id,
        "views": work.views,
        "likes": work.likes,
        "downloads": work.downloads,
        "liked": Like.objects.filter(user=user, work=work).exists() if user else False,
        "created_at": work.created_at.isoformat(),
        "updated_at": work.updated_at.isoformat(),
        "remakes": [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "preview_path": r.preview_path,
                "author": AuthorOut.from_orm(r.author).dict(),
                "allow_download": r.allow_download,
                "created_at": r.created_at.isoformat(),
            }
            for r in remakes
        ],
    }


@router.post("/", auth=JWTAuth(), response=WorkDetailOut)
def create_work(
    request,
    title: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    source: str = Form(...),
    allow_remix: bool = Form(False),
    allow_download: bool = Form(False),
    file: UploadedFile = File(...),
):
    """上传作品"""
    if not source.strip():
        raise HttpError(400, "图源自为必填项")

    user = request.auth
    tag_list = [t.strip() for t in tags.split(',') if t.strip()] if tags else []

    # 保存文件并生成预览图
    file_path = save_model_file(file, user.id)
    preview_path = generate_preview(file_path, user.id)

    work = Work.objects.create(
        title=title,
        description=description,
        author=user,
        file_path=file_path,
        preview_path=preview_path,
        source=source,
        allow_remix=allow_remix,
        allow_download=allow_download,
    )
    work.tags.set(_get_or_create_tags(tag_list))

    return _serialize_work_detail(work, request.auth)


@router.post("/remix", auth=JWTAuth(), response=WorkDetailOut)
def create_remix(
    request,
    parent_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    source: str = Form(...),
    allow_remix: bool = Form(False),
    allow_download: bool = Form(False),
    file: UploadedFile = File(...),
):
    """上传二改作品"""
    if not source.strip():
        raise HttpError(400, "图源自为必填项")

    parent = get_object_or_404(Work, id=parent_id, is_deleted=False)
    if not parent.allow_remix:
        raise HttpError(400, "该作品不允许二改")

    user = request.auth
    tag_list = [t.strip() for t in tags.split(',') if t.strip()] if tags else []

    file_path = save_model_file(file, user.id)
    preview_path = generate_preview(file_path, user.id)

    work = Work.objects.create(
        title=title,
        description=description,
        author=user,
        file_path=file_path,
        preview_path=preview_path,
        source=source,
        allow_remix=allow_remix,
        allow_download=allow_download,
        parent=parent,
    )
    work.tags.set(_get_or_create_tags(tag_list))

    return _serialize_work_detail(work, request.auth)


@router.get("/", response=PaginatedWorksOut)
def list_works(
    request,
    page: int = 1,
    page_size: int = 12,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    search_type: str = "all",  # all | work | tag | author
):
    """作品列表（支持 tag 过滤、关键词搜索、搜索类型筛选）"""
    qs = Work.objects.filter(is_deleted=False).select_related('author').prefetch_related('tags')

    if tag:
        qs = qs.filter(tags__name=tag)
    if search:
        if search_type == "work":
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
        elif search_type == "tag":
            qs = qs.filter(tags__name__icontains=search).distinct()
        elif search_type == "author":
            qs = qs.filter(author__username__icontains=search)
        else:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(author__username__icontains=search) |
                Q(tags__name__icontains=search)
            ).distinct()

    total = qs.count()
    start = (page - 1) * page_size
    items = qs[start:start + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_work_list_item(w) for w in items],
    }


@router.get("/hot", response=PaginatedWorksOut)
def hot_works(
    request,
    page: int = 1,
    page_size: int = 50,
    period: str = "all",      # all | month | week | day
    sort: str = "composite",  # composite | views | likes
):
    """热榜：支持时间范围(all/month/week/day)和排序方式(composite/views/likes)"""
    qs = Work.objects.filter(is_deleted=False).select_related('author').prefetch_related('tags')

    now = timezone.now()
    if period == "month":
        qs = qs.filter(created_at__gte=now - timedelta(days=30))
    elif period == "week":
        qs = qs.filter(created_at__gte=now - timedelta(days=7))
    elif period == "day":
        qs = qs.filter(created_at__gte=now - timedelta(days=1))

    if sort == "views":
        qs = qs.annotate(
            score=F('views')
        ).order_by('-score')
    elif sort == "likes":
        qs = qs.annotate(
            score=F('likes')
        ).order_by('-score')
    else:
        qs = qs.annotate(
            score=ExpressionWrapper(
                F('views') * 1 + F('likes') * 3 + F('downloads') * 5,
                output_field=IntegerField()
            )
        ).order_by('-score')

    total = qs.count()
    start = (page - 1) * page_size
    items = qs[start:start + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_work_list_item(w) for w in items],
    }


@router.get("/mine", auth=JWTAuth(), response=PaginatedWorksOut)
def my_works(
    request,
    page: int = 1,
    page_size: int = 12,
    type: str = "all",  # all | original | remix
):
    """个人中心作品列表"""
    user = request.auth
    qs = Work.objects.filter(author=user, is_deleted=False).select_related('author').prefetch_related('tags')

    if type == "original":
        qs = qs.filter(parent__isnull=True)
    elif type == "remix":
        qs = qs.filter(parent__isnull=False)

    total = qs.count()
    start = (page - 1) * page_size
    items = qs[start:start + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_work_list_item(w) for w in items],
    }


@router.get("/{work_id}", response=WorkDetailOut)
def work_detail(request, work_id: int):
    """作品详情（浏览量 +1，含二改子栏）"""
    work = get_object_or_404(Work, id=work_id, is_deleted=False)
    # 浏览量原子递增
    Work.objects.filter(id=work_id).update(views=F('views') + 1)
    work.refresh_from_db()
    # 可选认证：有 token 则解析用户用于 liked 字段
    user = None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            user = JWTAuth()(request)
        except Exception:
            pass
    return _serialize_work_detail(work, user)


@router.put("/{work_id}", auth=JWTAuth(), response=WorkDetailOut)
def update_work(request, work_id: int, payload: WorkUpdateIn):
    """编辑自己的作品"""
    work = get_object_or_404(Work, id=work_id, is_deleted=False)
    if work.author_id != request.auth.id:
        raise HttpError(403, "无权编辑他人作品")

    data = payload.dict(exclude_unset=True)
    if 'tags' in data:
        work.tags.set(_get_or_create_tags(data.pop('tags')))
    for key, value in data.items():
        setattr(work, key, value)
    work.save()
    return _serialize_work_detail(work, request.auth)


@router.put("/{work_id}/file", auth=JWTAuth(), response=WorkDetailOut)
def replace_work_file(request, work_id: int, file: UploadedFile = File(...)):
    """替换作品文件（同时重新生成预览图）"""
    work = get_object_or_404(Work, id=work_id, is_deleted=False)
    if work.author_id != request.auth.id:
        raise HttpError(403, "无权编辑他人作品")

    # 删除旧文件
    old_file = os.path.join(settings.MEDIA_ROOT, work.file_path)
    old_preview = os.path.join(settings.MEDIA_ROOT, work.preview_path)
    for old in [old_file, old_preview]:
        if old and os.path.exists(old):
            os.remove(old)

    # 保存新文件并重新生成预览
    work.file_path = save_model_file(file, request.auth.id)
    work.preview_path = generate_preview(work.file_path, request.auth.id)
    work.save()
    return _serialize_work_detail(work, request.auth)


@router.delete("/{work_id}", auth=JWTAuth())
def delete_work(request, work_id: int):
    """软删除自己的作品"""
    work = get_object_or_404(Work, id=work_id, is_deleted=False)
    if work.author_id != request.auth.id:
        raise HttpError(403, "无权删除他人作品")
    work.is_deleted = True
    work.save()
    return {"detail": "作品已删除"}


@router.post("/{work_id}/like", auth=JWTAuth())
def toggle_like(request, work_id: int):
    """点赞/取消点赞（toggle）"""
    work = get_object_or_404(Work, id=work_id, is_deleted=False)
    user = request.auth
    liked = Like.objects.filter(user=user, work=work).first()
    if liked:
        liked.delete()
        Work.objects.filter(id=work_id).update(likes=F('likes') - 1)
    else:
        Like.objects.create(user=user, work=work)
        Work.objects.filter(id=work_id).update(likes=F('likes') + 1)
    work.refresh_from_db()
    return {"liked": liked is None, "likes": work.likes}


@router.get("/{work_id}/download")
def download_work(request, work_id: int):
    """下载模型文件（校验 allow_download，原子递增下载数）"""
    work = get_object_or_404(Work, id=work_id, is_deleted=False)
    if not work.allow_download:
        raise HttpError(403, "该作品不允许下载")
    file_full = os.path.join(settings.MEDIA_ROOT, work.file_path)
    if not os.path.exists(file_full):
        raise Http404("文件不存在")
    Work.objects.filter(id=work_id).update(downloads=F('downloads') + 1)
    filename = os.path.basename(work.file_path)
    # as_attachment=True 强制浏览器下载而非导航/预览
    return FileResponse(open(file_full, 'rb'), filename=filename, as_attachment=True)
