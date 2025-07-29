# listen to status change of duty log
# if restart scan duty task queue needed
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from datetime import timedelta

import redis
def notify(channel, message):
    r = redis.Redis()
    role_channel = channel
    r.publish(role_channel, message)
    print(f"Notification pub to {channel}: {message}")


client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["policy_system"]

async def check_violation():
    try:
        collection = db['log_duty_execution']
        pipeline = [{"$match": {"operationType":  "update"}}]
        async with collection.watch(pipeline, full_document='updateLookup') as stream:
            async for change in stream:    
                document_key = change["documentKey"]
                updated_fields = change["updateDescription"]["updatedFields"]
                print(f"🔄 DutyLog {document_key} updated: {updated_fields}")

                if "status" in updated_fields and updated_fields["status"] == "violation_pending":
                    document = change["fullDocument"]  # ✅ 现在不会报错了
                    duty =  await db["duty"].find_one({"_id": document["duty_id"]})
                    violation = None
                    if duty and "violation_id" in duty:
                        violation = await db["violation"].find_one({"_id": duty["violation_id"]})
                        if violation:
                            condition = violation["condition"]
                            if condition["type"] == "timeout":
                                new_deadline = condition["time"].replace("days", "")
                                new_deadline = document["assigned_at"] + timedelta(days=int(new_deadline))
                                old_deadline = await db["duty_task_queue"].find_one({"_id": document_key["_id"]})
                                if new_deadline < old_deadline["deadline"]:
                                    print(f"🔄 Updating deadline for Duty {document_key} to {new_deadline}")
                                    await db["duty_task_queue"].update_one(
                                        {"_id": document_key["_id"]},
                                        {"$set": {"deadline": new_deadline,
                                                  "status": "assigned"}}
                                    )
                                    await db["log_duty_execution"].update_one(
                                        {"_id": document_key["_id"]},
                                        {"$set": {"status": "assigned"}}
                                    )
                                else:
                                    print(f"❌ Duty {document['duty_id']} deadline already passed. violation dectected.")
                                    await db["duty_task_queue"].delete_one({"_id": document_key["_id"]})
                                    await db["log_duty_execution"].update_one(
                                        {"_id": document_key["_id"]},
                                        {"$set": {"status": "violated"}}
                                    )
                                    for role in document["related_agents"]["roles"]:
                                        notify(
                                            channel=role,  
                                            message=f"❌ Duty {document['duty_id']} violated due to deadline exceeded, reference {document_key['_id']}."
                                        )
    except PyMongoError as e:
        print(f"❌ Error watching changes: {e}")

if __name__ == "__main__":
    print("🔍 Listening for pending violations...")
    asyncio.run(check_violation())
