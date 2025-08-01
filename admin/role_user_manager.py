# role manager
# assign role
# delete role
# manage role

#create agent
#assign role to agent
#delete agent

# from mongoengine import connect
from database.models import Agent, Role, AgentRoleRelation, Power, Duty, AgentPowerRelation, AgentDutyRelation, RoleStateEnum
from datetime import datetime
from database import connection
connection.connect_to_mongo()


def create_agent(agents):
    msg = ""
    for agent in agents:
        agent_id = agent.get("uid")
        agent_name = agent.get("agent_name")
        if not agent_id or not agent_name:
            print("❌ Agent UID and Name are required.")
            msg += f'fail to create agent{agent};'
            continue

        existing_agent = Agent.objects(uid=agent_id).first()
        if existing_agent:
            print(f"❌ Agent with UID {agent_id} already exists, skip.")
            msg += f'Agent with UID {agent_id} already exists, skip;'
        else:
            Agent(uid=agent_id, agent_name=agent_name, roles=[]).save()
            print(f"✅ Agent {agent_name} created successfully with UID {agent_id}.")
            msg+= f'Agent {agent_name} created with UID {agent_id};'
        if agent.get("roles"):
            for role in agent["roles"]:
                result = assign_role_to_agent(agent_id, role)
                if result["status"] == "error":
                    msg+=result["message"]
                else:
                    msg+=f'Agent {agent_name} successfully assigned role {role};'
    return {"status":"finished", "message": msg}

def delete_agent(agent_uid: str):
    msg = ""
    agent = Agent.objects(uid=agent_uid).first()
    if not agent:
        print(f"❌ Agent with UID {agent_uid} does not exist.")
        return {"status": "error", "message": f"Agent with UID {agent_uid} does not exist."}

    # 从数据库删除 Agent
    try:
        agent.delete()
        print(f"✅ Agent {agent.agent_name} deleted successfully.")
        msg += f'Agent {agent.agent_name} deleted;'
    except Exception as e:
        print(f"❌ Failed to delete Agent: {e}")
        msg += f'fail to delete Agent {agent.agent_name};'
        return {"status": "error", "message": f"Failed to delete Agent, detail:{e}"}
    
    power_relation = AgentPowerRelation.objects(uid=agent.uid).first()
    duty_relation = AgentDutyRelation.objects(uid=agent.uid).first()
    if power_relation:
        try:
            power_relation.delete()
            print(f"✅ PowerRelation for Agent {agent.agent_name} deleted successfully.")
            msg += f'PowerRelation for Agent {agent.agent_name} deleted;'
        except Exception as e:
            print(f"❌ Failed to delete PowerRelation: {e}")
            msg += f'fail to delete PowerRelation for Agent {agent.agent_name},detail:{e};'
            return {"status": "error", "message": msg}
    if duty_relation:
        try:
            duty_relation.delete()
            print(f"✅ DutyRelation for Agent {agent.agent_name} deleted successfully.")
            msg += f'DutyRelation for Agent {agent.agent_name} deleted;'
        except Exception as e:
            print(f"❌ Failed to delete DutyRelation: {e}")
            msg += f'fail to delete DutyRelation for Agent {agent.agent_name},detail:{e};'
            return {"status": "error", "message": msg}
    print(f"✅ Agent {agent.agent_name} and all related relations deleted successfully.")
    # msg += f'Agent {agent.agent_name} and all related relations deleted;'
    return {"status": "success", "message": msg}

    

    return {"status": "success", "message": msg}

def update_agent(agent_uid: str, agent_name: str, roles: list = None):
    msg = ""
    agent = Agent.objects(uid=agent_uid).first()
    if not agent:
        print(f"❌ Agent with UID {agent_uid} does not exist.")
        return {"status": "error", "message": f"Agent with UID {agent_uid} does not exist."}

    # 更新 Agent 的名称
    agent.agent_name = agent_name
    try:
        agent.save()
        print(f"✅ Agent {agent.agent_name} updated successfully.")
        msg += f'Agent {agent.agent_name} updated;'
    except Exception as e:
        print(f"❌ Failed to save Agent: {e}")
        msg += f'fail to save Agent {agent.agent_name};'
        return {"status": "error", "message": f"Failed to save Agent, detail:{e}"}

    # 更新角色
    if roles:
        for role in roles:
            result = assign_role_to_agent(agent_uid, role)
            if result["status"] == "error":
                msg += result["message"]
            else:
                msg += f'Agent {agent.agent_name} successfully assigned role {role};'

    return {"status": "success", "message": msg}

#后续加上检查role state的逻辑
def assign_role_to_agent(agent_uid: str, role_uid: str):
    msg = ""
    agent = Agent.objects(uid=agent_uid).first()
    role = Role.objects(uid=role_uid).first()

    if not agent or not role:
        print("❌ Agent 或 Role 不存在")
        return {"status": "error", "message": "Agent or Role does not exist."}
 
    existing_roles =  [r.role_id for r in agent.roles]
    power_relation = AgentPowerRelation.objects(uid=agent.uid).first()
    duty_relation = AgentDutyRelation.objects(uid=agent.uid).first()

    if not existing_roles:
        agent.roles.append(
        AgentRoleRelation(
            role_id= role.uid,
            created_at=str(datetime.now()),  # 示例创建时间
            expire_at=None,  # 示例过期时间
            state = RoleStateEnum.active  # 示例状态
        ))
        try:
            agent.save()
            print(f"✅ Create AgentRoleRelation bound:{agent.uid} → {role.role_name}")
            msg += f'AgentRoleRelation bound:{agent.uid} → {role.role_name};'
        except Exception as e:
            print(f"❌ Failed to save Agent: {e}")
            msg += f'fail to save Agent {agent.agent_name};'
            return {"status": "error", "message": f"Failed to save Agent, detail:{e}"}
        print(f"✅ Agent {agent.agent_name} saved successfully.")
    else:
        if role.uid not in existing_roles:
            agent.roles.append(
                AgentRoleRelation(
                    role_id=role.uid,
                    created_at=str(datetime.now()),  # 示例创建时间
                    expire_at=None,  # 示例过期时间
                    state=RoleStateEnum.active  # 示例状态
                ))     
            try:
                agent.save()
                print(f"🔁 Assign new role {agent.uid} += {role.role_name}")
                msg += f'Assign new role {agent.uid} += {role.role_name};'
            except Exception as e:
                print(f"❌ Failed to save Agent: {e}")
                msg += f'fail to save Agent {agent.agent_name};'
                return  {"status": "error", "message": f"Failed to save Agent, detail:{e}"}
            print(f"✅ Agent {agent.uid} saved successfully.")          
        else:
            print(f"⬆️ Agent {agent_uid} has been assigned role:{role.role_name}")
            msg+= f'Agent {agent.agent_name} has been assigned role:{role.role_name};'

    # 2. 为 Agent 分配 Role 的 Powers 和 Duties
    if not power_relation:
        power_relation = AgentPowerRelation(uid=agent.uid, agent_name=agent.agent_name, powers={})
        existing_power = []
    else:
        existing_power = [p for p in power_relation.powers.keys()]

    if not duty_relation:
        duty_relation = AgentDutyRelation(uid=agent.uid, agent_name=agent.agent_name, duties={})
        existing_duty = []
    else:
        existing_duty = [d for d in duty_relation.duties.keys()]

    for duty in role["duties"]:
        duty_id = duty["duty_id"]
        action = Duty.objects(uid=duty_id).first()
        if not action:
            print(f"❌ Duty {d}'s Action ID could not be found.")
            msg += f'fail to find duty {duty_id},skip;'
            continue
        if existing_duty and duty_id in existing_duty:
            # cur_duty = str(duty["duty_id"])
            print(f"⬆️ Updating current Duty: {duty_id}")
            duty_relation.duties[duty_id]["counterparty_role_id"] = duty["counterparty_role_id"]
            duty_relation.duties[duty_id]["state"] = duty["initial_state"]
            duty_relation.duties[duty_id]["assigned_by"] = "role_system"
            duty_relation.duties[duty_id]["action_id"] = action.uid
            duty_relation.duties[duty_id]["scope"] = duty["scope"]
            duty_relation.save()
               # duty_relation.duties.remove(duty)  # Remove existing duty before adding again
            continue
        action_id = action.uid
        d={"counterparty_role_id": duty["counterparty_role_id"],"assigned_by": "role_system", 
           "state": duty["initial_state"],"action_id":action_id,"scope":duty["scope"]}  # Use a dict to store duty details
        duty_relation.duties[duty_id] = d  # Use duty.duty_id as key
        try:
            duty_relation.save()
            print(f"✅ Create AgentDutyRelation:{agent.uid} → {duty_id}")
            msg += f'Create AgentDutyRelation:{agent.uid} → {duty_id};'
        except Exception as e:
            print(f"❌ Failed to save AgentDutyRelation: {e}")
            msg += f'fail to save AgentDutyRelation {agent.agent_name};'
            return {"status": "error", "message": f"Failed to save AgentDutyRelation, detail:{e}"}
    

    for power in role["powers"]: 
        power_id = power["power_id"]  
        action = Power.objects(uid=power_id).first()
        if not action:
            print(f"❌ Power {power_id}'s Action ID could not be found.")
            msg += f'fail to find power {power_id},skip;'
            continue
        if existing_power and power_id in existing_power:
            # cur_power = str(power["power_id"])
            print(f"⬆️ Updating current Power: {power_id}")
            power_relation.powers[power_id]["state"] = power["initial_state"]
            power_relation.powers[power_id]["assigned_by"] = "role_system"
            power_relation.powers[power_id]["action_id"] = action.uid
            power_relation.powers[power_id]["scope"] = power["scope"]
            power_relation.save()
            continue
        action_id = action.uid
        p = {"state": power["initial_state"], "assigned_by": "role_system", "action_id": action_id,"scope":power["scope"]}  # Use a dict to store power details
        power_relation.powers[power_id] = p
        try:
            power_relation.save()
            print(f"✅ Create AgentPowerRelation:{agent.uid} → {power_id}")
            msg += f'Create AgentPowerRelation:{agent.uid} → {power_id};'
        except Exception as e:
            print(f"❌ Failed to save AgentPowerRelation: {e}")
            msg += f'fail to save AgentPowerRelation {agent.agent_name};'
            return {"status": "error", "message": f"Failed to save AgentPowerRelation, detail:{e}"}
    return {"status": "success", "message": msg}

def remove_role_from_agent(agent_uid: str, role_uid: str):
    msg = ""
    agent = Agent.objects(uid=agent_uid).first()
    if not agent:
        print(f"❌ Agent with UID {agent_uid} does not exist.")
        return {"status": "error", "message": f"Agent with UID {agent_uid} does not exist."}

    existing_roles = [r.role_id for r in agent.roles]
    if role_uid not in existing_roles:
        print(f"❌ Role {role_uid} is not assigned to Agent {agent_uid}.")
        return {"status": "error", "message": f"Role {role_uid} is not assigned to Agent {agent_uid}."}

    # Remove the role from the agent's roles
    agent.roles = [r for r in agent.roles if r.role_id != role_uid]
    try:
        agent.save()
        print(f"✅ Role {role_uid} removed from Agent {agent_uid}.")
        msg += f'Role {role_uid} removed from Agent {agent_uid};'
    except Exception as e:
        print(f"❌ Failed to save Agent: {e}")
        msg += f'fail to save Agent {agent.agent_name};'
        return {"status": "error", "message": f"Failed to save Agent, detail:{e}"}

    # Optionally, remove the powers and duties associated with the role
    power_relation = AgentPowerRelation.objects(uid=agent.uid).first()
    duty_relation = AgentDutyRelation.objects(uid=agent.uid).first()
    role = Role.objects(uid=role_uid).first()
    power_delete = role.powers if role else []
    duty_delete = role.duties if role else []
    if power_relation and power_delete:
        for p in power_delete:
            power_id = p.get("power_id")
            if power_id in power_relation.powers:
                del power_relation.powers[power_id]
                print(f"✅ Power {power_id} removed from Agent {agent_uid}.")
                msg += f'Power {power_id} removed;'
            else:
                print(f"❌ Power {power_id} not found in Agent {agent_uid}.")
                msg += f'Related Power {power_id} not found in Agent {agent_uid};'
        try:
            power_relation.save()
            print(f"✅ Powers associated with Role {role_uid} removed from Agent {agent_uid}.")
            msg += f'Powers associated with Role {role_uid} removed from Agent {agent_uid};'
        except Exception as e:
            print(f"❌ Failed to save PowerRelation: {e}")
            msg += f'fail to save PowerRelation for Agent {agent.agent_name};'
            return {"status": "error", "message": f"Failed to save PowerRelation, detail:{e}"}

    if duty_relation and duty_delete:
        for d in duty_delete:
            duty_id = d.get("duty_id")
            if duty_id in duty_relation.duties:
                del duty_relation.duties[duty_id]
                print(f"✅ Duty {duty_id} removed from Agent {agent_uid}.")
                msg += f'Duty {duty_id} removed;'
            else:
                print(f"❌ Duty {duty_id} not found in Agent {agent_uid}.")
                msg += f'Related Duty {duty_id} not found in Agent {agent_uid};'
        try:
            duty_relation.save()
            print(f"✅ Duties associated with Role {role_uid} removed from Agent {agent_uid}.")
            msg += f'Duties associated with Role {role_uid} removed from Agent {agent_uid};'
        except Exception as e:
            print(f"❌ Failed to save DutyRelation: {e}")
            msg += f'fail to save DutyRelation for Agent {agent.agent_name};'
            return {"status": "error", "message": f"Failed to save DutyRelation, detail:{e}"}
    return {"status": "success", "message": msg}
                                
# msg = create_agent([{"uid": "agent1", "agent_name": "Agent1", "roles": ["doctor_hospital_1","patient_hospital_1"]},])
# print(msg)
# assign_role_to_agent("agent1", "doctor_hospital_1")
# msg = remove_role_from_agent("agent1", "doctor_hospital_1")
# print(msg)
# msg = delete_agent("agent1")
# print(msg)

# assign_role_to_agent("Bob001", "doctor_hospital_1")
# assign_role_to_agent("Alice001", "patient_hospital_1")