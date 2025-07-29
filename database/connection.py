from mongoengine import connect, disconnect
from pymongo.errors import ServerSelectionTimeoutError
import os

def connect_to_mongo():
    disconnect(alias="default")
    db = os.getenv("MONGO_DB", "policy_system")
    host = os.getenv("MONGO_HOST", "host.docker.internal")
    port = os.getenv("MONGO_PORT", "27017")
    replica_set = os.getenv("MONGO_REPLICA_SET", "rs0")

    uri = f"mongodb://{host}:{port}/?replicaSet={replica_set}"
    print(f"🔗 Connecting to MongoDB at {uri}")

    try:
        conn = connect(
            db=db,
            host=uri,
            alias="default",
            serverSelectionTimeoutMS=3000  # 3 秒内超时
        )
        # 立即触发连接
        conn.server_info()
        print("✅ Successfully connected to MongoDB")
        return conn
    except ServerSelectionTimeoutError as e:
        print("❌ Failed to connect to MongoDB")
        print(f"Reason: {e}")
        return None
