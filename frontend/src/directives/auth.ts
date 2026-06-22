/**
 * v-auth 指令 — 基于角色的元素显隐控制。
 *
 * 用法：
 *   v-auth="'LEADER'"              -- 当前用户 >= LEADER 时渲染
 *   v-auth="'ADMIN'"               -- 当前用户 >= ADMIN 时渲染
 *   v-auth="'MEMBER'"              -- 所有登录用户都渲染
 *   v-auth:hidden="true"           -- 权限不足时隐藏（display:none）而非移除
 *
 * 原理：权限不足时直接从 DOM 移除元素（或隐藏），确保按钮/菜单不会被操作到。
 */
import type { Directive, DirectiveBinding } from 'vue'
import { useAuthStore } from '@/stores/auth'

const ROLE_HIERARCHY: Record<string, number> = {
  MEMBER: 0,
  LEADER: 1,
  ADMIN: 2,
}

function checkRole(userRole: string, isSuperuser: boolean, minRole: string): boolean {
  if (!minRole) return true
  const userLevel = isSuperuser ? ROLE_HIERARCHY['ADMIN'] : (ROLE_HIERARCHY[userRole] ?? 0)
  return userLevel >= (ROLE_HIERARCHY[minRole] ?? 0)
}

export const authDirective: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    const auth = useAuthStore()
    const minRole = String(binding.value || 'MEMBER')
    const hidden = binding.modifiers?.hidden

    const hasPermission = auth.user
      ? checkRole(auth.user.role, auth.user.is_superuser, minRole)
      : false

    if (!hasPermission) {
      if (hidden) {
        el.style.display = 'none'
        el.__vAuthHidden = true
      } else {
        el.parentNode?.removeChild(el)
      }
    }
  },

  updated(el: HTMLElement, binding: DirectiveBinding) {
    const auth = useAuthStore()
    const minRole = String(binding.value || 'MEMBER')
    const hidden = binding.modifiers?.hidden

    const hasPermission = auth.user
      ? checkRole(auth.user.role, auth.user.is_superuser, minRole)
      : false

    if (!hasPermission) {
      if (hidden) {
        el.style.display = 'none'
        el.__vAuthHidden = true
      } else {
        el.parentNode?.removeChild(el)
      }
    } else if (el.__vAuthHidden) {
      el.style.display = ''
      el.__vAuthHidden = false
    }
  },
}

declare global {
  interface HTMLElement {
    __vAuthHidden?: boolean
  }
}
