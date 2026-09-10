<template>
  <div class="profile-page">
    <el-card>
      <h2>个人中心</h2>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ user?.username }}</el-descriptions-item>
        <el-descriptions-item label="用户ID">{{ user?.id }}</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <h3>账号操作</h3>
      <el-alert
        title="注销账号将软删除您的账号和所有作品，使用相同用户名重新注册可恢复数据"
        type="warning"
        :closable="false"
        style="margin-bottom: 16px"
      />
      <el-button type="danger" :loading="deactivating" @click="handleDeactivate">注销账号</el-button>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { authApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const deactivating = ref(false)
const user = computed(() => userStore.user)

async function handleDeactivate() {
  try {
    await ElMessageBox.confirm(
      '确定要注销账号吗？注销后账号和作品将被软删除，可通过相同用户名重新注册恢复。',
      '注销账号',
      { type: 'warning', confirmButtonText: '确认注销', confirmButtonType: 'danger' }
    )
    deactivating.value = true
    await authApi.deactivate()
    ElMessage.success('账号已注销')
    userStore.logout()
    router.push('/login')
  } catch (e) {
    if (e !== 'cancel') {
      // 错误已由拦截器处理
    }
  } finally {
    deactivating.value = false
  }
}
</script>

<style scoped>
.profile-page {
  max-width: 600px;
  margin: 0 auto;
}
</style>
