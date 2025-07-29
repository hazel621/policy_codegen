from fastapi import APIRouter, HTTPException
from database.models import LogRequestExecution, LogDutyExecution, Role, Power, Agent, AgentPowerRelation
from datetime import datetime
from datetime import timedelta
import uuid
from operations import notifier
from event_handler.state_checker import check_state

router = APIRouter()

@router.post("/hospital_1/request_access/")
async def request_access_handler(agent_id: str, counterparty_role_id:str=None, counterparty_agent_id:str=None, target_role_id: str=None, target_agent_id: str = None, scope: str = None,item: str = None,duty_ref:str=None):
    log = LogRequestExecution(
        uid=str(uuid.uuid4()),
        requester_id=agent_id,
        action_id="request_access",
        started_at=datetime.now(),
        end_at=None,
        related_duties=[],
        related_powers=[],
        status="pending",
    )
    log.save()

    # 🧭 State Checker: check agent's state
    state_check = check_state(agent_id=agent_id, action_id= "request_access",scope="hospital_1", target_agent_id=target_agent_id, target_role_id=target_role_id, item=item,duty_ref=duty_ref)
    if state_check["status"] == "fail":
        log.status = "failed"
        log.result = state_check["message"]
        log.end_at = datetime.now()
        log.save()
        raise HTTPException(status_code=403, detail=state_check["message"])
    print(f"🧭 State Checker: {state_check['message']} for Agent {agent_id} and Action request_access")

    
    
    counterparty_role_id = "doctor_hospital_1" if "doctor_hospital_1"!="from_request" else counterparty_agent_id
    counterparty_agent_id = "" if ""!="from_request" else counterparty_agent_id
    duty_id = "send_data"
    if not counterparty_role_id and not counterparty_agent_id:
        log.status = "failed"
        log.result = "Either role_id or agent_id must be provided"
        log.end_at = datetime.now()
        log.save()
        raise HTTPException(status_code=400, detail="Either role_id or agent_id must be provided")
    if counterparty_role_id:
        role = Role.objects(uid=counterparty_role_id).first()
        if not role:
            log.status = "failed"
            log.result = f"Role { counterparty_role_id } not found"
            log.end_at = datetime.now()
            log.save()
            raise HTTPException(status_code=404, detail=f"Role { counterparty_role_id } not found")
        for duty in role.duties:
            if duty["duty_id"] == duty_id:
                print(f"✅ Duty {duty_id} activated for Role { counterparty_role_id }")
                related_duties = [{"role_id": counterparty_role_id, "duty_id": duty_id}]
                log.related_duties = related_duties
                log.save()

                duty_log_id = str(uuid.uuid4())
                duty_log = LogDutyExecution(
                    uid=duty_log_id,
                    request_id=log.uid,
                    requester_id=agent_id,
                    duty_id= duty_id,
                    action_id="request_access",
                    related_agents={"roles": [counterparty_role_id],"scope": "hospital_1" },
                    assigned_at=datetime.now(),
                    started_at=None,
                    fulfilled_at=None,
                    violated_at=None,
                    status="assigned",
                    status_change_leads_to=[{"state":"assigned","leads_to":{"type":"add_power","power_id":"send_data"}},
 {"state":"fulfilled","leads_to":{"type":"remove_power","power_id":"send_data"}}]
                )
                duty_log.save()
                break
    elif counterparty_agent_id:
        agent = Agent.objects(uid=counterparty_agent_id).first()
        if not agent:
            log.status = "failed"
            log.result = f"Agent {counterparty_agent_id} not found"
            log.end_at = datetime.now()
            log.save()
            raise HTTPException(status_code=404, detail=f"Agent {counterparty_agent_id} not found")
        for duty in agent.duties:
            if duty["duty_id"] == duty_id :
                print(f"✅ Duty { duty_id } activated for Agent {counterparty_agent_id}")
                related_duties = [{"agent_id": counterparty_agent_id, "duty_id":  duty_id }]
                log.related_duties = related_duties
                log.save()

                duty_log_id = str(uuid.uuid4())
                duty_log = LogDutyExecution(
                    uid=duty_log_id,
                    request_id=log.uid,
                    requester_id=agent_id,
                    duty_id= duty_id ,
                    action_id="request_access",
                    related_agents={"agents": [counterparty_agent_id],"scope": "hospital_1"},
                    assigned_at=datetime.now(),
                    started_at=None,
                    fulfilled_at=None,
                    violated_at=None,
                    status="assigned",
                    status_change_leads_to=[]
                )
                duty_log.save()
                break
    
    

    log.status = "succeeded"
    log.end_at = datetime.now()
    log.save()
    return {"status": "success", "action": "request_access"}