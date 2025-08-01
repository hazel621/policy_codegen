# ----------- 构建阶段 -------------
FROM node:18-alpine AS builder

WORKDIR /app

# 拷贝依赖文件并安装依赖
COPY package.json package-lock.json ./
RUN npm install

# 拷贝源码并构建
COPY . .
RUN npm run build

# ----------- 运行阶段 -------------
FROM nginx:alpine

# 清理默认页面
RUN rm -rf /usr/share/nginx/html/*

# 拷贝构建好的文件
COPY --from=builder /app/dist /usr/share/nginx/html

# 添加 CORS 支持（可选：适用于浏览器端开发时调试跨域）
COPY default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
