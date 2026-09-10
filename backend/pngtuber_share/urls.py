"""
URL configuration for pngtuber_share project.
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from pngtuber_share.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]

# 开发环境提供 media 文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
