<template>
  <div class="mine-page">
    <h2>我的作品</h2>
    <el-tabs v-model="activeTab" @tab-change="loadWorks">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="原创作品" name="original" />
      <el-tab-pane label="二改作品" name="remix" />
    </el-tabs>

    <el-row :gutter="16" v-loading="loading">
      <el-col :span="6" v-for="work in works" :key="work.id">
        <el-card class="work-card" shadow="hover">
          <div class="preview" @click="$router.push(`/work/${work.id}`)">
            <img :src="previewUrl(work.preview_path)" />
          </div>
          <div class="info">
            <div class="title" @click="$router.push(`/work/${work.id}`)">{{ work.title }}</div>
            <div class="meta">
              <el-tag v-for="t in work.tags" :key="t.id" size="small" class="tag">{{ t.name }}</el-tag>
            </div>
            <div class="actions">
              <el-button size="small" @click="openEdit(work)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(work)">删除</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && works.length === 0" description="暂无作品" />

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editVisible" title="编辑作品" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="标题"><el-input v-model="editForm.title" /></el-form-item>
        <el-form-item label="介绍"><el-input v-model="editForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="标签">
          <el-select v-model="editForm.tags" multiple filterable allow-create default-first-option style="width:100%" />
        </el-form-item>
        <el-form-item label="图源自"><el-input v-model="editForm.source" /></el-form-item>
        <el-form-item label="允许下载"><el-switch v-model="editForm.allow_download" /></el-form-item>
        <el-form-item label="允许二创"><el-switch v-model="editForm.allow_remix" /></el-form-item>
        <el-form-item label="替换文件">
          <input ref="fileInput" type="file" accept=".pngRemix,.zip" @change="onFileChange" style="display:none" />
          <el-button @click="$refs.fileInput.click()">
            {{ editForm.newFile ? editForm.newFile.name : '选择新文件' }}
          </el-button>
          <span v-if="editForm.newFile" class="file-hint">已选择，保存时替换原文件并重新生成预览图</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { worksApi } from '../api'

const works = ref([])
const loading = ref(false)
const activeTab = ref('all')
const editVisible = ref(false)
const saving = ref(false)
const fileInput = ref(null)
const editForm = reactive({ id: null, title: '', description: '', tags: [], source: '', allow_remix: false, allow_download: false, newFile: null })

function previewUrl(path) {
  return path ? `/media/${path}` : ''
}

async function loadWorks() {
  loading.value = true
  try {
    const res = await worksApi.mine({ type: activeTab.value })
    works.value = res.data.items
  } finally {
    loading.value = false
  }
}

function openEdit(work) {
  editForm.id = work.id
  editForm.title = work.title
  editForm.description = work.description
  editForm.tags = work.tags.map(t => t.name)
  editForm.source = work.source
  editForm.allow_remix = work.allow_remix
  editForm.allow_download = work.allow_download
  editForm.newFile = null
  if (fileInput.value) fileInput.value.value = ''
  editVisible.value = true
}

function onFileChange(e) {
  editForm.newFile = e.target.files[0] || null
}

async function saveEdit() {
  saving.value = true
  try {
    await worksApi.update(editForm.id, {
      title: editForm.title,
      description: editForm.description,
      tags: editForm.tags,
      source: editForm.source,
      allow_remix: editForm.allow_remix,
      allow_download: editForm.allow_download,
    })
    // 如果选择了新文件，替换原文件并重新生成预览图
    if (editForm.newFile) {
      const fd = new FormData()
      fd.append('file', editForm.newFile)
      await worksApi.replaceFile(editForm.id, fd)
    }
    ElMessage.success('保存成功')
    editVisible.value = false
    loadWorks()
  } finally {
    saving.value = false
  }
}

async function handleDelete(work) {
  try {
    await ElMessageBox.confirm(`确定删除作品"${work.title}"吗？`, '提示', { type: 'warning' })
    await worksApi.delete(work.id)
    ElMessage.success('已删除')
    loadWorks()
  } catch {}
}

onMounted(loadWorks)
</script>

<style scoped>
.mine-page {
  max-width: 1100px;
  margin: 0 auto;
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
}
.title {
  font-weight: 600;
  cursor: pointer;
  margin: 8px 0 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tag {
  margin-right: 4px;
  margin-bottom: 4px;
}
.actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
.file-hint {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
