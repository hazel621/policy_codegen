from fastapi import FastAPI
import importlib.util
import os
import sys
from fastapi.middleware.cors import CORSMiddleware
from database.connection import connect_to_mongo

db_connect = connect_to_mongo()

HANDLER_DIR = "./handlers"

app = FastAPI(title="Event Handler Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定 http://localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def include_all_handlers(app: FastAPI):
    for filename in os.listdir(HANDLER_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_path = os.path.join(HANDLER_DIR, filename)
            module_name = f"handlers.{filename[:-3]}"

            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 假设每个 handler 文件中都定义了一个名为 `router` 的 APIRouter 实例
            if hasattr(module, "router"):
                print(f"🔗 Including router from: {filename}")
                app.include_router(module.router, prefix="/actions", tags=["actions"])
            else:
                print(f"⚠️  No router found in {filename}, skipping...")

include_all_handlers(app)
