from datetime import datetime

from django.contrib.auth import authenticate
from django.db import transaction
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken

from accounts.models import User
from accounts.schemas import RegisterIn, LoginIn, TokenOut, UserOut

router = Router(tags=["auth"])


@router.post("/register", response={201: TokenOut})
def register(request, payload: RegisterIn):
    """注册：若用户名已软删除则恢复，否则创建新用户"""
    username = payload.username.strip()
    if not username:
        raise HttpError(400, "用户名不能为空")
    # 查找已软删除的同名用户，恢复
    deleted_user = User.objects.filter(username=username, is_deleted=True).first()
    if deleted_user:
        deleted_user.is_deleted = False
        deleted_user.deleted_at = None
        deleted_user.set_password(payload.password)
        deleted_user.save()
        # 恢复该用户的作品
        from works.models import Work
        Work.objects.filter(author=deleted_user, is_deleted=True).update(is_deleted=False)
        user = deleted_user
    else:
        if User.objects.filter(username=username).exists():
            raise HttpError(400, "用户名已存在")
        user = User.objects.create_user(username=username, password=payload.password)

    refresh = RefreshToken.for_user(user)
    return 201, {"access": str(refresh.access_token), "refresh": str(refresh)}


@router.post("/login", response=TokenOut)
def login(request, payload: LoginIn):
    """登录"""
    user = authenticate(username=payload.username, password=payload.password)
    if not user or user.is_deleted:
        raise HttpError(401, "用户名或密码错误，或账号已注销")
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


@router.post("/deactivate", auth=JWTAuth())
def deactivate(request):
    """注销（软删除）"""
    user = request.auth
    with transaction.atomic():
        user.is_deleted = True
        user.deleted_at = datetime.now()
        user.save()
        # 软删除该用户的作品
        from works.models import Work
        Work.objects.filter(author=user, is_deleted=False).update(is_deleted=True)
    return {"detail": "账号已注销"}


@router.get("/me", auth=JWTAuth(), response=UserOut)
def me(request):
    """获取当前用户信息"""
    return request.auth
