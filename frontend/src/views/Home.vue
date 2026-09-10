<template>
  <div>
    <div class="toolbar">
      <el-input
        v-model="search"
        placeholder="搜索作品标题、作者或标签..."
        style="width: 300px"
        clearable
        @keyup.enter="onSearch"
        @clear="onSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-radio-group
        v-if="searched"
        v-model="searchType"
        size="small"
        @change="loadWorks"
      >
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="work">作品</el-radio-button>
        <el-radio-button value="tag">标签</el-radio-button>
        <el-radio-button value="author">作者</el-radio-button>
      </el-radio-group>
    </div>

    <el-row :gutter="16" v-loading="loading">
      <el-col :span="6" v-for="work in works" :key="work.id">
        <el-card class="work-card" shadow="hover" @click="$router.push(`/work/${work.id}`)">
          <div class="preview">
            <img :src="previewUrl(work.preview_path)" :alt="work.title" />
          </div>
          <div class="info">
            <div class="title">{{ work.title }}</div>
            <div class="meta">
              <el-tag v-for="t in work.tags" :key="t.id" size="small" class="tag">{{ t.name }}</el-tag>
            </div>
            <div class="footer">
              <span class="author">{{ work.author.username }}</span>
              <span class="views"><el-icon><View /></el-icon> {{ work.views }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && works.length === 0" description="暂无作品" />

    <div class="pagination" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadWorks"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { worksApi } from '../api'

const works = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)
const search = ref('')
const searched = ref(false)
const searchType = ref('all')
const activeTag = ref('')
const popularTags = ['可爱', '二次元', '猫耳', '原创', 'Q版', '男生', '女生']

function previewUrl(path) {
  return path ? `/media/${path}` : ''
}

function toggleTag(tag) {
  activeTag.value = activeTag.value === tag ? '' : tag
  page.value = 1
  loadWorks()
}

function onSearch() {
  searched.value = !!search.value
  searchType.value = 'all'
  page.value = 1
  loadWorks()
}

async function loadWorks() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (activeTag.value) params.tag = activeTag.value
    if (search.value) {
      params.search = search.value
      params.search_type = searchType.value
    }
    const res = await worksApi.list(params)
    works.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

onMounted(loadWorks)
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.tag-chip {
  cursor: pointer;
}
.work-card {
  margin-bottom: 16px;
  cursor: pointer;
}
.preview {
  aspect-ratio: 1;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.preview img {
  max-height: 100%;
  max-width: 100%;
  object-fit: contain;
}
.info {
  padding: 8px 0;
}
.title {
  font-weight: 600;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta {
  display: flex;
  flex-wrap: nowrap;
  overflow: hidden;
  gap: 4px;
  margin-bottom: 6px;
  height: 24px;
}
.tag {
  flex-shrink: 0;
}
.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #888;
}
.views {
  display: flex;
  align-items: center;
  gap: 4px;
}
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
