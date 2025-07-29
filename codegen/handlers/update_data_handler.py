from fastapi import APIRouter, HTTPException
from database.models import LogRequestExecution, LogDutyExecution, Role, Power, Agent, AgentPowerRelation
from datetime import datetime
from datetime import timedelta
import uuid
from event_handler.state_checker import check_state
import redis

router = APIRouter()

@router.post("/hospital_1/update_data/")
async def update_data_handler(agent_id: str, counterparty_role_id:str=None, counterparty_agent_id:str=None, target_role_id: str=None, target_agent_id: str = None, scope: str = None,item: str = None,duty_ref:str=None):
    log = LogRequestExecution(
        uid=str(uuid.uuid4()),
        requester_id=agent_id,
        action_id="update_data",
        started_at=datetime.now(),
        end_at=None,
        related_duties=[],
        related_powers=[],
        status="pending",
    )
    log.save()

    # 🧭 State Checker: check agent's state
    state_check = check_state(agent_id=agent_id, action_id= "update_data",scope="hospital_1", target_agent_id=target_agent_id, target_role_id=target_role_id, item=item,duty_ref=duty_ref)
    if state_check["status"] == "fail":
        log.status = "failed"
        log.result = state_check["message"]
        log.end_at = datetime.now()
        log.save()
        raise HTTPException(status_code=403, detail=state_check["message"])
    print(f"🧭 State Checker: {state_check['message']} for Agent {agent_id} and Action update_data")

    
    
    requester_id = agent_id
    message = f"data of {target_agent_id} updated by doctor_hospital_1"
    target_agent_id = "from_request" if "from_request"!="from_request" else target_agent_id
    target_role_id = "" if ""!="from_request" else target_role_id
    if target_agent_id:
        message = f"data of {target_agent_id} updated by doctor_hospital_1"
        try:
            r = redis.Redis(host="redis", port=6379, socket_connect_timeout=2, socket_timeout=2)
            r.publish(target_agent_id, message)
            print(f"Notification sent to {target_agent_id}: {message}")
        except redis.ConnectionError as e:
            print(f"Redis connection error: {e}")
            log.status = "failed"
            log.result = "Redis connection error"
            log.end_at = datetime.now()
            log.save()
            raise HTTPException(status_code=500, detail="Internal server error: Redis connection failed")
    elif target_role_id:
        message = f"data of {target_agent_id} updated by doctor_hospital_1"
        try:
            r = redis.Redis(host="redis", port=6379, socket_connect_timeout=2, socket_timeout=2)
            r.publish(target_role_id, message)
            print(f"Notification sent to {target_role_id}: {message}")
        except redis.ConnectionError as e:
            print(f"Redis connection error: {e}")
            log.status = "failed"
            log.result = "Redis connection error"
            log.end_at = datetime.now()
            log.save()
            raise HTTPException(status_code=500, detail="Internal server error: Redis connection failed")
    if duty_ref:
        duty_log = LogDutyExecution.objects(uid=duty_ref).first()
        duty_log.status = "fulfilled"
        duty_log.fulfilled_at = datetime.now()
        duty_log.save()
        print(f"🔔 Notification sent to {target_role_id or target_agent_id} by {requester_id}")
    
    
    

    log.status = "succeeded"
    log.end_at = datetime.now()
    log.save()
    return {"status": "success", "action": "update_data"}