FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制脚本和依赖
COPY escalation_trigger.py .
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置默认启动脚本
CMD ["python", "escalation_trigger.py"]
