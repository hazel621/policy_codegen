from fastapi import APIRouter, HTTPException
from database.models import LogRequestExecution, LogDutyExecution, Role, Power, Agent, AgentPowerRelation
from datetime import datetime
from datetime import timedelta
import uuid
from operations import notifier
from event_handler.state_checker import check_state

router = APIRouter()

@router.post("/hospital_1/create_data/")
async def create_data_handler(agent_id: str, counterparty_role_id:str=None, counterparty_agent_id:str=None, target_role_id: str=None, target_agent_id: str = None, scope: str = None,item: str = None,duty_ref:str=None):
    log = LogRequestExecution(
        uid=str(uuid.uuid4()),
        requester_id=agent_id,
        action_id="create_data",
        started_at=datetime.now(),
        end_at=None,
        related_duties=[],
        related_powers=[],
        status="pending",
    )
    log.save()

    # 🧭 State Checker: check agent's state
    state_check = check_state(agent_id=agent_id, action_id= "create_data",scope="hospital_1", target_agent_id=target_agent_id, target_role_id=target_role_id, item=item,duty_ref=duty_ref)
    if state_check["status"] == "fail":
        log.status = "failed"
        log.result = state_check["message"]
        log.end_at = datetime.now()
        log.save()
        raise HTTPException(status_code=403, detail=state_check["message"])
    print(f"🧭 State Checker: {state_check['message']} for Agent {agent_id} and Action create_data")

    
    
    requester_id = agent_id
    message = f"new data of {target_agent_id} created by doctor"
    target_agent_id = "from_request" if "from_request"!="from_request" else target_agent_id
    target_role_id = "" if ""!="from_request" else target_role_id
    if target_agent_id:
        message = f"{requester_id} new data of {target_agent_id} created by doctor {target_agent_id}"
        notifier.notify(target_agent_id, message)
    elif target_role_id:
        message = f"{requester_id} new data of {target_agent_id} created by doctor {target_role_id}"
        notifier.notify(target_role_id, message)
    if duty_ref:
        duty_log = LogDutyExecution.objects(uid=duty_ref).first()
        duty_log.status = "fulfilled"
        duty_log.fulfilled_at = datetime.now()
        duty_log.save()
        print(f"🔔 Notification sent to {target_role_id or target_agent_id} by {requester_id}")
    

    
    

    log.status = "succeeded"
    log.end_at = datetime.now()
    log.save()
    return {"status": "success", "action": "create_data"}