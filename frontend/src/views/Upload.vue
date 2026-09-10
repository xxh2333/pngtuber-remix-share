<template>
  <div class="upload-page">
    <h2>{{ isRemix ? '上传二创作品' : '上传作品' }}</h2>
    <el-alert
      v-if="isRemix && parentTitle"
      :title="`二创自：${parentTitle}`"
      type="info"
      :closable="false"
      style="margin-bottom: 16px"
    />
    <el-form :model="form" label-width="100px" style="max-width: 700px">
      <el-form-item label="标题" required>
        <el-input v-model="form.title" placeholder="作品标题" />
      </el-form-item>
      <el-form-item label="介绍">
        <el-input v-model="form.description" type="textarea" :rows="4" placeholder="作品介绍" />
      </el-form-item>
      <el-form-item label="标签">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入标签后回车"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="图源自" required>
        <el-input v-model="form.source" placeholder="来源 URL 或文字说明（必填）" />
        <div class="tip">请填写图片/模型的来源，保护原作者权益</div>
      </el-form-item>
      <el-form-item label="授权设置">
        <el-select v-model="form.permission" placeholder="选择授权方式">
          <el-option label="允许下载和二改" value="both" />
          <el-option label="仅允许下载" value="download_only" />
          <el-option label="不允许下载和二改" value="none" />
        </el-select>
        <div class="tip">下载：其他用户可下载模型文件；二改：其他用户可基于此作品上传二改版本</div>
      </el-form-item>
      <el-form-item label="模型文件" required>
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          accept=".zip,.pngremix,.pngtuber"
          :on-change="handleFileChange"
          :on-exceed="handleExceed"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">将 ZIP 包 / .pngRemix 模型拖到此处，或<em>点击选择</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 ZIP 包或 PNGTuber Plus 导出的 .pngRemix / .pngtuber 文件，最大 50MB，禁止 AI 模型文件</div>
          </template>
        </el-upload>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="handleSubmit">提交上传</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { worksApi } from '../api'

const route = useRoute()
const router = useRouter()
const uploadRef = ref()
const loading = ref(false)
const parentId = ref(route.query.parent || null)
const parentTitle = ref(route.query.title || '')
const isRemix = ref(!!parentId.value)

const form = reactive({
  title: '',
  description: '',
  tags: [],
  source: '',
  permission: 'none',
  file: null,
})

function handleFileChange(file) {
  const allowed = ['.zip', '.pngremix', '.pngtuber']
  const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
  if (!allowed.includes(ext)) {
    ElMessage.error('仅支持 ZIP 或 .pngRemix / .pngtuber 格式文件')
    uploadRef.value?.clearFiles()
    return
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 50MB')
    uploadRef.value?.clearFiles()
    return
  }
  form.file = file.raw
}

function handleExceed() {
  ElMessage.warning('只能上传一个文件')
}

async function handleSubmit() {
  if (!form.title) return ElMessage.warning('请填写标题')
  if (!form.source) return ElMessage.warning('请填写图源自')
  if (!form.file) return ElMessage.warning('请选择模型文件')

  const fd = new FormData()
  fd.append('title', form.title)
  fd.append('description', form.description)
  fd.append('tags', form.tags.join(','))
  fd.append('source', form.source)
  fd.append('allow_remix', form.permission === 'both')
  fd.append('allow_download', form.permission === 'both' || form.permission === 'download_only')
  fd.append('file', form.file)

  loading.value = true
  try {
    const api = isRemix.value ? worksApi.remix : worksApi.create
    if (isRemix.value) fd.append('parent_id', parentId.value)
    const res = await api(fd)
    ElMessage.success('上传成功')
    router.push(`/work/${res.data.id}`)
  } catch (e) {
    // 拦截器已处理错误
  } finally {
    loading.value = false
  }
}

// 二改模式下预填图源自提示
onMounted(() => {
  if (isRemix.value && !form.source) {
    form.source = `基于原作品二创，原作品：${parentTitle.value}`
  }
})
</script>

<style scoped>
.upload-page {
  max-width: 800px;
  margin: 0 auto;
}
.tip {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style>
