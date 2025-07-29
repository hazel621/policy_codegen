# duty monitor
# listen to duty log changes
# assign duty task with deadline
# check duty status to maintain the queue
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from datetime import timedelta
import datetime

client = AsyncIOMotorClient("mongodb://host.docker.internal:27017/?replicaSet=rs0")
db = client["policy_system"]

def parse_timeout(value: str) -> timedelta:
    value = value.strip().lower()
    if value.endswith("h"):
        return timedelta(hours=int(value[:-1]))
    elif value.endswith("m"):
        return timedelta(minutes=int(value[:-1]))
    elif value.endswith("s"):
        return timedelta(seconds=int(value[:-1]))
    elif value.endswith("d"):
        return timedelta(days=int(value[:-1]))
    else:
        # fallback: try pure number as seconds
        return timedelta(seconds=int(value))
# [{"state":"assigned","leads_to":{"type":"add_power","power_id":"send_data"}},
#  {"state":"fulfilled","leads_to":{"type":"remove_power","power_id":"send_data"}}]
async def handle_transformation_if_needed(doc):
    related_agents = doc.get("related_agents", {})
    scope = related_agents.get("scope", "default")
    related_agents = related_agents.get("roles") if related_agents.get("roles") else related_agents.get("agents", [])
    related_agents = related_agents[0] if isinstance(related_agents, list) and len(related_agents) > 0 else related_agents
    rules = doc.get("status_change_leads_to")
    for rule in rules:

        trigger = rule.get("state")
        effect = rule.get("leads_to")

        # 判断是否满足触发条件
        current_status = doc.get("status")
        if (
            # trigger["type"] == "duty"
            # and trigger["id"] == doc["duty_id"]
            # and trigger["operation"] == "activate"
            # and current_status == "assigned"
            current_status == trigger
        ):
            await apply_effect(effect,related_agents,scope)

async def apply_effect(effect: dict,related_agents:str,scope:str = "default"):
    if effect["type"] == "add_power":
        power_id = effect["power_id"]
        power_doc = {
            "power_id": power_id,
            "created_at": datetime.datetime.now(),
            "scope": scope,
        }
        await db["role"].update_one(
            {"_id": related_agents},
            {"$set": {f"temporary_powers.{power_id}": power_doc}}
        )
        print(f"⚡️ Power {effect['power_id']} added to {related_agents} by transformation")
    elif effect["type"] == "remove_power":
        power_id = effect["power_id"]
        await db["role"].update_one(
            {"_id": related_agents},
            {"$unset": {f"temporary_powers.{power_id}": ""}}
        )
        print(f"⚡️ Power {effect['power_id']} removed from {related_agents} by transformation")

async def listen_to_duties():
    try:
        collection = db['log_duty_execution']
        pipeline = [{"$match": {"operationType": {"$in": ["insert", "update"]}}}]

        async with collection.watch(pipeline) as stream:
            async for change in stream:
                op_type = change["operationType"]
                if op_type == "insert":    
                    document = change["fullDocument"]
                    print(f"🆕 New LogDutyExecution inserted: {document}")
                    await handle_transformation_if_needed(document)
                    duty =  await db["duty"].find_one({"_id": document["duty_id"]})
                    violation = None
                    deadline = None
                    if duty and "violation_id" in duty:
                        violation = await db["violation"].find_one({"_id": duty["violation_id"]})
                        if violation:
                            condition = violation["condition"]
                            deadline = condition.get("time", None)
                            # print(deadline)
                            # if condition["type"] == "timeout":
                            #     deadline = condition["time"].replace("days", "")

                    task_queue = db['duty_task_list']
                    task_queue.insert_one({
                                "_id": document["_id"],
                                "requester_id": document["requester_id"],
                                "related_action_id": document["action_id"], #duty-related action needed to be fufilled
                                "duty_id": document["duty_id"],
                                "deadline": document["assigned_at"] + parse_timeout(deadline) if deadline else None,
                                # "deadline": document["assigned_at"] + timedelta(seconds=int(deadline)) if deadline else None,
                                "status": "assigned"
                            })
                elif op_type == "update":
                    document_key = change["documentKey"]
                    updated_fields = change["updateDescription"]["updatedFields"]
                    print(f"🔄 DutyLog {document_key} updated: {updated_fields}")
                    # 先读取最新文档
                    full_doc = await db["log_duty_execution"].find_one({"_id": document_key["_id"]})
                    await handle_transformation_if_needed(full_doc)
                    # ⬇️ 检查 transformation
                    if full_doc:
                        await handle_transformation_if_needed(full_doc)
                    if "status" in updated_fields and updated_fields["status"] in ["fulfilled", "violated"]:
                        await db["duty_task_list"].delete_one({"_id": document_key["_id"]})
                        print(f"🗑 DutyTaskList entry for {document_key} removed after status update.")

    except PyMongoError as e:
        print(f"❌ Error watching changes: {e}")


if __name__ == "__main__":
    print("🔍 Listening for new Duty logs...")
    asyncio.run(listen_to_duties())