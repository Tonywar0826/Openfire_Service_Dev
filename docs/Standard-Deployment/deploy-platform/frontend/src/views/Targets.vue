<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { targetsApi } from '../api'

interface Target {
  id: string
  name: string
  host: string
  connection_type: 'agent' | 'ssh' | 'docker_tls'
  status: string
}

const targets = ref<Target[]>([])
const showForm = ref(false)
const loading = ref(false)
const testing = ref('')

const connTypes = [
  { value: 'agent', label: 'Agent 模式（推荐）', desc: '客户服务器装 Agent，权限最小' },
  { value: 'ssh', label: 'SSH 直连', desc: '用 SSH 账号远程执行' },
  { value: 'docker_tls', label: 'Docker 远程端口', desc: '连客户 Docker API（TLS）' },
]

const connLabel = (t: string) => connTypes.find((c) => c.value === t)?.label ?? t

const form = ref({
  name: '',
  host: '',
  connection_type: 'agent' as 'agent' | 'ssh' | 'docker_tls',
  agent_url: '',
  agent_token: '',
  ssh_port: 22,
  ssh_user: '',
  ssh_password: '',
  ssh_key: '',
  docker_port: 2376,
  docker_tls_cert: '',
})

async function load() {
  loading.value = true
  try {
    const res = await targetsApi.list()
    targets.value = res.data.targets || []
  } catch (e) {
    console.error('加载目标服务器失败', e)
  } finally {
    loading.value = false
  }
}

async function add() {
  await targetsApi.add({ ...form.value })
  showForm.value = false
  await load()
}

async function remove(name: string) {
  if (!confirm(`确定删除目标服务器「${name}」？`)) return
  await targetsApi.remove(name)
  await load()
}

async function test(name: string) {
  testing.value = name
  try {
    const res = await targetsApi.test(name)
    alert(res.data.message || '连接正常')
  } catch (e) {
    alert('连接测试失败')
  } finally {
    testing.value = ''
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <span class="hint">登记客户服务器，选好连接方式，之后所有一键操作都作用在这台服务器上。</span>
      <button class="btn primary" @click="showForm = !showForm">＋ 添加目标服务器</button>
    </div>

    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="targets.length === 0" class="empty">还没有目标服务器，点右上角「添加目标服务器」登记客户服务器。</div>
    <div v-else class="list">
      <div v-for="t in targets" :key="t.id" class="row">
        <div class="info">
          <div class="name">{{ t.name }}</div>
          <div class="meta">{{ t.host }} · {{ connLabel(t.connection_type) }}</div>
        </div>
        <span class="status" :class="t.status === 'ok' ? 'ok' : ''">{{ t.status === 'ok' ? '已连接' : '未连接' }}</span>
        <button class="btn" :disabled="testing === t.name" @click="test(t.name)">
          {{ testing === t.name ? '测试中…' : '测试连接' }}
        </button>
        <button class="btn danger" @click="remove(t.name)">删除</button>
      </div>
    </div>

    <div v-if="showForm" class="modal" @click.self="showForm = false">
      <div class="modal-body">
        <h3>添加目标服务器</h3>
        <label>名称 <input v-model="form.name" placeholder="如：客户A 生产服务器" /></label>
        <label>地址 <input v-model="form.host" placeholder="IP 或域名" /></label>
        <label>连接方式
          <select v-model="form.connection_type">
            <option v-for="c in connTypes" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
        </label>
        <p class="desc">{{ connLabel(form.connection_type) }}：{{ connTypes.find((c) => c.value === form.connection_type)?.desc }}</p>

        <template v-if="form.connection_type === 'agent'">
          <label>Agent 地址 <input v-model="form.agent_url" placeholder="https://IP:9443" /></label>
          <label>Agent 令牌 <input v-model="form.agent_token" type="password" /></label>
        </template>
        <template v-else-if="form.connection_type === 'ssh'">
          <label>SSH 端口 <input v-model.number="form.ssh_port" type="number" /></label>
          <label>SSH 用户 <input v-model="form.ssh_user" /></label>
          <label>SSH 密码 <input v-model="form.ssh_password" type="password" /></label>
          <label>SSH 密钥（可选） <textarea v-model="form.ssh_key" rows="3" placeholder="粘贴私钥内容"></textarea></label>
        </template>
        <template v-else>
          <label>Docker 端口 <input v-model.number="form.docker_port" type="number" /></label>
          <label>TLS 证书 <textarea v-model="form.docker_tls_cert" rows="3" placeholder="证书内容或路径"></textarea></label>
        </template>

        <div class="modal-actions">
          <button class="btn" @click="showForm = false">取消</button>
          <button class="btn primary" :disabled="!form.name || !form.host" @click="add">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.hint { font-size: 13px; color: var(--muted); }
.list { display: flex; flex-direction: column; gap: 10px; }
.row {
  display: flex; align-items: center; gap: 14px; background: var(--card);
  border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px;
}
.info { flex: 1; }
.name { font-weight: 600; font-size: 15px; }
.meta { font-size: 13px; color: var(--muted); margin-top: 2px; }
.status { font-size: 12px; padding: 3px 10px; border-radius: 12px; background: #f3f4f6; color: var(--muted); }
.status.ok { background: #dcfce7; color: #15803d; }
.empty { color: var(--muted); font-size: 14px; padding: 60px 0; text-align: center; }

.btn {
  border: 1px solid var(--border); background: var(--card); color: var(--text);
  padding: 7px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; transition: .15s;
}
.btn:hover { background: #f3f4f6; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn.primary { background: var(--brand); border-color: var(--brand); color: #fff; }
.btn.primary:hover { background: #4b50b0; }
.btn.danger { color: var(--red); }
.btn.danger:hover { background: #fef2f2; }

.modal { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal-body { background: #fff; border-radius: 14px; padding: 24px; width: 480px; max-height: 85vh; overflow-y: auto; }
.modal-body h3 { margin-bottom: 16px; font-size: 17px; }
.modal-body label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 12px; }
.modal-body input, .modal-body select, .modal-body textarea {
  display: block; width: 100%; margin-top: 5px; padding: 8px 10px; border: 1px solid var(--border);
  border-radius: 8px; font-size: 14px; font-family: inherit; box-sizing: border-box;
}
.modal-body textarea { resize: vertical; }
.desc { font-size: 12px; color: var(--muted); margin: -4px 0 14px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px; }
</style>
