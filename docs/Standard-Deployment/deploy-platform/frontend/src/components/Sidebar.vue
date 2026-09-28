<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const menuGroups = [
  {
    group: '总览',
    items: [
      { path: '/overview', icon: '📊', label: '概览' },
      { path: '/targets', icon: '🖥️', label: '目标服务器' },
      { path: '/deploy', icon: '🚀', label: '部署' },
      { path: '/topology', icon: '🕸️', label: '拓扑与扩展' },
    ],
  },
  {
    group: '运维',
    items: [
      { path: '/rollback', icon: '↩️', label: '回退' },
      { path: '/backup', icon: '💾', label: '备份' },
      { path: '/monitor', icon: '📈', label: '监控' },
    ],
  },
  {
    group: '系统',
    items: [{ path: '/settings', icon: '⚙️', label: '设置' }],
  },
]
</script>

<template>
  <aside class="sidebar">
    <div class="logo"><span class="dot">⚡</span> Openfire 部署平台</div>
    <nav>
      <template v-for="g in menuGroups" :key="g.group">
        <div class="group">{{ g.group }}</div>
        <router-link
          v-for="item in g.items"
          :key="item.path"
          :to="item.path"
          class="menu-item"
          :class="{ active: route.path === item.path }"
        >
          <span class="ic">{{ item.icon }}</span>
          {{ item.label }}
        </router-link>
      </template>
    </nav>
    <div class="sidebar-footer">v0.1 · P0 骨架</div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 232px; background: var(--sidebar-bg); color: var(--sidebar-text);
  display: flex; flex-direction: column; flex-shrink: 0;
}
.logo {
  display: flex; align-items: center; gap: 10px; padding: 20px 18px;
  color: #fff; font-weight: 600; font-size: 15px; border-bottom: 1px solid #2a3040;
}
.logo .dot {
  width: 28px; height: 28px; border-radius: 7px; background: var(--brand);
  display: flex; align-items: center; justify-content: center; font-size: 15px; color: #fff;
}
nav { flex: 1; padding: 12px 10px; }
.group { font-size: 11px; color: #5c6573; margin: 16px 10px 6px; letter-spacing: .5px; }
.menu-item {
  display: flex; align-items: center; gap: 11px; padding: 10px 12px;
  border-radius: 8px; cursor: pointer; font-size: 14px; margin-bottom: 2px;
  color: var(--sidebar-text); text-decoration: none; transition: background .15s;
}
.menu-item:hover { background: #2a3040; color: #fff; }
.menu-item.active { background: var(--brand); color: #fff; }
.menu-item .ic { width: 18px; text-align: center; font-size: 15px; }
.sidebar-footer { padding: 14px 18px; border-top: 1px solid #2a3040; font-size: 12px; color: #5c6573; }
</style>
