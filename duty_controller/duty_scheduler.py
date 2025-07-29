# duty scheduler
# maintain duty task queue by checking deadline and status of duty and notifying roles
import time
import datetime
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler

import redis
def notify(channel, message):
    r = redis.Redis()
    role_channel = channel
    r.publish(role_channel, message)
    print(f"Notification pub to {channel}: {message}")

client = MongoClient("mongodb://host.docker.internal:27017/?replicaSet=rs0")
db = client["policy_system"]

duty_log_collection = db["log_duty_execution"]
task_queue_collection = db["duty_task_list"]

def poll_and_check_duties():
    now = datetime.datetime.now()

    # Scan all tasks in duty queue
    tasks = task_queue_collection.find({})

    for task in tasks:
        duty_log_id = task["_id"]

        # Fetch the corresponding duty log
        duty_log = duty_log_collection.find_one({"_id": duty_log_id})
        # print(duty_log)

        if not duty_log:
            print(f"⚠ DutyLog {duty_log_id} not found. Removing task from queue.")
            task_queue_collection.delete_one({"_id": duty_log_id})
            continue

        # Check if already fulfilled
        if duty_log["status"] == "fulfilled":
            print(f"✅ Duty {duty_log_id} has been fulfilled. Removing task from queue.")
            task_queue_collection.delete_one({"_id": duty_log_id})
            continue

        if duty_log["status"] in ["waiting"]:
            continue  # Skip if still waiting or violation pending

        # schedule duty
        for role in duty_log["related_agents"]["roles"]:
            notify(
                channel= role,
                message=f"Duty {duty_log['duty_id']} is scheduled. Please {duty_log['duty_id']} with reference: {task['_id']} before {task['deadline']}."
            )

        # Check if violated based on deadline
        deadline = task["deadline"]
        if deadline and now >= deadline:
            print(f"❌ Duty {duty_log_id} deadline exceeded. Marking as violated.")
            # Notify the role channel about the violation
            for role in duty_log["related_agents"]["roles"]:
                notify(
                    channel= role,
                    message=f"Potential violation detected for Duty {duty_log_id}. Deadline exceeded at {now}."
                )
            # send it to violation monitor
            duty_log_collection.update_one(
                {"_id": duty_log_id},
                {"$set": {"status": "violated"}}
            )
            task_queue_collection.update_one(
                {"_id": duty_log_id},
                {"$set": {"status": "waiting"}}
            )
            continue

        # Still within execution window
        remaining = (deadline - now).total_seconds() if deadline else "unlimited"
        print(f"⏳ Duty {duty_log_id} still pending. Remaining time: {remaining} seconds")

# Start scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(poll_and_check_duties, 'interval', seconds=15)
scheduler.start()

print("✅ Duty Scheduler started and running...")

# Prevent main thread from exiting
while True:
    time.sleep(10)
