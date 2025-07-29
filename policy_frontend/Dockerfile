# Step 1: Build React app
FROM node:18 AS builder

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY package.json package-lock.json ./
RUN npm install

# 拷贝源代码并构建
COPY . .
RUN npm run build

# 阶段2：使用 Nginx 运行构建后的静态文件
FROM nginx:stable-alpine

# 清除默认静态资源
RUN rm -rf /usr/share/nginx/html/*

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 拷贝自定义 nginx.conf（如果你需要 history 模式支持可以加上）
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
