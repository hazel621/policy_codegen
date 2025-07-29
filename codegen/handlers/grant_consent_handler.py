from fastapi import APIRouter, HTTPException
from database.models import LogRequestExecution, LogDutyExecution, Role, Power, Agent, AgentPowerRelation
from datetime import datetime
from datetime import timedelta
import uuid
from operations import notifier
from event_handler.state_checker import check_state

router = APIRouter()

@router.post("/hospital_1/grant_consent/")
async def grant_consent_handler(agent_id: str, counterparty_role_id:str=None, counterparty_agent_id:str=None, target_role_id: str=None, target_agent_id: str = None, scope: str = None,item: str = None):
    log = LogRequestExecution(
        uid=str(uuid.uuid4()),
        requester_id=agent_id,
        action_id="grant_consent",
        started_at=datetime.now(),
        end_at=None,
        related_duties=[],
        related_powers=[],
        status="pending",
    )
    log.save()

    # 🧭 State Checker: check agent's state
    state_check = check_state(agent_id=agent_id, action_id= "grant_consent",scope="hospital_1", target_agent_id=target_agent_id, target_role_id=target_role_id, item=item)
    if state_check["status"] == "fail":
        log.status = "failed"
        log.result = state_check["message"]
        log.end_at = datetime.now()
        log.save()
        raise HTTPException(status_code=403, detail=state_check["message"])
    print(f"🧭 State Checker: {state_check['message']} for Agent {agent_id} and Action grant_consent")

    
    
    power_id = "share_data"
    power_exist =  Power.objects(uid=power_id).first()
    target_role_id = "from_request" if "from_request"!="from_request" else target_role_id
    target_agent_id = "from_request" if "from_request"!="from_request" else target_agent_id
    item = "requester.data".replace("requester",agent_id) if "requester.data" else item

    if not target_role_id and not target_agent_id:
        log.status = "failed"
        log.result = "Either role_id or agent_id must be provided"
        log.end_at = datetime.now()
        log.save()
        raise HTTPException(status_code=400, detail="Either role_id or agent_id must be provided")
    
    if not power_exist:
        log.status = "failed"
        log.result = f"Power {power_id} not found"
        log.end_at = datetime.now()
        log.save()
        raise HTTPException(status_code=404, detail=f"Power {power_id} not found")
    
    if target_role_id:
        target_role = Role.objects(uid=target_role_id).first()
        if not target_role:
            log.status = "failed"
            log.result = f"Role {target_role_id} not found"
            log.end_at = datetime.now()
            log.save()
            raise HTTPException(status_code=404, detail=f"Role {target_role_id} not found")  
        
        log.related_powers = [{"role_id": target_role_id, "power_id": power_id}]
        existing_power = target_role.powers
        expire_at = None
        duration = "10d" if "10d" else None
        scope = "from_request" if "from_request"!="from_request" else target_role.scope

        if any(power["power_id"] == power_id for power in existing_power):
            log.status = "succeeded"
            log.result = f"Power {power_id} already exists in Role {target_role_id}"
            log.end_at = datetime.now()
            log.save()
        else:
            if duration:
                if duration.endswith("s"):
                    duration = int(duration[:-1] )
                    expire_at = datetime.now() + timedelta(seconds=duration)
                elif duration.endswith("d"):
                    duration = int(duration[:-1] )
                    expire_at = datetime.now() + timedelta(days=duration)
                elif duration.endswith("h"):
                    duration = int(duration[:-1] )
                    expire_at = datetime.now() + timedelta(hours=duration)
                elif duration.endswith("m"):
                    duration = int(duration[:-1] )
                    expire_at = datetime.now() + timedelta(minutes=duration)

            power_doc = {
                "power_id": power_id,
                "created_at": datetime.now(),
                "expire_at": expire_at,
                "scope": scope,
                "item": item,
            }
            temporary_powers = target_role.temporary_powers if target_role.temporary_powers else {}
            temporary_powers[power_id]=power_doc
            target_role.temporary_powers= temporary_powers
            target_role.save()
            print(f"⚡️ Power share_data added by performing grant_consent")
    elif target_agent_id:
        agent = Agent.objects(uid=target_agent_id).first()
        if not agent:
            log.status = "failed"
            log.result = f"Agent {target_agent_id} not found"
            log.end_at = datetime.now()
            log.save()
            raise HTTPException(status_code=404, detail=f"Agent {target_agent_id} not found")
        
        agent_powers_rel = AgentPowerRelation.objects(uid=target_agent_id).first()
        agent_powers = agent_powers_rel.powers if agent_powers_rel else []
        existing_power = agent_powers.get(power_id, [])
        log.related_powers = [{"agent_id": target_agent_id, "power_id": power_id}]
        if existing_power:
            log.status = "succeeded"
            log.result = f"Power {power_id} already exists in Agent {target_agent_id}"
            log.end_at = datetime.now()
            log.save()
        else:
            expire_at = None
            duration = "10d" if "10d" else None
            if duration:
                if duration.endswith("s"):
                    duration = int(duration[:-1] )
                    expire_at = datetime.now() + timedelta(seconds=duration)
                elif duration.endswith("d"):
                    duration = int(duration[:-1] )
                    expire_at = datetime.now() + timedelta(days=duration)
                elif duration.endswith("h"):
                    duration = int(duration[:-1] )
                    expire_at = datetime.now() + timedelta(hours=duration)
                elif duration.endswith("m"):
                    duration = int(duration[:-1] )
                    expire_at = datetime.now() + timedelta(minutes=duration)
            power_doc = {
                "power_id": power_id,
                "created_at": datetime.now(),
                "expire_at": expire_at,
                "scope": scope,
                "item": item,
            }
            agent_powers[power_id] = power_doc
            agent_powers_rel.powers = agent_powers
            agent_powers_rel.save()
            print(f"⚡️ Power share_data added by performing grant_consent")
    
    

    log.status = "succeeded"
    log.end_at = datetime.now()
    log.save()
    return {"status": "success", "action": "grant_consent"}