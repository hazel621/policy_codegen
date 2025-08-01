FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝源代码
COPY duty_monitor.py .
COPY duty_scheduler.py .

# 启动两个后台进程（一个监听 MongoDB，一个周期性调度）
CMD ["bash", "-c", "python duty_monitor.py & python duty_scheduler.py && wait"]

# CMD ["python", "duty_monitor.py"]