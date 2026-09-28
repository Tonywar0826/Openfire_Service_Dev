<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { deployApi, targetsApi } from '../api'

interface Target { name: string; host: string; connection_type: string }

const step = ref(1)
const targets = ref<Target[]>([])
const deploying = ref(false)
const result = ref<Record<string, any> | null>(null)
const error = ref('')

const form = ref({
  scale: 'small' as string,
  target_name: '',
  domain: '',
  admin_password: '',
  db_password: '',
  lan_ip: '',
  coturn_port: 13478,
  coturn_user: 'collab',
  coturn_password: 'collab@123',
  openfire_instances: 1,
  coturn_instances: 1,
})

// 可选参数展开控制（coturn 三项默认折叠）
const showAdvanced = ref(false)

const scaleOptions = [
  { value: 'small', label: '小规模 (small)', desc: '1 Openfire + 1 数据库 + 1 coturn' },
  { value: 'medium', label: '中规模 (medium)', desc: '2 Openfire + 主从数据库 + 2 coturn' },
  { value: 'large', label: '大规模 (large)', desc: '3+ Openfire + Patroni 高可用 + 3 coturn' },
  { value: 'custom', label: '自定义 (custom)', desc: '自由指定服务数量' },
]

const isCustom = computed(() => form.value.scale === 'custom')
// 四个必填参数齐全才可部署
const paramsReady = computed(() =>
  form.value.domain.trim() && form.value.admin_password && form.value.db_password && form.value.lan_ip.trim()
)

onMounted(async () => {
  try {
    const res = await targetsApi.list()
    targets.value = res.data.targets || []
  } catch {
    /* 忽略 */
  }
})

async function doDeploy() {
  deploying.value = true
  error.value = ''
  result.value = null
  try {
    const payload: Record<string, unknown> = {
      scale: form.value.scale,
      domain: form.value.domain.trim(),
      admin_password: form.value.admin_password,
      db_password: form.value.db_password,
      lan_ip: form.value.lan_ip.trim(),
      coturn_port: form.value.coturn_port,
      coturn_user: form.value.coturn_user,
      coturn_password: form.value.coturn_password,
    }
    if (form.value.target_name) payload.target_name = form.value.target_name
    if (isCustom.value) {
      payload.openfire_instances = form.value.openfire_instances
      payload.coturn_instances = form.value.coturn_instances
    }
    const res = await deployApi.deploy(payload)
    result.value = res.data
    step.value = 4
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || '部署失败'
  } finally {
    deploying.value = false
  }
}

// 状态图标映射
function statusText(s: string) {
  return { ok: '✅', fail: '❌', warn: '⚠️', pending: '⏳' }[s] || '·'
}

// 自检项按层分组（L1/L2/L3/L4）
const layerGroups = computed(() => {
  const items = (result.value?.selfcheck as any[]) || []
  const order = ['L1', 'L2', 'L3', 'L4']
  const groups: { name: string; items: any[] }[] = []
  for (const l of order) {
    const its = items.filter((i) => i.layer === l)
    if (its.length) groups.push({ name: l, items: its })
  }
  return groups
})
</script>

<template>
  <div class="page">
    <div class="steps">
      <template v-for="(s, i) in ['选择规模', '填写参数', '确认', '结果']" :key="s">
        <div class="step" :class="{ active: step === i + 1, done: step > i + 1 }">
          <span class="num">{{ i + 1 }}</span>{{ s }}
        </div>
        <div v-if="i < 3" class="line" :class="{ done: step > i + 1 }"></div>
      </template>
    </div>

    <!-- 第 1 步：选规模 -->
    <div v-if="step === 1" class="panel">
      <div class="scales">
        <div
          v-for="s in scaleOptions" :key="s.value"
          class="scale-card" :class="{ selected: form.scale === s.value }"
          @click="form.scale = s.value"
        >
          <div class="scale-label">{{ s.label }}</div>
          <div class="scale-desc">{{ s.desc }}</div>
        </div>
      </div>
      <div class="actions">
        <button class="btn primary" @click="step = 2">下一步</button>
      </div>
    </div>

    <!-- 第 2 步：填参数 -->
    <div v-else-if="step === 2" class="panel">
      <label>目标服务器（留空 = 本机部署验证）
        <select v-model="form.target_name">
          <option value="">本机（LocalConnector）</option>
          <option v-for="t in targets" :key="t.name" :value="t.name">{{ t.name }}（{{ t.host }} · {{ t.connection_type }}）</option>
        </select>
      </label>
      <label><span class="req">*</span> XMPP 域名（客户提供）
        <input v-model="form.domain" placeholder="如 im.example.com" />
      </label>
      <label><span class="req">*</span> Openfire admin 密码
        <input v-model="form.admin_password" type="password" placeholder="管理员登录密码" />
      </label>
      <label><span class="req">*</span> Openfire 数据库密码
        <input v-model="form.db_password" type="password" placeholder="数据库密码" />
      </label>
      <label><span class="req">*</span> 局域网 IP（文件上传/coturn 转发地址）
        <input v-model="form.lan_ip" placeholder="如 192.168.31.19（ipconfig 查看）" />
      </label>

      <!-- 可选：coturn（音视频），默认与协作平台一致，一般无需改 -->
      <div class="advanced">
        <button type="button" class="advanced-toggle" @click="showAdvanced = !showAdvanced">
          <span>{{ showAdvanced ? '▾' : '▸' }} 可选：coturn 音视频中继配置</span>
          <span class="hint">（默认值与协作平台一致，一般无需改）</span>
        </button>
        <div v-if="showAdvanced" class="advanced-body">
          <label>coturn 端口
            <input v-model.number="form.coturn_port" type="number" min="1024" max="65535" />
            <small class="tip">前端音视频连接 coturn 的端口，需与协作平台前端一致，默认 13478</small>
          </label>
          <label>coturn 用户名
            <input v-model="form.coturn_user" />
            <small class="tip">TURN 静态用户名，默认 collab</small>
          </label>
          <label>coturn 密码
            <input v-model="form.coturn_password" type="password" />
            <small class="tip">TURN 静态密码，默认 collab@123</small>
          </label>
        </div>
      </div>

      <template v-if="isCustom">
        <label>Openfire 实例数 <input v-model.number="form.openfire_instances" type="number" min="1" max="50" /></label>
        <label>coturn 实例数 <input v-model.number="form.coturn_instances" type="number" min="1" max="50" /></label>
      </template>

      <div class="actions">
        <button class="btn" @click="step = 1">上一步</button>
        <button class="btn primary" :disabled="!paramsReady" @click="step = 3">下一步</button>
      </div>
    </div>

    <!-- 第 3 步：确认 -->
    <div v-else-if="step === 3" class="panel">
      <div class="summary">
        <div class="sum-row"><span>规模</span><b>{{ form.scale }}</b></div>
        <div class="sum-row"><span>目标服务器</span><b>{{ form.target_name || '本机' }}</b></div>
        <div class="sum-row"><span>XMPP 域名</span><b>{{ form.domain }}</b></div>
        <div class="sum-row"><span>admin 密码</span><b>••••••</b></div>
        <div class="sum-row"><span>数据库密码</span><b>••••••</b></div>
        <div class="sum-row"><span>局域网 IP</span><b>{{ form.lan_ip }}</b></div>
        <template v-if="isCustom">
          <div class="sum-row"><span>Openfire 实例数</span><b>{{ form.openfire_instances }}</b></div>
          <div class="sum-row"><span>coturn 实例数</span><b>{{ form.coturn_instances }}</b></div>
        </template>
      </div>
      <div class="actions">
        <button class="btn" @click="step = 2">上一步</button>
        <button class="btn primary" :disabled="deploying" @click="doDeploy">
          {{ deploying ? '部署中…' : '🚀 一键部署' }}
        </button>
      </div>
    </div>

    <!-- 第 4 步：结果 -->
    <div v-else class="panel">
      <div v-if="error" class="result error">❌ {{ error }}</div>
      <div v-else-if="result" class="result-body">
        <!-- 部署概览 -->
        <div class="result" :class="result.status === 'success' ? 'ok' : 'error'">
          <div class="result-title">{{ result.status === 'success' ? '✅ 部署成功' : '❌ 部署失败' }}</div>
          <div class="sum-row"><span>项目</span><b>{{ result.project }}</b></div>
          <div v-if="result.plugins" class="sum-row"><span>插件</span><b>{{ result.plugins.join(', ') }}</b></div>
          <div class="sum-row"><span>配置初始化</span><b>{{ result.tables_ready ? '完成' : '未完成' }}</b></div>
        </div>

        <!-- 配置同步清单 -->
        <div v-if="result.config_sync" class="section">
          <div class="section-title">② 配置同步清单 <span class="tag">逐项校验 · 名称 + 概要说明</span></div>
          <div v-for="(c, i) in result.config_sync" :key="i" class="cfg-item">
            <span class="status" :class="c.status">{{ statusText(c.status) }}</span>
            <div class="cfg-body">
              <div class="cfg-name">{{ c.name }}</div>
              <div class="cfg-desc">{{ c.description }}</div>
              <div class="cfg-meta">
                <span class="dir">{{ c.direction }}</span>
                <span class="val">{{ c.value }}</span>
              </div>
              <div class="cfg-detail">{{ c.detail }}</div>
            </div>
          </div>
        </div>

        <!-- 自检清单 -->
        <div v-if="result.selfcheck" class="section">
          <div class="section-title">③ 自检校验清单 <span class="tag">容器 → 服务 → 功能 → Bug 回归</span></div>
          <div v-if="result.selfcheck_summary" class="check-summary">
            <span class="cs ok">✅ 通过 {{ result.selfcheck_summary.ok }}</span>
            <span class="cs fail">❌ 失败 {{ result.selfcheck_summary.fail }}</span>
            <span class="cs warn">⚠️ 警告 {{ result.selfcheck_summary.warn }}</span>
            <span class="cs pending">⏳ 待核验 {{ result.selfcheck_summary.pending }}</span>
          </div>
          <div v-for="(layer, li) in layerGroups" :key="li" class="layer">
            <div class="layer-head">{{ layer.name }}<span class="layer-count">{{ layer.items.length }} 项</span></div>
            <div v-for="(c, ci) in layer.items" :key="ci" class="check-item">
              <span class="status" :class="c.status">{{ statusText(c.status) }}</span>
              <span class="check-name">{{ c.name }}</span>
              <span v-if="c.bugs && c.bugs !== '—'" class="bug">{{ c.bugs }}</span>
              <span class="check-detail">{{ c.detail }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="actions">
        <button class="btn primary" @click="step = 1">再次部署</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.steps { display: flex; align-items: center; margin-bottom: 24px; }
.step { display: flex; align-items: center; gap: 7px; font-size: 14px; color: var(--muted); }
.step .num {
  width: 24px; height: 24px; border-radius: 50%; background: #e5e7eb; color: var(--muted);
  display: flex; align-items: center; justify-content: center; font-size: 13px;
}
.step.active { color: var(--text); font-weight: 600; }
.step.active .num { background: var(--brand); color: #fff; }
.step.done .num { background: #dcfce7; color: #15803d; }
.line { flex: 1; height: 2px; background: #e5e7eb; margin: 0 12px; }
.line.done { background: #86efac; }

.panel { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }
.scales { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-bottom: 20px; }
.scale-card {
  border: 2px solid var(--border); border-radius: 10px; padding: 16px; cursor: pointer; transition: .15s;
}
.scale-card:hover { border-color: #c7cbf5; }
.scale-card.selected { border-color: var(--brand); background: #f5f6ff; }
.scale-label { font-weight: 600; font-size: 15px; }
.scale-desc { font-size: 13px; color: var(--muted); margin-top: 5px; }

label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 14px; }
.req { color: var(--red); margin-right: 2px; }
input, select {
  display: block; width: 100%; margin-top: 5px; padding: 9px 11px; border: 1px solid var(--border);
  border-radius: 8px; font-size: 14px; font-family: inherit; box-sizing: border-box;
}

.summary { margin-bottom: 20px; }
.sum-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
.sum-row span { color: var(--muted); }
.sum-row b { font-weight: 600; }

.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px; }
.btn {
  border: 1px solid var(--border); background: var(--card); color: var(--text);
  padding: 9px 18px; border-radius: 8px; cursor: pointer; font-size: 14px; transition: .15s;
}
.btn:hover { background: #f3f4f6; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn.primary { background: var(--brand); border-color: var(--brand); color: #fff; }
.btn.primary:hover { background: #4b50b0; }

.result { border-radius: 10px; padding: 18px; font-size: 14px; }
.result.ok { background: #f0fdf4; border: 1px solid #bbf7d0; }
.result.error { background: #fef2f2; border: 1px solid #fecaca; }
.result-title { font-weight: 700; font-size: 16px; margin-bottom: 12px; }
.output {
  background: #1f2430; color: #d1d5db; border-radius: 8px; padding: 12px; font-size: 12px;
  max-height: 260px; overflow-y: auto; margin-top: 12px; white-space: pre-wrap; word-break: break-all;
}

/* ---- 可选参数折叠区 ---- */
.advanced { margin-bottom: 14px; }
.advanced-toggle {
  display: flex; align-items: center; gap: 8px; width: 100%; background: #f8fafc;
  border: 1px dashed var(--border); border-radius: 8px; padding: 9px 12px;
  cursor: pointer; font-size: 13px; color: var(--text); text-align: left;
}
.advanced-toggle .hint { color: var(--muted); font-size: 12px; }
.advanced-body { margin-top: 10px; padding: 4px 2px; }
small.tip { display: block; color: var(--muted); font-size: 12px; margin-top: 4px; }

/* ---- 结果页：配置同步 + 自检 ---- */
.result-body { display: flex; flex-direction: column; gap: 18px; }
.section { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.section-title {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; font-weight: 600; font-size: 14px;
  background: #f8fafc; border-bottom: 1px solid var(--border);
}
.section-title .tag { font-size: 12px; color: var(--muted); font-weight: 400; }

.status {
  width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 12px;
}
.status.ok { background: #dcfce7; color: #15803d; }
.status.fail { background: #fee2e2; color: #b91c1c; }
.status.warn { background: #fef3c7; color: #b45309; }
.status.pending { background: #e0e7ff; color: #4338ca; }

.cfg-item { display: flex; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.cfg-item:last-child { border-bottom: none; }
.cfg-body { flex: 1; min-width: 0; }
.cfg-name { font-family: ui-monospace, Menlo, monospace; font-size: 13px; font-weight: 600; color: #2563eb; }
.cfg-desc { font-size: 12.5px; color: var(--muted); margin-top: 3px; }
.cfg-meta { display: flex; gap: 10px; margin-top: 6px; align-items: center; }
.cfg-meta .dir { font-size: 11px; color: var(--muted); background: #eef2ff; padding: 2px 8px; border-radius: 4px; }
.cfg-meta .val { font-size: 11px; font-family: ui-monospace, Menlo, monospace; color: #475569; word-break: break-all; }
.cfg-detail { font-size: 12px; color: #64748b; margin-top: 4px; }

.check-summary { display: flex; gap: 10px; flex-wrap: wrap; padding: 10px 16px; border-bottom: 1px solid var(--border); }
.check-summary .cs { font-size: 13px; font-weight: 600; padding: 3px 10px; border-radius: 6px; }
.cs.ok { background: #dcfce7; color: #15803d; }
.cs.fail { background: #fee2e2; color: #b91c1c; }
.cs.warn { background: #fef3c7; color: #b45309; }
.cs.pending { background: #e0e7ff; color: #4338ca; }

.layer { border-bottom: 1px solid var(--border); }
.layer:last-child { border-bottom: none; }
.layer-head {
  display: flex; align-items: center; gap: 8px; padding: 9px 16px;
  font-weight: 600; font-size: 13px; background: #f8fafc;
}
.layer-count { margin-left: auto; font-size: 12px; color: var(--muted); font-weight: 400; }
.check-item { display: flex; align-items: flex-start; gap: 10px; padding: 9px 16px 9px 32px; border-top: 1px solid #f1f5f9; }
.check-name { font-size: 13px; font-weight: 500; flex-shrink: 0; }
.check-item .bug { font-size: 11px; color: var(--muted); font-family: ui-monospace, Menlo, monospace; flex-shrink: 0; }
.check-detail { flex: 1; font-size: 12px; color: #64748b; text-align: right; word-break: break-all; }
</style>
