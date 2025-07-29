# 如果有expire at,检查是否过期
from database.models import AgentPowerRelation, AgentDutyRelation,LogDutyExecution,Agent, Role
from datetime import datetime
# from mongoengine import connect

# connect(db="policy_system", host="localhost", port=27017)
def check_state(**kwargs):
    agent_id = kwargs.get("agent_id")
    action_id = kwargs.get("action_id")
    # target_agent_id = kwargs.get("target_agent_id")
    # target_role_id = kwargs.get("target_role_id")
    scope = kwargs.get("scope")
    item = kwargs.get("item")
    if not agent_id or not action_id:
        return {"status": "fail", "message": "Missing agent_id or action_id"}
    if kwargs.get("duty_ref"):
        # 如果有 duty_ref，检查 duty 是否存在
        duty_ref = kwargs.get("duty_ref")
        duty_tracked = LogDutyExecution.objects(uid=duty_ref).first()
        if not duty_tracked:
            return {"status": "fail", "message": f"No Tracked Duty with ID {duty_ref}"}
        if  duty_tracked.status != "assigned":
            return {"status": "fail", "message": f"Tracked Duty {duty_ref} is not in assigned state"}
        
        # related_agents = duty_tracked.related_agents
        # if related_agents.get("agents"):
        #     if agent_id not in related_agents["agents"]:
        #         return {"status": "fail", "message": f"Agent {agent_id} is not related to duty {duty_ref}"}
        power_rel = AgentPowerRelation.objects(uid=agent_id).first()
        duty_rel = AgentDutyRelation.objects(uid=agent_id).first()
        power_rel = power_rel.powers if power_rel else {}
        duty_rel = duty_rel.duties if duty_rel else {}
        
        power_exist = power_rel.get(action_id, None)
        duty_exist = duty_rel.get(action_id, None)
        if not power_exist and not duty_exist:   
            return {"status": "fail", "message": f"Agent {agent_id} has no {action_id}-related power and duty"}
        elif duty_exist and not power_exist:
            if scope != duty_exist.get("scope"):
                return {"status": "fail", "message": f"Duty {action_id} is not scoped to {scope}"}
            return {"status": "pass", "message": "no power found but duty exists, state check passed"}
        elif power_exist and not duty_exist:
            if scope != power_exist.get("scope"):
                return {"status": "fail", "message": f"Power {action_id} is not scoped to {scope}"}
            return {"status": "pass", "message": "no duty found but power exists, state check passed"}
        
    # 如果没有 duty_ref，检查 agent 是否有相关的 power 或 duty
    agent_power_rel = AgentPowerRelation.objects(uid=agent_id).first()
    agent_duty_rel = AgentDutyRelation.objects(uid=agent_id).first()
    
    agent_duty_rel = agent_duty_rel.duties if agent_duty_rel else {}
    agent_power_rel = agent_power_rel.powers if agent_power_rel else {}

    agent_duty_exist = agent_duty_rel.get(action_id, None)
    agent_power_exist = agent_power_rel.get(action_id, None)
    if not agent_duty_exist and not agent_power_exist:
        return {"status": "fail", "message": f"Agent {agent_id} has no related power and duty"}
    if agent_power_exist:
        if agent_power_exist.get("expire_at") and datetime.fromisoformat(str(agent_power_exist["expire_at"])) < datetime.now():
            return {"status": "fail", "message": f"Power {action_id} has expired"}
        if scope != agent_power_exist.get("scope"):
            return {"status": "fail", "message": f"Power {action_id} is not scoped to {scope}"}
        if agent_power_exist.get("item") != item:
            return {"status": "fail", "message": f"Power {action_id} is not scoped to item {item}"}
        return {"status": "pass", "message": "State check passed for power"}
    if agent_duty_exist:
        if agent_duty_exist.get("expire_at") and datetime.fromisoformat(agent_duty_exist["expire_at"]) < datetime.now():
            return {"status": "fail", "message": f"Duty {action_id} has expired"}
        if scope != agent_duty_exist.get("scope"):
                return {"status": "fail", "message": f"Duty {action_id} is not scoped to {scope}"}
        return {"status": "pass", "message": "State check passed for duty"}
    
    roles = Agent.objects(uid=agent_id).first()
    roles = roles.roles
    for role in roles:
        db_role = Role.objects(uid=role["role_id"]).first()
        temporary_powers = db_role.temporary_powers if db_role else {}
        if action_id in temporary_powers.keys():
            expire_at = temporary_powers[action_id].get("expire_at")
            if expire_at and datetime.fromisoformat(expire_at) < datetime.now():
                return {"status": "fail", "message": f"Temporary power {action_id} has expired"}
            if scope != temporary_powers[action_id].get("scope"):
                return {"status": "fail", "message": f"Temporary power {action_id} is not scoped to {scope}"}
            return {"status": "pass", "message": "State check passed for temporary power found"}
    
    if agent_duty_exist:
        return {"status": "pass", "message": "no power found but duty exists, state check passed"}
                 
    # print(f"🧭 State Checker: Agent {agent_id} is allowed to perform action {action_id}")
    return {"status": "", "message": ""}