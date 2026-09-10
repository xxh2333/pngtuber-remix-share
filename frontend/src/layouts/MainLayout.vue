<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <el-icon :size="28"><Picture /></el-icon>
        <span>PNGTuber 分享</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="menu"
      >
        <el-menu-item index="/tutorial">
          <el-icon><Reading /></el-icon>
          <span>新手教程</span>
        </el-menu-item>
        <el-menu-item index="/">
          <el-icon><House /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/hot">
          <el-icon><TrendCharts /></el-icon>
          <span>热榜</span>
        </el-menu-item>
        <el-menu-item index="/mine">
          <el-icon><FolderOpened /></el-icon>
          <span>我的作品</span>
        </el-menu-item>
        <el-menu-item index="/upload">
          <el-icon><UploadFilled /></el-icon>
          <span>上传</span>
        </el-menu-item>
        <el-menu-item index="/profile">
          <el-icon><User /></el-icon>
          <span>个人中心</span>
        </el-menu-item>
      </el-menu>
      <div class="user-area" v-if="userStore.isLogin()">
        <el-divider />
        <el-avatar :size="32">{{ userStore.user?.username?.charAt(0) }}</el-avatar>
        <span class="username">{{ userStore.user?.username }}</span>
        <el-button text type="danger" size="small" @click="handleLogout">退出</el-button>
      </div>
      <div class="user-area" v-else>
        <el-divider />
        <el-button type="primary" size="small" @click="$router.push('/login')">登录</el-button>
      </div>
    </el-aside>
    <el-main class="main-content">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'
import { authApi } from '../api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  } catch {}
}

// 登录后拉取用户信息
if (userStore.isLogin() && !userStore.user) {
  authApi.me().then(res => userStore.setUser(res.data)).catch(() => userStore.logout())
}
</script>

<style scoped>
.layout {
  height: 100vh;
}
.sidebar {
  background: #1f2937;
  color: #fff;
  display: flex;
  flex-direction: column;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px;
  font-size: 18px;
  font-weight: bold;
  color: #fff;
}
.menu {
  border-right: none;
  background: transparent;
  flex: 1;
}
.menu :deep(.el-menu-item) {
  color: #d1d5db;
}
.menu :deep(.el-menu-item.is-active) {
  background: #374151;
  color: #fff;
}
.menu :deep(.el-menu-item:hover) {
  background: #374151;
}
.user-area {
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
.username {
  flex: 1;
  color: #fff;
}
.main-content {
  background: #f3f4f6;
  padding: 20px;
  overflow-y: auto;
}
</style>
