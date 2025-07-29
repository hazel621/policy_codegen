FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制 codegen 和 database 到容器
COPY codegen /app/codegen
COPY database /app/database

# 安装依赖
RUN pip install --no-cache-dir -r /app/codegen/requirements.txt

# 创建 handler 输出目录（用于代码生成）
RUN mkdir -p /app/enforcement

# 启动 FastAPI 服务
CMD ["uvicorn", "codegen.main:app", "--host", "0.0.0.0", "--port", "8000"]
