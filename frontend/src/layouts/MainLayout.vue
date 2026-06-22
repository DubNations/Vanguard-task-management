<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePermission } from '@/composables/usePermission'
import { useNotificationStore } from '@/stores/notification'
import { ElMessageBox } from 'element-plus'
import { timeAgo } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const perm = usePermission()
const notifStore = useNotificationStore()

const username = computed(() => auth.username)
const breadcrumbParent = computed(() => (route.meta as any).parent as { path: string; title: string } | undefined)

const isCollapse = ref(localStorage.getItem('sidebar_collapse') === 'true')

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
  localStorage.setItem('sidebar_collapse', String(isCollapse.value))
}

// 普通菜单项 — 根据路由 minRole 动态过滤
const menuItems = computed(() => {
  const all = [
    { index: '/', icon: 'DataAnalysis', label: '工作台', minRole: undefined },
    { index: '/tasks', icon: 'List', label: '任务管理', minRole: undefined },
    { index: '/tasks/kanban', icon: 'Grid', label: '看板视图', minRole: undefined },
    { index: '/tasks/timeline', icon: 'Clock', label: '时间线', minRole: undefined },
    { index: '/tasks/calendar', icon: 'Calendar', label: '日历视图', minRole: undefined },
    { index: '/points', icon: 'Trophy', label: '积分排行', minRole: undefined },
    { index: '/imports', icon: 'Upload', label: '任务导入', minRole: 'LEADER' },
    { index: '/exports', icon: 'Download', label: '任务导出', minRole: undefined },
  ]
  if (!auth.user) return []
  return all.filter(item => perm.hasRole(item.minRole as any || 'MEMBER'))
})

// 管理后台菜单项 — 每个菜单对应独立的权限函数
const adminItems = computed(() => {
  if (!auth.user) return []
  const items = [
    { index: '/admin/users', icon: 'User', label: '用户管理', visible: perm.canManageUsers() },
    { index: '/admin/audit', icon: 'Document', label: '操作日志', visible: perm.canViewAuditLog() },
    { index: '/admin/teams', icon: 'OfficeBuilding', label: '团队管理', visible: perm.canManageTeams() },
    { index: '/admin/points', icon: 'Setting', label: '积分配置', visible: perm.canManagePointsConfig() },
  ]
  return items.filter(item => item.visible)
})

const hasAdminMenu = computed(() => adminItems.value.length > 0)

// 通知
const showNotif = ref(false)
onMounted(() => {
  notifStore.fetchNotifications().catch(() => {})
})

const handleLogout = async () => {
  await ElMessageBox.confirm('确定退出登录？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await auth.logout()
  router.push('/login')
}

const handleUserCommand = (cmd: string) => {
  if (cmd === 'logout') handleLogout()
  else if (cmd === 'profile') router.push('/profile')
  else if (cmd === 'password') router.push('/profile?tab=password')
}
</script>

<template>
  <el-container class="layout-container">
    <!-- Sidebar -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <div class="logo">
        <el-icon size="24" color="#409eff"><Trophy /></el-icon>
        <span v-show="!isCollapse" class="logo-text">尖兵部队</span>
      </div>

      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        router
        class="sidebar-menu"
        background-color="#1d2b3a"
        text-color="#ffffffb3"
        active-text-color="#ffffff"
      >
        <el-menu-item v-for="item in menuItems" :key="item.index" :index="item.index">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.label }}</template>
        </el-menu-item>

        <template v-if="hasAdminMenu">
          <el-sub-menu index="admin-group" v-if="!isCollapse">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item
              v-for="item in adminItems"
              :key="item.index"
              :index="item.index"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>{{ item.label }}</template>
            </el-menu-item>
          </el-sub-menu>
          <template v-else>
            <el-menu-item
              v-for="item in adminItems"
              :key="item.index"
              :index="item.index"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>{{ item.label }}</template>
            </el-menu-item>
          </template>
        </template>
      </el-menu>

      <div class="collapse-btn" @click="toggleCollapse">
        <el-icon :size="16">
          <component :is="isCollapse ? 'Expand' : 'Fold'" />
        </el-icon>
      </div>
    </el-aside>

    <!-- Main content -->
    <el-container>
      <!-- Header -->
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="breadcrumbParent" :to="{ path: breadcrumbParent.path }">
              {{ breadcrumbParent.title }}
            </el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">
              {{ route.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 通知铃铛 -->
          <el-popover
            v-model:visible="showNotif"
            placement="bottom-end"
            :width="360"
            trigger="click"
          >
            <template #reference>
              <el-badge :value="notifStore.unreadCount" :hidden="notifStore.unreadCount === 0" class="notif-badge">
                <el-icon :size="20" class="notif-icon" @click="showNotif = !showNotif">
                  <Bell />
                </el-icon>
              </el-badge>
            </template>
            <div class="notif-panel">
              <div class="notif-header">
                <strong>通知</strong>
                <el-button link type="primary" size="small" @click="notifStore.markAllRead()">全部已读</el-button>
              </div>
              <div class="notif-list">
                <div
                  v-for="n in notifStore.notifications.slice(0, 10)"
                  :key="n.id"
                  :class="['notif-item', { unread: !n.is_read }]"
                  @click="notifStore.markRead(n.id); $router.push(n.task_id ? `/tasks/${n.task_id}` : '/')"
                >
                  <div class="notif-title">{{ n.title }}</div>
                  <div class="notif-time">{{ timeAgo(n.created_at) }}</div>
                </div>
                <el-empty v-if="!notifStore.notifications.length" description="暂无通知" :image-size="60" />
              </div>
            </div>
          </el-popover>

          <!-- 用户菜单 -->
          <el-dropdown @command="handleUserCommand">
            <span class="user-info">
              <el-avatar :size="28" style="background: #409eff">
                {{ username.charAt(0).toUpperCase() }}
              </el-avatar>
              <span class="user-name">{{ username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item command="password">
                  <el-icon><Lock /></el-icon>修改密码
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- Content -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped lang="scss">
.layout-container {
  height: 100vh;
}

.sidebar {
  background: #1d2b3a;
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.3s ease;
  display: flex;
  flex-direction: column;

  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: white;
    font-size: 18px;
    font-weight: 600;
    border-bottom: 1px solid #ffffff1a;
    flex-shrink: 0;
  }

  .logo-text {
    white-space: nowrap;
  }
}

.sidebar-menu {
  border-right: none;
  flex: 1;

  :deep(.el-menu-item.is-active) {
    background-color: #409eff !important;
    position: relative;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 3px;
      background: #67c23a;
      border-radius: 0 2px 2px 0;
    }
  }
}

.collapse-btn {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffffb3;
  cursor: pointer;
  border-top: 1px solid #ffffff1a;
  transition: all 0.2s;
  flex-shrink: 0;

  &:hover {
    color: #fff;
    background: #ffffff0d;
  }
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  padding: 0 20px;
  z-index: 10;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.notif-badge {
  cursor: pointer;
}

.notif-icon {
  color: #606266;
  cursor: pointer;
  transition: color 0.2s;

  &:hover {
    color: #409eff;
  }
}

.notif-panel {
  .notif-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 10px;
    border-bottom: 1px solid #f0f0f0;
  }

  .notif-list {
    max-height: 320px;
    overflow-y: auto;
  }

  .notif-item {
    padding: 10px 8px;
    border-bottom: 1px solid #f8f8f8;
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: #f5f7fa;
    }

    &.unread {
      background: #ecf5ff;
    }

    .notif-title {
      font-size: 13px;
      color: #303133;
      margin-bottom: 4px;
    }

    .notif-time {
      font-size: 11px;
      color: #909399;
    }
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;

  .user-name {
    font-size: 14px;
    color: #606266;
  }
}

.main-content {
  background: #f5f7fa;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
