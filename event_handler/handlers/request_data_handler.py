from fastapi import APIRouter, HTTPException
from database.models import LogRequestExecution, LogDutyExecution, Role
from datetime import datetime
import uuid
from operations import notifier
from event_handler.state_checker import check_state

router = APIRouter()


@router.post("/request_data/")
async def request_data_handler(agent_id: str):
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
    state_check = check_state(agent_id=agent_id, action_id="request_data")
    if state_check["status"] == "fail":
        log.status = "failed"
        log.result = state_check["message"]
        log.end_at = datetime.now()
        log.save()
        raise HTTPException(status_code=403, detail=state_check["message"])
    print(f"🧭 State Checker: {state_check['message']} for Agent {agent_id} and Action request_data")

    # 🧭 Activate Duty: send_data
    role_id = "doctor_hospital_1"
    role = Role.objects(uid=role_id).first()
    if not role:
        log.status = "failed"
        log.result = f"Role {role_id} not found"
        log.end_at = datetime.now()
        log.save()
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found")
    for duty in role.duties:
        if duty["duty_id"] == "send_data":
            print(f"✅ Duty send_data activated for Role {role_id}")
            
            related_duties = [{"role_id": role_id, "duty_id": "send_data"}]
            log.related_duties = related_duties
            log.save()

            duty_log_id = str(uuid.uuid4())
            duty_log = LogDutyExecution(
                uid=duty_log_id,
                request_id=log.uid,
                requester_id=agent_id,
                duty_id="send_data",
                action_id="request_data",
                related_agents={"roles": [role_id]},  
                assigned_at=datetime.now(),
                started_at=None,  
                fulfilled_at=None,  
                violated_at=None, 
                status="assigned",
                status_change_leads_to = [{"state":{'type': 'duty', 'id': 'send_data', 'operation': 'activate'},"leads_to":{'type': 'power', 'id': 'send_data', 'operation': 'activate'}}]
            )
            duty_log.save()
            break        
    
    # 📢 Notify
    requester_id = agent_id
    message = f"data requested by {requester_id}, reference: {duty_log_id}"
    notifier.notify("doctor_hospital_1",message)

    log.status = "succeeded"
    log.end_at = datetime.now()
    log.save()
    return {"status": "success", "action": "request_data"}
