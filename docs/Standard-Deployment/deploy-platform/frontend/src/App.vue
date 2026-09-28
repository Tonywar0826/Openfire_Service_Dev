<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import Sidebar from './components/Sidebar.vue'

const route = useRoute()
const pageTitle = computed(() => (route.meta.title as string) || '')
</script>

<template>
  <div class="layout">
    <Sidebar />
    <div class="main">
      <header class="topbar">
        <span class="env">Openfire 本地环境</span>
        <span class="tag">规模：小 (small)</span>
        <div class="header-right">
          <span class="health"><span class="dot"></span> 运行正常</span>
        </div>
      </header>
      <main class="content">
        <div class="page-title">{{ pageTitle }}</div>
        <router-view />
      </main>
    </div>
  </div>
</template>

<style>
:root {
  --brand: #5b5fc7;
  --sidebar-bg: #1f2430;
  --sidebar-text: #9aa3b2;
  --bg: #f5f6f8;
  --card: #ffffff;
  --border: #e6e8ec;
  --text: #1f2430;
  --muted: #6b7280;
  --green: #22c55e;
  --amber: #f59e0b;
  --red: #ef4444;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--text); }
.layout { display: flex; height: 100vh; overflow: hidden; }
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar {
  height: 60px; background: var(--card); border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 24px; gap: 14px; flex-shrink: 0;
}
.topbar .env { font-weight: 600; font-size: 15px; }
.tag { font-size: 12px; padding: 3px 10px; border-radius: 12px; background: #eef0ff; color: var(--brand); font-weight: 500; }
.header-right { margin-left: auto; display: flex; align-items: center; gap: 16px; }
.health { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--muted); }
.health .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 3px rgba(34, 197, 94, .15); }
.content { flex: 1; overflow-y: auto; padding: 24px; }
.page-title { font-size: 20px; font-weight: 700; margin-bottom: 16px; }
</style>
