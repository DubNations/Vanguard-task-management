---
name: vue-frontend
description: Use when writing or reviewing Vue 3 frontend code. Covers Composition API patterns, TypeScript integration, Element Plus usage, Pinia store patterns, and common Vue pitfalls. Use when working with .vue files, stores, composables, or frontend API calls.
---

# Vue 3 + TypeScript Best Practices

## Component Patterns
- Always use `<script setup lang="ts">` for new components
- Use `defineProps<{}>()` and `defineEmits<{}>()` with TypeScript generics
- Prefer `computed()` over methods for derived state
- Use `ref()` for primitives, `reactive()` for objects (but prefer `ref()` for consistency)
- Use `toRefs()` when destructuring reactive objects to maintain reactivity

## TypeScript
- Define interfaces in `stores/*.ts` or `types/*.ts`, not inline
- Use `as const` for literal type arrays
- Avoid `any` — use `unknown` and type Narrowing
- Use `NonNullable<T>` to strip null/undefined from union types

## State Management (Pinia)
- Keep stores focused: one store per domain (tasks, auth, notifications)
- Use `getters` for computed state, `actions` for async operations
- Never mutate state outside of actions
- Use `storeToRefs()` for reactive store properties in components

## API Calls
- Centralize API instance in `api/index.ts` with interceptors
- Handle errors at the interceptor level, not in every component
- Use TypeScript interfaces for API request/response types
- Never store tokens in localStorage in production — use httpOnly cookies

## Element Plus
- Import components on-demand, not globally: `import { ElMessage } from 'element-plus'`
- Use `v-loading` directive instead of manual loading state for async data
- Use `el-form` with `:model` and `rules` for form validation
- Use `el-table` with `stripe` and `size="small"` for data tables
- Use `el-dialog` with `destroy-on-close` to reset form state

## Common Pitfalls
- Never use `v-if` and `v-for` on the same element — `v-for` has higher priority
- Use `key` prop on all `v-for` lists
- Don't mutate props — use `emit()` or computed properties
- Use `watch()` with `{ immediate: true }` for initial data fetch
- Clean up event listeners and timers in `onUnmounted()`
- Use `nextTick()` when you need DOM to update after state change

## Performance
- Use `defineAsyncComponent()` for route-level code splitting
- Use `v-memo` for expensive list rendering
- Lazy-load images with `loading="lazy"`
- Debounce search inputs with `useDebounceFn()` from VueUse
- Avoid re-creating objects/arrays in templates — use `computed()` to cache
