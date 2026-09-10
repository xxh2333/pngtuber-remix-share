<template>
  <div class="register-page">
    <el-card class="register-card">
      <h2 class="title">注册 PNGTuber 分享</h2>
      <el-form :model="form" label-width="0" @submit.prevent="handleRegister">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="handleRegister">注册</el-button>
      </el-form>
      <div class="footer">
        已有账号？<el-link type="primary" @click="$router.push('/login')">去登录</el-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { authApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function handleRegister() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (form.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  loading.value = true
  try {
    const res = await authApi.register(form.username, form.password)
    userStore.setToken(res.data.access)
    const me = await authApi.me()
    userStore.setUser(me.data)
    ElMessage.success('注册成功')
    router.push('/')
  } catch (e) {
    // 拦截器已处理错误
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.register-card {
  width: 380px;
  padding: 20px;
}
.title {
  text-align: center;
  margin: 0 0 24px;
}
.footer {
  text-align: center;
  margin-top: 16px;
}
</style>
