from fastapi import FastAPI
import importlib.util
import os
import sys
from fastapi.middleware.cors import CORSMiddleware
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from database.connection import connect_to_mongo
import time

# MongoDB 连接
db_connect = connect_to_mongo()

# 监听的目录（你的挂载卷路径）
HANDLER_DIR = "./codegen/handlers"

app = FastAPI(title="Event Handler Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定 http://localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_handler(filename: str):
    """加载单个 handler 文件"""
    if not filename.endswith(".py") or filename.startswith("__"):
        return

    module_path = os.path.join(HANDLER_DIR, filename)
    module_name = f"dynamic_handlers.{filename[:-3]}"  # 避免和已有 handlers 冲突

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    if hasattr(module, "router"):
        print(f"🔗 Including router from: {filename}")
        app.include_router(module.router, tags=["actions"])
    else:
        print(f"⚠️ No router found in {filename}, skipping...")


def include_all_handlers():
    """初始化时加载所有现有的 handler"""
    for filename in os.listdir(HANDLER_DIR):
        load_handler(filename)


class HandlerDirWatcher(FileSystemEventHandler):
    """文件变化监听器"""
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            filename = os.path.basename(event.src_path)
            print(f"📂 New handler detected: {filename}, loading...")
            load_handler(filename)


# 初始化加载现有 handlers
include_all_handlers()

# 启动 watchdog 监听
observer = Observer()
event_handler = HandlerDirWatcher()
observer.schedule(event_handler, HANDLER_DIR, recursive=False)
observer.start()

@app.on_event("shutdown")
def shutdown_event():
    observer.stop()
    observer.join()