from django.conf import settings
from django.db import models


class Tag(models.Model):
    """标签"""
    name = models.CharField(max_length=50, unique=True, verbose_name="标签名")

    class Meta:
        db_table = 'tag'
        verbose_name = '标签'
        verbose_name_plural = '标签'

    def __str__(self):
        return self.name


class Work(models.Model):
    """作品（PNGTuber 模型）"""
    title = models.CharField(max_length=200, verbose_name="标题")
    description = models.TextField(blank=True, default='', verbose_name="介绍")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='works',
        verbose_name="作者"
    )
    file_path = models.CharField(max_length=500, verbose_name="模型文件路径")
    preview_path = models.CharField(max_length=500, blank=True, default='', verbose_name="预览图路径")
    tags = models.ManyToManyField(Tag, blank=True, related_name='works', verbose_name="标签")
    source = models.CharField(max_length=500, verbose_name="图源自")
    allow_remix = models.BooleanField(default=False, verbose_name="是否允许二改")
    allow_download = models.BooleanField(default=False, verbose_name="是否允许下载")
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='remakes',
        verbose_name="原作品"
    )
    views = models.PositiveIntegerField(default=0, verbose_name="浏览量")
    likes = models.PositiveIntegerField(default=0, verbose_name="点赞数")
    downloads = models.PositiveIntegerField(default=0, verbose_name="下载数")
    is_deleted = models.BooleanField(default=False, verbose_name="是否已删除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'work'
        verbose_name = '作品'
        verbose_name_plural = '作品'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Like(models.Model):
    """点赞记录"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name="用户"
    )
    work = models.ForeignKey(
        Work,
        on_delete=models.CASCADE,
        related_name='like_records',
        verbose_name="作品"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="点赞时间")

    class Meta:
        db_table = 'like'
        verbose_name = '点赞'
        verbose_name_plural = '点赞'
        unique_together = ('user', 'work')

    def __str__(self):
        return f"{self.user.username} likes {self.work.title}"
