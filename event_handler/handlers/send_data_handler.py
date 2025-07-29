from fastapi import APIRouter, HTTPException
from database.models import LogRequestExecution, LogDutyExecution, Role
from datetime import datetime
import uuid
# from mongoengine import connect
from operations import notifier
from event_handler.state_checker import check_state

router = APIRouter()

# connect(db="policy_system", host="localhost", port=27017)

@router.post("/send_data/")
async def request_data_handler(agent_id: str,duty_ref: str = None,target_agent_id: str = None):
    log = LogRequestExecution(
        uid=str(uuid.uuid4()),
        requester_id=agent_id,
        action_id="request_data",
        started_at=datetime.now(),
        end_at= None,  
        related_duties = [],
        related_powers = [],
        status="pending",
    )
    log.save()
    # 🧭 State Checker: check agent's state
    if duty_ref:
        state_check = check_state(agent_id=agent_id,action_id = "send_data", duty_ref=duty_ref)
        if state_check["status"] == "fail":
            raise HTTPException(status_code=400, detail=state_check["message"])
        else:
            print(f"🧭 State Checker: {state_check['message']} for agent {agent_id} with action request_data")
            duty_log = LogDutyExecution.objects.get(uid=duty_ref)
            duty_log.status = "executing"
            duty_log.fulfilled_at = datetime.now()
            duty_log.status = "fulfilled"
            duty_log.save()

            log.status = "succeeded"
            log.end_at = datetime.now()
            log.save()
        # Notify the agent about the request
        notifier.notify(
            channel=agent_id,
            message=f"Request for data initiated. Reference: {duty_ref}. Please fulfill the request."
        )
    else:
        state_check = check_state(agent_id=agent_id, action_id="send_data",target_agent_id=target_agent_id)
        if state_check["status"] == "fail":
            log.status = "failed"
            log.state_check_result = state_check["message"]
            log.result = state_check["message"]
            log.end_at = datetime.now()
            log.save()
            raise HTTPException(status_code=403, detail=state_check["message"])
        log.state_check_result = state_check["message"]
        print(f"🧭 State Checker: {state_check['message']} for Agent {agent_id} and Action request_data")
        log.status = "succeeded"
        log.end_at = datetime.now()
        log.save()
        # Notify the agent about the request
        notifier.notify(
            channel=agent_id,
            message="Request for data initiated. Please fulfill the request."
        )

    return {"status": "success", "message": "Request for data initiated.", "request_id": log.uid}