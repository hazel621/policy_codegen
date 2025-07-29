import redis
def notify(channel, message):
    """
    Sends a notification message to a specified channel.
    
    Args:
        channel (str): The channel to send the notification to.
        message (str): The message to be sent.
    """
    r = redis.Redis()
    role_channel = channel
    r.publish(role_channel, message)
    print(f"Notification sent to {channel}: {message}")
    