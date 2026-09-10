<template>
  <div class="hot-page">
    <h2 class="page-title">🔥 作品热榜</h2>

    <div class="filters">
      <el-radio-group v-model="period" @change="loadHot">
        <el-radio-button value="all">总榜</el-radio-button>
        <el-radio-button value="month">月榜</el-radio-button>
        <el-radio-button value="week">周榜</el-radio-button>
        <el-radio-button value="day">日榜</el-radio-button>
      </el-radio-group>

      <el-radio-group v-model="sort" @change="loadHot">
        <el-radio-button value="composite">综合</el-radio-button>
        <el-radio-button value="views">浏览</el-radio-button>
        <el-radio-button value="likes">点赞</el-radio-button>
      </el-radio-group>
    </div>

    <el-table :data="works" v-loading="loading" stripe>
      <el-table-column label="排名" width="80" align="center">
        <template #default="{ $index }">
          <span :class="['rank', `rank-${$index + 1}`]">{{ $index + 1 }}</span>
        </template>
      </el-table-column>
      <el-table-column label="预览" width="100">
        <template #default="{ row }">
          <img :src="previewUrl(row.preview_path)" class="thumb" />
        </template>
      </el-table-column>
      <el-table-column label="作品" prop="title">
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/work/${row.id}`)">{{ row.title }}</el-link>
          <div class="author">by {{ row.author.username }}</div>
        </template>
      </el-table-column>
      <el-table-column label="浏览" prop="views" width="100" align="center" />
      <el-table-column label="点赞" prop="likes" width="100" align="center" />
      <el-table-column label="标签" width="200">
        <template #default="{ row }">
          <el-tag v-for="t in row.tags" :key="t.id" size="small" class="tag">{{ t.name }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadHot"
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
const pageSize = 50
const loading = ref(false)
const period = ref('all')
const sort = ref('composite')

function previewUrl(path) {
  return path ? `/media/${path}` : ''
}

async function loadHot() {
  loading.value = true
  try {
    const res = await worksApi.hot({ page: page.value, page_size: pageSize, period: period.value, sort: sort.value })
    works.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

onMounted(loadHot)
</script>

<style scoped>
.hot-page {
  max-width: 1100px;
  margin: 0 auto;
}
.page-title {
  margin-top: 0;
}
.filters {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}
.rank {
  font-weight: bold;
  font-size: 18px;
}
.rank-1 { color: #f59e0b; }
.rank-2 { color: #9ca3af; }
.rank-3 { color: #cd7f32; }
.thumb {
  width: 60px;
  height: 60px;
  object-fit: contain;
  border-radius: 4px;
}
.author {
  font-size: 12px;
  color: #999;
}
.tag {
  margin-right: 4px;
}
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
