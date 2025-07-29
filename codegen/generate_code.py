from jinja2 import Environment, FileSystemLoader
from database.models import Action, Power , Duty, Role, Violation
import re

# 加载模板
env = Environment(loader=FileSystemLoader("codegen/template"))
template = env.get_template("action_handler_async.py.j2")

def parse_rule_component(component_str: str) -> dict:
    """
    解析 "+ duty send_data" 或 "- power revoke_access"
    返回：{type: 'duty', id: 'send_data', operation: 'activate'}
    """
    match = re.match(r'([+-])\s*(duty|power)\s+(\w+)', component_str.strip())
    if not match:
        return {}
    
    op_sign, comp_type, comp_id = match.groups()
    return {
        "type": comp_type,
        "id": comp_id,
        "operation": "activate" if op_sign == "+" else "deactivate"
    }
# 'rules': [{'leads_to': '+ power send_data', 'state': '+ duty send_data'}],
def generate_rules(rules):
    state_info = parse_rule_component(rules.get("state", ""))
    leads_to_info = parse_rule_component(rules.get("leads_to", ""))
    print(f"State Info: {state_info}, Leads To Info: {leads_to_info}")
    
# generate_rules({'leads_to': '+ power send_data', 'state': '+ duty send_data'})


def generate_action_handler(*,template,action_id,action_type,action_scope,operation):
    output = template.render(
        action_id= action_id,
        action_type= action_type,
        action_scope= action_scope,
        operations= operation,
    )
    filename = f'codegen/handlers/{action_type}_handler.py'
    with open(filename, "w") as f:
        f.write(output)

    print(f"✅ Generate handler:{filename}")

def store_role(roles):
    msg=""
    for role in roles:
        # 若是 Pydantic 模型，先转 dict
        try:
            data = role.dict() if hasattr(role, 'dict') else role

            role_id = data["uid"]
            role_name = data["role_name"]
            description = data.get("description")
            powers = data.get("powers", [])
            duties = data.get("duties", [])
            scope = data.get("scope")
            print(scope)

            db_role = Role.objects(uid=role_id).first()

            if db_role:
                print(f"⬆️ Role {role_id} exists, Updating Role")
                msg += f"Role {role_id} exists, Updating Role;"
                new_powers = []
                new_duties = []

                for power in powers:
                    try:
                        power_id = power.get("power_id")
                        db_power = Power.objects(uid=power_id).first()
                        if not db_power:
                            print(f"❌ Power {power_id} does not exist, skipping")
                            msg+= f"Power {power_id} does not exist, skipping;"
                            continue
                        new_powers.append(power)
                    except Exception as e:
                        print(f"❌ Error processing power {power}: {e}")
                        msg+= f"Error processing power {power}: {e};"
                        continue

                for duty in duties:
                    try:
                        duty_id = duty.get("duty_id")
                        db_duty = Duty.objects(uid=duty_id).first()
                        if not db_duty:
                            print(f"❌ Duty {duty_id} does not exist, skipping")
                            msg+= f"Duty {duty_id} does not exist, skipping;"
                            continue
                        new_duties.append(duty)
                    except Exception as e:
                        print(f"❌ Error processing duty {duty}: {e}")
                        msg+= f"Error processing duty {duty}: {e};"
                        continue

                db_role.role_name = role_name
                db_role.description = description
                db_role.scope = scope
                db_role.powers = new_powers
                db_role.duties = new_duties
                db_role.save()

            else:
                print(f"✅ Create new role: {role_id}")
                msg += f"Create new role: {role_id};"
                new_powers = []
                new_duties = []

                for power in powers:
                    try:
                        power_id = power.get("power_id")
                        db_power = Power.objects(uid=power_id).first()
                        if not db_power:
                            print(f"❌ Power {power_id} does not exist, skipping")
                            msg+= f"Power {power_id} does not exist, skipping;"
                            continue
                        print(f"✅ Add power {power_id} to role {role_id}")
                        new_powers.append(power)
                    except Exception as e:
                        print(f"❌ Error processing power {power}: {e}")
                        msg+= f"Error processing power {power}: {e};"
                        continue

                for duty in duties:
                    try:
                        duty_id = duty.get("duty_id")
                        db_duty = Duty.objects(uid=duty_id).first()
                        if not db_duty:
                            print(f"❌ Duty {duty_id} does not exist, skipping")
                            msg+= f"Duty {duty_id} does not exist, skipping;"
                            continue
                        print(f"✅ Add duty {duty_id} to role {role_id}")
                        new_duties.append(duty)
                    except Exception as e:
                        print(f"❌ Error processing duty {duty}: {e}")
                        msg+= f"Error processing duty {duty}: {e};"
                        continue

                try:
                    Role(uid=role_id,
                    role_name=role_name,
                    description=description,
                    scope=scope,
                    powers=new_powers,
                    duties=new_duties
                    ).save()
                    print(f"✅ Create new role: {role_id}")
                    msg += f"Create new role: {role_id};"
                except Exception as e:
                    print(f"❌ Fail to save role: {e}")
                    msg+= f"Fail to save role: {e};"
                    continue
        except Exception as e:
            print(f"❌ Error storing role {role_id}, detail:{e}")
            msg += f"Error storing role {role_id}, detail:{e};"
            continue
    return {"status": "finished",
        "message": msg}

def store_action(actions):
    msg = ""
    for action in actions:
        try:
            data = action.dict() if hasattr(action, 'dict') else action
            action_id = data.get("uid")
            action_type = data.get("action_type").replace("#", "")
            consequence = data.get("consequence", {})

            db_action = Action.objects(uid=action_id).first()
            if db_action:
                print(f"⬆️ Action {action_id} exists, Updating Action")
                msg += f"Action {action_id} exists, Updating Action;"
                db_action.action_type = action_type
                db_action.consequence = consequence
                try:
                    db_action.save()
                except Exception as e:
                    print(f"❌ Fail to update Action: {e}")
                    msg += f"Fail to update Action: {e};"
                    continue
            else:
                try:
                    Action(uid=action_id, action_type=action_type, consequence=consequence).save()
                    print(f"✅ Create new action: {action_id}")
                    msg += f"Create new action: {action_id};"
                except Exception as e:
                    print(f"❌ Fail to save Action: {e}")
                    return {"message": f"Fail to save Action: {e}"}
        except Exception as e:
            print(f"❌ Error storing action {action_id}, detail:{e}")
            msg += f"Error storing action {action_id}, detail:{e};"
            continue
    return {"status": "finished",
            "message": msg}

def store_power(powers):
    msg = ""
    for power in powers:
        try:
            data = power.dict() if hasattr(power, 'dict') else power
            power_id = data.get("uid")
            action_type = data.get("action_type").replace("#", "")
            action_id = data.get("action_id")

            db_action = Action.objects(uid=action_type).first()
            
            if not db_action:
                print(f"❌ Action {action_type} does not exist, skipping power {power_id}")
                msg += f"Action {action_type} does not exist, skipping power {power_id};"
                continue

            db_power = Power.objects(uid=power_id).first()
            if db_power:
                print(f"⬆️ Power {power_id} exists, Updating Power")
                msg += f"Power {power_id} exists, Updating Power;"
                db_power.action_type = action_type
                db_power.action_id = action_id
                try:
                    db_power.save()
                    print(f"✅ Power {power_id} updated")
                    msg += f"Power {power_id} updated;"
                except Exception as e:
                    print(f"❌ Fail to update power: {e}")
                    msg += f"Fail to update power: {e};"
                    continue
            else:
                try:
                    Power(uid=power_id, action_type=action_type, action_id=action_id).save()
                    msg+= f"Create new power: {power_id};"
                    print(f"✅ Create new power: {power_id}")
                except Exception as e:
                    print(f"❌ Fail to save power{power_id}: {e}")
                    msg += f"Fail to save power{power_id}, detail:{e};"
                    continue
        except Exception as e:
            print(f"❌ Error storing power {power_id}, detail:{e}")
            msg += f"Error storing power {power_id}, detail:{e};"
            continue
    return {"status": "finished",
            "message": msg}

def store_duty(duties):
    msg = ""
    for duty in duties:
        data = duty.dict() if hasattr(duty, 'dict') else duty
        duty_id = data.get("uid")
        action_type = data.get("action_type").replace("#", "")
        action_id = data.get("action_id")
        violation_id = data.get("violation_id")
        # counterparty_role_id = data.get("counterparty_role_id")
        # print(f"✅ Create duty: {duty_id}")
        db_action = Action.objects(uid=action_type).first()
        
        if not db_action:
            print(f"❌ Action {action_type} does not exist, skipping duty {duty_id}")
            msg += f"Action {action_type} does not exist, skipping duty {duty_id};"
            continue
        db_duty = Duty.objects(uid=duty_id).first()
        if db_duty:
            print(f"⬆️ Duty {duty_id} exists, Updating Duty")
            db_duty.action_type = action_type
            db_duty.action_id = action_id
            db_duty.violation_id = violation_id
            # db_duty.counterparty_role_id = counterparty_role_id
            try:
                db_duty.save()
                msg += f"Duty {duty_id} updated;"
            except Exception as e:
                print(f"❌ Fail to update Duty: {e}")
                msg += f"Fail to update Duty: {e};"
                continue
            continue
        else:
            try:
                Duty(uid=duty_id, action_type=action_type, action_id=action_id,violation_id=violation_id).save()
                print(f"✅ Create new duty: {duty_id}")
                msg += f"Create new duty: {duty_id};"
            except Exception as e:
                print(f"❌ Fail to save duty{duty_id}: {e}")
                msg += f"Fail to save duty{duty_id}, detail:{e};"
                continue
    return {"status": "finished",
            "message": msg}

def store_violation(violations):
    msg = ""
    for violation in violations:
        data = violation.dict() if hasattr(violation, 'dict') else violation
        violation_id = data.get("uid")
        condition = data.get("condition")
        consequence = data.get("consequence")
        db_violation = Violation.objects(uid=violation_id).first()
        if db_violation:
            print(f"⬆️ Violation {violation_id} exists, Updating Violation")
            msg += f"Violation {violation_id} exists, Updating Violation;"
            db_violation.condition = condition
            db_violation.consequence = consequence
            try:
                db_violation.save()
                print(f"✅ Violation {violation_id} updated")
                msg += f"Violation {violation_id} updated;"
            except Exception as e:
                print(f"❌ Fail to update Violation: {e}")
                msg += f"Fail to update Violation: {e};"
                continue
            continue
        else:
            try:
                Violation(uid=violation_id, condition=condition,consequence=consequence).save()
                print(f"✅ Create new violation: {violation_id}")
                msg += f"Create new violation: {violation_id};"
            except Exception as e:
                print(f"❌ Fail to save Violation: {e}")
                msg += f"Fail to save Violation: {e};"
                continue     
    return {"status": "finished",
            "message": msg}


# store_power(config["power"])

# with open("./config/example_action.json") as f:
# with open("./config/example_power.json") as f:
# with open("./config/example_violation.json") as f:
# with open("./config/example_duty.json") as f:
# with open("./config/example_role.json") as f:
    # config = json.load(f)
# store_action(config["actions"])
# store_power_only(config["powers"])
# store_violation(config["violations"])
# store_duty_only(config["duties"])
# store_role(config["roles"])



# generate_action_handler(
#     template=template,
#     action_id="grant_consent",
#     action_type="grant_consent",
#     action_scope= "hospital_1",
#     operation=[
#         {
#                 "type": "add_power",
#                 "parameter": {
#                     "power_id": "share_data",
#                     "target_role_id": "from_request",
#                     "target_agent_id": "from_request",
#                     "scope": "from_request",
#                     "item": "requester.data",
#                     "duration": "10d"
#                 }
#             }
#     ]
# )

# generate_action_handler(
#     template=template,
#     action_id="share_data",
#     action_type="share_data",
#     action_scope= "hospital_1",
#     operation=[
#         {
#             "type": "notify",
#             "parameter": {
#                 "message": "{requester_id} shared data {item} with {target_agent_id},{target_role_id}",
#                 "target_role_id": "from_request",
#                 "target_agent_id": "from_request",
#                 "item":"from_request"
#             }
#         }
#     ]
# )

# generate_action_handler(
#     template=template,
#     action_id="create_data",
#     action_type="create_data",
#     action_scope= "hospital_2",
#     operation=[
#         {
#             "type": "notify",
#             "parameter": {
#                 "message": "new data of {target_agent_id} created by doctor",
#                 "target_agent_id": "target_agent_id"
#             }
#         }
#     ]
# )

# generate_action_handler(
#     template=template,
#     action_id="create_data",
#     action_type="create_data",
#     action_scope= "hospital_1",
#     operation=[
#         {
#             "type": "notify",
#             "parameter": {
#                 "message": "new data of {target_agent_id} created by doctor",
#                 "target_agent_id": "from_request",
#             }
#         }
#     ]
# )

# generate_action_handler(
#     template=template,
#     action_id="request_access",
#     action_type="request_access",
#     action_scope= "hospital_1",
#     operation=[
#         {
#             "type": "activate_duty",
#             "parameter": {
#                 "duty_id": "send_data",
#                 "counterparty_role_id": "doctor_hospital_1"
#             }
#         }
#     ]
# )
# generate_action_handler(
#     template=template,
#     action_id="send_data",
#     action_type="send_data",
#     action_scope= "hospital_1",
#     operation=[
#     {
#         "type": "notify",
#         "parameter": {
#             "message": "data sent to {target_agent_id} by {requester_id}",
#             "target_agent_id": "from_request"
#         }
#             }
#     ]
# )