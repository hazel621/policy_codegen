from fastapi import APIRouter, HTTPException
from database.models import LogRequestExecution, LogDutyExecution, Role, Power, Agent, AgentPowerRelation
from datetime import datetime
from datetime import timedelta
import uuid
from event_handler.state_checker import check_state
import redis

router = APIRouter()

@router.post("/hospital_1/revoke_consent/")
async def revoke_consent_handler(agent_id: str, counterparty_role_id:str=None, counterparty_agent_id:str=None, target_role_id: str=None, target_agent_id: str = None, scope: str = None,item: str = None,duty_ref:str=None):
    log = LogRequestExecution(
        uid=str(uuid.uuid4()),
        requester_id=agent_id,
        action_id="revoke_consent",
        started_at=datetime.now(),
        end_at=None,
        related_duties=[],
        related_powers=[],
        status="pending",
    )
    log.save()

    # 🧭 State Checker: check agent's state
    state_check = check_state(agent_id=agent_id, action_id= "revoke_consent",scope="hospital_1", target_agent_id=target_agent_id, target_role_id=target_role_id, item=item,duty_ref=duty_ref)
    if state_check["status"] == "fail":
        log.status = "failed"
        log.result = state_check["message"]
        log.end_at = datetime.now()
        log.save()
        raise HTTPException(status_code=403, detail=state_check["message"])
    print(f"🧭 State Checker: {state_check['message']} for Agent {agent_id} and Action revoke_consent")

    
    
    power_id = "share_data"
    power_exist =  Power.objects(uid=power_id).first()
    target_role_id = "from_request" if "from_request"!="from_request" else target_role_id
    target_agent_id = "from_request" if "from_request"!="from_request" else target_agent_id
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
        existing_power = target_role.temporary_powers if target_role.temporary_powers else {}
        item = "requester.data".replace("requester",agent_id) if "requester.data" else None
        for power in existing_power:
            if power["power_id"] == power_id:
                if item and power.get("item") != item:
                    log.status = "failed"
                    log.result = f"Power {power_id} not found in Role {target_role_id} with item {item}"
                    log.end_at = datetime.now()
                    log.save()
                    raise HTTPException(status_code=404, detail=f"Power {power_id} not found in Role {target_role_id} with item {item}")
                del target_role.temporary_powers[power_id]
                target_role.save()
                log.status = "succeeded"
                log.result = f"Power {power_id} removed from Role {target_role_id}"
                log.end_at = datetime.now()
                log.save()
                print(f"⚡️ Power {power_id} removed from Role {target_role_id} by performing revoke_consent")
                break
        else:
            log.status = "succeeded"
            log.result = f"Power {power_id} not found in Role {target_role_id}"
            log.end_at = datetime.now()
            log.save()
    elif target_agent_id:
        agent = Agent.objects(uid=target_agent_id).first()
        if not agent:
            log.status = "failed"
            log.result = f"Agent {target_agent_id} not found"
            log.end_at = datetime.now()
            log.save()
            raise HTTPException(status_code=404, detail=f"Agent {target_agent_id} not found")
        
        agent_powers_rel = AgentPowerRelation.objects(uid=target_agent_id).first()
        agent_powers = agent_powers_rel.powers if agent_powers_rel else {}
        log.related_powers = [{"agent_id": target_agent_id, "power_id": power_id}]
        item = "requester.data".replace("requester",agent_id) if "requester.data" else None
        for power in agent_powers:
            if power["power_id"] == power_id:
                if item and power.get("item") != item:
                    log.status = "failed"
                    log.result = f"Power {power_id} not found in Agent {target_agent_id} with item {item}"
                    log.end_at = datetime.now()
                    log.save()
                    raise HTTPException(status_code=404, detail=f"Power {power_id} not found in Agent {target_agent_id} with item {item}")
                del agent_powers[power_id]
                agent_powers_rel.powers = agent_powers
                agent_powers_rel.save()
                log.status = "succeeded"
                log.result = f"Power {power_id} removed from Agent {target_agent_id}"
                log.end_at = datetime.now()
                log.save()
                print(f"⚡️ Power {power_id} removed from Agent {target_agent_id} by performing revoke_consent")
                break
        else:
            log.status = "succeeded"
            log.result = f"Power {power_id} not found in Agent {target_agent_id}"
            log.end_at = datetime.now()
            log.save()

    
    
    
    requester_id = agent_id
    message = f"consent revoked by patient{requester_id}"
    target_agent_id = "" if ""!="from_request" else target_agent_id
    target_role_id = "doctor_hospital_1" if "doctor_hospital_1"!="from_request" else target_role_id
    if target_agent_id:
        message = f"consent revoked by patient{requester_id}"
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
        message = f"consent revoked by patient{requester_id}"
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
    return {"status": "success", "action": "revoke_consent"}