<template>
  <div class="detail-page" v-loading="loading">
    <template v-if="work">
      <div class="header">
        <div class="preview">
          <img :src="previewUrl(work.preview_path)" :alt="work.title" />
        </div>
        <div class="info">
          <h1>{{ work.title }}</h1>
          <div class="author">
            作者：{{ work.author.username }} · 创建于 {{ formatDate(work.created_at) }}
            <el-button v-if="work.parent_id" link type="primary" @click="goParent">
              ← 查看原作品
            </el-button>
          </div>
          <div class="stats">
            <span><el-icon><View /></el-icon> 浏览 {{ work.views }}</span>
            <span class="like-btn" :class="{ liked: work.liked }" @click="toggleLike">
              <el-icon><Star /></el-icon> 点赞 {{ work.likes }}
            </span>
            <span><el-icon><Download /></el-icon> 下载 {{ work.downloads }}</span>
            <el-tag :type="permissionTagType" size="small">
              {{ permissionLabel }}
            </el-tag>
          </div>
          <div class="tags">
            <el-tag v-for="t in work.tags" :key="t.id" class="tag">{{ t.name }}</el-tag>
          </div>
          <div class="source">
            <strong>图源自：</strong>
            <a v-if="isUrl(work.source)" :href="work.source" target="_blank">{{ work.source }}</a>
            <span v-else>{{ work.source }}</span>
          </div>
          <div class="actions">
            <el-button v-if="work.allow_download" @click="handleDownload">
              <el-icon><Download /></el-icon> 下载模型
            </el-button>
            <el-button v-if="work.allow_remix" type="primary" @click="goRemix">
              <el-icon><EditPen /></el-icon> 上传二创
            </el-button>
          </div>
        </div>
      </div>

      <el-card class="description-card">
        <h3>作品介绍</h3>
        <div class="desc-text">{{ work.description || '暂无介绍' }}</div>
      </el-card>

      <el-card class="remakes-card">
        <h3>二创作品 ({{ work.remakes ? work.remakes.length : 0 }})</h3>
        <div v-if="work.remakes && work.remakes.length" class="remake-list">
          <div v-for="r in work.remakes" :key="r.id" class="remake-item" @click="$router.push(`/work/${r.id}`)">
            <div class="remake-preview">
              <img :src="previewUrl(r.preview_path)" />
            </div>
            <div class="remake-info">
              <div class="remake-title">{{ r.title }}</div>
              <div class="remake-author">by {{ r.author.username }} · {{ formatDate(r.created_at) }}</div>
              <div class="remake-desc">{{ r.description || '暂无介绍' }}</div>
              <div class="remake-actions">
                <el-tag v-if="r.allow_download" type="success" size="small">可下载</el-tag>
                <el-tag v-else type="info" size="small">不可下载</el-tag>
                <span class="remake-go">查看详情 →</span>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无二创作品" :image-size="60" />
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { worksApi } from '../api'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const work = ref(null)
const loading = ref(false)

function previewUrl(path) {
  return path ? `/media/${path}` : ''
}

function formatDate(s) {
  return new Date(s).toLocaleString('zh-CN')
}

function isUrl(s) {
  return /^https?:\/\//.test(s)
}

const permissionLabel = computed(() => {
  if (!work.value) return ''
  const { allow_download, allow_remix } = work.value
  if (allow_download && allow_remix) return '允许下载和二改'
  if (allow_download) return '仅允许下载'
  if (allow_remix) return '仅允许二改'
  return '不允许下载和二改'
})

const permissionTagType = computed(() => {
  if (!work.value) return 'info'
  const { allow_download, allow_remix } = work.value
  if (allow_download && allow_remix) return 'success'
  if (allow_download || allow_remix) return 'warning'
  return 'danger'
})

function goParent() {
  router.push(`/work/${work.value.parent_id}`)
}

function goRemix() {
  router.push({
    path: '/upload',
    query: { parent: work.value.id, title: work.value.title },
  })
}

function handleDownload() {
  window.location.href = worksApi.downloadUrl(work.value.id)
}

async function toggleLike() {
  if (!userStore.isLogin()) {
    ElMessage.warning('请先登录')
    return router.push('/login')
  }
  try {
    const res = await worksApi.like(work.value.id)
    work.value.liked = res.data.liked
    work.value.likes = res.data.likes
  } catch (e) {
    // 拦截器已处理错误
  }
}

async function loadDetail() {
  loading.value = true
  try {
    const res = await worksApi.detail(route.params.id)
    work.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(loadDetail)

watch(() => route.params.id, () => {
  if (route.params.id) loadDetail()
})
</script>

<style scoped>
.detail-page {
  max-width: 1100px;
  margin: 0 auto;
}
.header {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
}
.preview {
  width: 360px;
  height: 360px;
  background: #fff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
}
.preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.info {
  flex: 1;
}
.info h1 {
  margin: 0 0 8px;
}
.author {
  color: #888;
  margin-bottom: 12px;
}
.stats {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 12px;
}
.stats span {
  display: flex;
  align-items: center;
  gap: 4px;
}
.like-btn {
  cursor: pointer;
  transition: color 0.2s;
}
.like-btn:hover {
  color: #e6a23c;
}
.like-btn.liked {
  color: #e6a23c;
  font-weight: bold;
}
.tags {
  margin-bottom: 12px;
}
.tag {
  margin-right: 6px;
}
.source {
  background: #fffbe6;
  border: 1px solid #ffe58f;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 16px;
}
.actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}
.description-card, .remakes-card {
  margin-bottom: 20px;
}
.desc-text {
  white-space: pre-wrap;
  line-height: 1.6;
}
.remake-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.remake-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.remake-item:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}
.remake-preview {
  width: 160px;
  height: 160px;
  background: #f5f7fa;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
}
.remake-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.remake-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.remake-title {
  font-weight: 600;
  font-size: 16px;
}
.remake-author {
  font-size: 13px;
  color: #909399;
}
.remake-desc {
  flex: 1;
  color: #606266;
  line-height: 1.6;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}
.remake-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.remake-go {
  color: #409eff;
  font-size: 13px;
}
</style>
