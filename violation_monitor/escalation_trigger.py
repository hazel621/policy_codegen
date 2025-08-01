import asyncio
from pymongo.errors import PyMongoError
from motor.motor_asyncio import AsyncIOMotorClient  # ✅ 使用 motor 的异步客户端

client = AsyncIOMotorClient("mongodb://host.docker.internal:27017/?replicaSet=rs0")  # ✅ motor client
db = client["policy_system"]


import redis
def notify(channel, message):
    r = redis.Redis(host="redis", port=6379, socket_connect_timeout=2, socket_timeout=2)
    role_channel = channel
    r.publish(role_channel, message)
    print(f"Notification pub to {channel}: {message}")

async def add_power(agent_id, power_id, scope):
    try:
        collection = db["agent_power_relation"]
        agent_power = await collection.find_one({"_id": agent_id})

        power_value = {
            "state": "active",
            "assigned_by": "violation_trigger",
            "action_id": power_id,
            "scope": scope
        }

        if agent_power:
            power_key = f"powers.{power_id}"
            await collection.update_one(
                {"_id": agent_id},
                {"$set": {power_key: power_value}}
            )
        else:
            power_obj = {power_id: power_value}
            await collection.insert_one({
                "_id": agent_id,
                "agent_name": agent_id,
                "powers": power_obj
            })
            print(f"🆕 Created AgentPowerRelation for Agent {agent_id} with Power {power_id}")
    except Exception as e:
        print(f"❌ Error in add_power: {e}")
  

async def check_violation():
    try:
        collection = db['log_duty_execution']
        pipeline = [{"$match": {"operationType":  "update"}}]
        async for change in collection.watch(pipeline, full_document='updateLookup'):
            document_key = change["documentKey"]
            updated_fields = change["updateDescription"]["updatedFields"]
            print(f"🔄 DutyLog {document_key} updated: {updated_fields}")
            if "status" in updated_fields and updated_fields["status"] in ["violated"]:
                document = change["fullDocument"]
                duty =  await db["duty"].find_one({"_id": document["duty_id"]})
                violation = None
                if duty and "violation_id" in duty:
                    violation = await db["violation"].find_one({"_id": duty["violation_id"]})
                    if violation:
                        consequence = violation["consequence"]
                        operations = consequence["operation"]
                        for operation in operations:
                            if operation["type"] == "add_power":
                                power_id = operation["power_id"]
                                scope = document.get("related_agents").get("scope", "default")
                                await add_power(
                                    document["requester_id"],
                                    power_id,
                                    scope
                                )
                                print(f"✅ Power {power_id} activated for Agent {document['requester_id']} due to violation.")
                            elif operation["type"] == "notify":
                                role = operation["target_role_id"]
                                message = operation["message"]
                                notify(
                                    channel=role,
                                    message=f"❌ Duty {document['duty_id']} violated due to: {message}, reference {document['_id']}."
                                )
                            elif operation["type"] == "activate_duty":
                                duty_id = operation["duty_id"]
                                # Activate the duty (implementation depends on your system)
                                print(f"🔄 Duty {duty_id} activated for Agent {document['requester_id']} due to violation.")
    except PyMongoError as e:
        print(f"❌ Error watching changes: {e}")

# if __name__ == "__main__":
print("🔍 Listening for Duty violations...")
asyncio.run(check_violation())