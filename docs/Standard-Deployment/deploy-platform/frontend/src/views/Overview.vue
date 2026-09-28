<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { statusApi } from '../api'

interface Status {
  health: string
  version: string
  targets: number
  deployed: boolean
  instances: number
  online_users: number
  database: string
}

const status = ref<Status | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await statusApi.status()
    status.value = res.data
  } catch (e) {
    console.error('加载状态失败', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <div v-if="loading" class="placeholder">加载中…</div>
    <template v-else>
      <div class="cards">
        <div class="card"><div class="label">目标服务器</div><div class="value">{{ status?.targets ?? '—' }}</div></div>
        <div class="card"><div class="label">Openfire 实例</div><div class="value">{{ status?.instances ?? '—' }}</div></div>
        <div class="card"><div class="label">在线用户</div><div class="value">{{ status?.online_users ?? '—' }}</div></div>
        <div class="card"><div class="label">数据库</div><div class="value sm">{{ status?.database ?? '—' }}</div></div>
      </div>

      <div v-if="status && !status.deployed" class="banner">
        <div class="banner-title">尚未部署 Openfire</div>
        <div class="banner-text">第一步：到「目标服务器」登记客户服务器；第二步：到「部署」一键部署。</div>
      </div>

      <div class="meta">平台版本 v{{ status?.version ?? '—' }} · 运行状态 {{ status?.health === 'ok' ? '正常' : '异常' }}</div>
    </template>
  </div>
</template>

<style scoped>
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
.card .label { font-size: 13px; color: var(--muted); margin-bottom: 8px; }
.card .value { font-size: 26px; font-weight: 700; }
.card .value.sm { font-size: 18px; }
.banner { background: #eef0ff; border: 1px solid #d7daf5; border-radius: 12px; padding: 16px 18px; margin-bottom: 20px; }
.banner-title { font-weight: 600; color: var(--brand); margin-bottom: 4px; }
.banner-text { font-size: 13px; color: var(--muted); }
.meta { font-size: 12px; color: var(--muted); }
.placeholder { color: var(--muted); font-size: 14px; padding: 40px; text-align: center; }
</style>
