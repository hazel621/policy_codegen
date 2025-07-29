# 这个现在不一定用
'''
一个请求，根据role，如果多个duty实例创建，请求和这些duty关联，一起维护在requestLog和LogDutyExecution中
当请求者请求并激活某个duty(事实上是根据现有的agentdutyrelation实例化了duty task来维护)时，会发出通知提醒duty holder，duty holder收到关于该请求的信息（request_id），再向系统发出完成该duty的请求，
系统根据这个信息，记录duty完成的情况。

1. power-related: requester has power to perform the action, but the action performed failed, save execution log and send it to requester.
2. duty-related: 
        2.1 requester has duty that has activated and tracked by duty monitor to perform the action, but the action performed failed, 
            save execution log and send it to requester, send it to compliance inspector to check if it violates.
        2.2 requester has duty that has not activated, but the action performed failed,send result to
            requester, doesn't trigger escalation since there's no duty tracked.
3. technical-related: save execution log and send it to requester, doesn't trigger escalation since it's technical error.

'''

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["policy_system"]

async def listen_to_changes():
    try:
        collection = db['log_request_execution']
        pipeline = [{"$match": {"operationType": "insert"}}]

        async with collection.watch(pipeline) as stream:
            async for change in stream:
                document = change["fullDocument"]
                print(f"🆕 New LogRequestExecution inserted: {document}")

                status = document["status"]
                request_id = document["uid"]  # 注意：request_id 可能是 uid

                if status == "pending":
                    print(f"⏳ Request {request_id} is pending, waiting for duty instantiation...")

                elif status == "succeeded":
                    print(f"✅ Request {request_id} succeeded, all duties fulfilled.")

                elif status == "failed":
                    print(f"❌ Request {request_id} failed, triggering violation process.")

                else:
                    print(f"⚠ Unknown status for request {request_id}: {status}")

    except PyMongoError as e:
        print(f"❌ Error watching changes: {e}")

if __name__ == "__main__":
    asyncio.run(listen_to_changes())
