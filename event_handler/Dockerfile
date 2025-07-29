FROM python:3.11-slim

# 创建工作目录
WORKDIR /app

# 复制当前目录代码（main.py 和 handlers 目录）
# COPY codegen/handlers /app/handlers
COPY event_handler /app/event_handler
COPY database /app/database

# 安装依赖（你需要在同级目录放 requirements.txt）
RUN pip install --no-cache-dir -r /app/event_handler/requirements.txt
RUN apt update && apt install -y iputils-ping redis-tools

# 开放端口（默认 FastAPI 使用8001）
EXPOSE 8001

# 启动 FastAPI 应用（main.py 中的 app 实例）
CMD ["uvicorn", "event_handler.main:app", "--host", "0.0.0.0", "--port", "8001"]

