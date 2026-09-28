import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/overview' },
    { path: '/overview', name: 'overview', component: () => import('../views/Overview.vue'), meta: { title: '概览' } },
    { path: '/targets', name: 'targets', component: () => import('../views/Targets.vue'), meta: { title: '目标服务器' } },
    { path: '/deploy', name: 'deploy', component: () => import('../views/Deploy.vue'), meta: { title: '部署' } },
    { path: '/topology', name: 'topology', component: () => import('../views/Topology.vue'), meta: { title: '拓扑与扩展' } },
    { path: '/rollback', name: 'rollback', component: () => import('../views/Rollback.vue'), meta: { title: '回退' } },
    { path: '/backup', name: 'backup', component: () => import('../views/Backup.vue'), meta: { title: '备份' } },
    { path: '/monitor', name: 'monitor', component: () => import('../views/Monitor.vue'), meta: { title: '监控' } },
    { path: '/settings', name: 'settings', component: () => import('../views/Settings.vue'), meta: { title: '设置' } },
  ],
})

export default router
