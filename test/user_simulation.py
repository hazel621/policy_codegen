import redis

r = redis.Redis()

role_channel = "doctor_hospital_1"
pubsub = r.pubsub()
pubsub.subscribe(role_channel)

for message in pubsub.listen():
    print(f"Bob received: {message}")
