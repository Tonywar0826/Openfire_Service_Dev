# Openfire 部署管理平台 - 前端
# dist 在宿主机预构建（npm run build），这里只做 nginx 托管 + 反代后端
FROM nginx:1.27-alpine
COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
