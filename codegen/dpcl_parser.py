# Re-inject DPCL input samples
dpcl_text_input_1 = """ power log_access{
    holder: patient
    action: #log_access
    consequence: "log success"
}
"""

dpcl_text_input_2 = """power send_data{
    holder: doctor
    action: #send_data
    consequence: +power log_access {
        holder: patient
        action: #log_access
        consequence: "log success"
    }
}
"""

dpcl_text_input_3 = """power request_data{
    holder: patient
    action: #request_data
    consequence: {+duty send_data{
			holder: hospital 
			counterparty: patient 
			action: #send_data 
			consequence: "data sent"
			violation: {condition: {"timeout":"72h"}}
            }
            + power p1{
                action: #p1_action
                holder: hospital
                consequence: "p1 action executed"
            }
            }
    }
    + duty send_data -> + power send_data{
        action: #send_data
        consequence: "data sent"
        holder: hospital               
    }
    + duty send_data.violation => +power report_fine{
    holder: patient 
    action:#report_fine
    consequence: "fine issued"
    }
}
"""
import re
from typing import Dict, Any, List, Tuple
import json

def clean(val: str) -> str:
    return val.strip().strip('"').strip().replace("#", "")

# def strip_block_body(block: str) -> str:
    match = re.match(r'(\s*\+\s*(duty|power)\s+\w+\s*\{)', block)
    if not match:
        return block  # fallback: return original
    prefix = match.group(1)
    return f"{prefix}}}"

# ----------- Block Extractors -----------
def extract_blocks_by_prefix(text: str, prefix_pattern: str) -> List[str]:
    pattern = re.compile(prefix_pattern)
    blocks = []
    start = 0
    while True:
        match = pattern.search(text, pos=start)
        if not match:
            break
        i = match.end() - 1
        stack = ['{']
        j = i + 1
        while j < len(text) and stack:
            if text[j] == '{':
                stack.append('{')
            elif text[j] == '}':
                stack.pop()
            j += 1
        blocks.append(text[match.start():j])
        start = j
    return blocks

def extract_power_blocks(text: str) -> List[str]:
    return extract_blocks_by_prefix(text, r'power\s+\w+\s*\{')

def extract_transformational_blocks(text: str) -> List[str]:
    return extract_blocks_by_prefix(text, r'\+ duty\s+\w+\s*->\s*\+ power\s+\w+\s*\{')

def extract_reactive_blocks(text: str) -> List[str]:
    return extract_blocks_by_prefix(text, r'\+ duty\s+\w+\.violation\s*=>\s*\+power\s+\w+\s*\{')

# safely extract the consequence block (not the nested consequence)
import re

def strip_all_blocks(text: str) -> str:
    result = ""
    pattern = re.compile(r'(\+\s*(duty|power)\s+\w+\s*\{)')
    start = 0

    while True:
        match = pattern.search(text, start)
        if not match:
            result += text[start:]
            break

        # 追加前面的非 block 部分
        result += text[start:match.start()]

        # 捕获 block 开头
        header = match.group(1)
        i = match.end()
        stack = ['{']
        block_content = ""

        while i < len(text) and stack:
            if text[i] == '{':
                stack.append('{')
            elif text[i] == '}':
                stack.pop()
            block_content += text[i]
            i += 1

        # 提取 holder 和 counterparty 字段
        holder_match = re.search(r'holder\s*:\s*([^\n{}]+)', block_content)
        counterparty_match = re.search(r'counterparty\s*:\s*([^\n{}]+)', block_content)

        lines = []
        if holder_match:
            lines.append(f"    holder: {holder_match.group(1).strip()}")
        if counterparty_match:
            lines.append(f"    counterparty: {counterparty_match.group(1).strip()}")

        result += header + "\n" + "\n".join(lines) + "\n}"

        start = i

    return result


def extract_consequence_block(text: str) -> str:
    match = re.search(r'consequence\s*:\s*', text)
    if not match:
        return ""
    start = match.end()
    stack = []
    i = start
    while i < len(text):
        if text[i] == '{':
            stack.append('{')
        elif text[i] == '}':
            if stack:
                stack.pop()
            else:
                break
        elif text[i] == '\n' and not stack:
            break
        i += 1
    return strip_all_blocks(text[start:i].strip())



# ----------- Consequence Parser -----------

def parse_consequence_block(text: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    operations = []
    duties = []
    powers = []

    # Match duty
    for match in re.finditer(r'([+-])\s*duty\s+(\w+)\s*\{([\s\S]*?)\}', text):
        sign, duty_id, body = match.groups()
        fields = dict(re.findall(r'(\w+)\s*:\s*("?[^"\n{}]+"?)', body))
        # if not fields or all(v.strip() == "" for v in fields.values()):
        #     continue  # skip empty duty block

        action_id = clean(fields.get("action", duty_id))
        counterparty = clean(fields.get("counterparty", ""))
        op_type = "activate_duty" if sign == '+' else "deactivate_duty"
        operations.append({
            "type": op_type,
            "parameter": {
                "duty_id": clean(duty_id),
                "counterparty_role_id": counterparty
            }
        })
        duties.append({
            "uid": clean(duty_id),
            "action_type": f"#{action_id}",
            "action_id": action_id,
            "violation_id": f"v_{duty_id}"
        })
        # operations.append({
        #     "type": "notify",
        #     "message": clean(fields.get("consequence", ""))
        # })

    # Match power
    for match in re.finditer(r'([+-])\s*power\s+(\w+)\s*\{([\s\S]*?)\}', text):
        sign, power_id, body = match.groups()
        fields = dict(re.findall(r'(\w+)\s*:\s*("?[^"\n{}]+"?)', body))
        # if not fields or all(v.strip() == "" for v in fields.values()):
        #     continue  # skip empty power block
        action_id = clean(fields.get("action", power_id))
        holder = clean(fields.get("holder", ""))
        op_type = "activate_power" if sign == '+' else "deactivate_power"
        operations.append({
            "type": op_type,
            "parameter": {
                "power_id": clean(power_id),
                "target_role_id": holder
            }
        })
        powers.append({
            "uid": clean(power_id),
            "action_type": f"#{action_id}",
            "action_id": action_id
        })
        # operations.append({
        #     "type": "notify",
        #     "message": clean(fields.get("consequence", ""))
        # })

    # Match remaining string notification
    cleaned = re.sub(r'([+-])\s*(duty|power)\s+\w+\s*\{[\s\S]*?\}', '', text)
    for match in re.finditer(r'"([^"\n]+)"', cleaned):
        msg = match.group(1).strip()
        if msg:
            operations.append({
                "type": "notify",
                "parameter": {
                "message": msg}
            })
    return operations, duties, powers

# ----------- Block Parsers -----------

def extract_outer_action(body: str) -> str:
    match = re.search(r'action\s*:\s*#?(\w+)', body)
    return clean(match.group(1)) if match else ""

def parse_main_power_block(block: str) -> Dict[str, Any]:
    match = re.search(r'power\s+(\w+)\s*\{([\s\S]*)\}', block)
    if not match:
        return {"powers": [], "actions": [], "duties": []}
    uid, body = match.groups()
    action_id = extract_outer_action(body)

    powers = [{
        "uid": clean(uid),
        "action_type": f"#{action_id}",
        "action_id": action_id
    }]

    consequence_text = extract_consequence_block(body) if "consequence" in body else ""
    # pprint(consequence_text)
    operations, duties, extra_powers = parse_consequence_block(consequence_text)

    action = {
        "uid": action_id,
        "action_type": f"#{action_id}",
        "consequences": {"operation": operations}
    }

    return {
        "powers": powers + extra_powers,
        "actions": [action],
        "duties": duties
    }

def extract_transformation_states(block: str) -> dict:
    """
    从 transformation block 中提取出 state 和 leads_to 两个组件。
    例如：+ duty send_data -> + power send_data
    返回 {"state": "+ duty send_data", "leads_to": "+ power send_data"}
    """
    match = re.match(r'\s*(\+ ?duty\s+\w+)\s*->\s*(\+ ?power\s+\w+)', block)
    if not match:
        return {}

    state, leads_to = match.groups()
    return {
        "state": state.strip(),
        "leads_to": leads_to.strip()
    }

def parse_transformational_block(block: str) -> Dict[str, Any]:
    match = re.search(r'\+ power\s+(\w+)\s*\{([\s\S]*?)\}', block)
    if not match:
        return {"powers": [], "actions": [], "duties": []}
    uid, body = match.groups()
    action_id = extract_outer_action(body)
    transformation_states = extract_transformation_states(block)
    # print(f"Transformation states: {transformation_states}")
    # print(match.groups())   

    powers = [{
        "uid": clean(uid),
        "action_type": f"#{action_id}",
        "action_id": action_id
    }]

    operations, duties, extra_powers = parse_consequence_block(body)

    action = {
        "uid": action_id,
        "action_type": f"#{action_id}",
        "consequences": {"operation": operations}
    }

    return {
        "powers": powers + extra_powers,
        "actions": [action],
        "duties": duties,
        "rules": [transformation_states]
    }

def extract_first_block_from(text: str, start: int) -> str:
    i = text.find('{', start)
    if i == -1:
        return ""
    stack = ['{']
    j = i + 1
    while j < len(text) and stack:
        if text[j] == '{':
            stack.append('{')
        elif text[j] == '}':
            stack.pop()
        j += 1
    return text[i:j]  # 包含大括号

def extract_condition_from_violation(full_block: str) -> dict:
    """
    从一个 duty block 的文本中，提取 violation.condition 字段的 dict 表达形式。
    """
    condition = {}

    # 1. 提取 violation 块 {...}
    v_match = re.search(r'violation\s*:\s*\{([\s\S]*?)\}', full_block)
    if not v_match:
        return {}

    v_body = v_match.group(1)

    # 2. 提取 condition 字段 {...}
    c_match = re.search(r'condition\s*:\s*(\{[\s\S]*?\})', v_body)
    if not c_match:
        return {}

    c_body = c_match.group(1).strip()

    # 3. 尝试解析为 JSON（标准或近似）
    try:
        # 标准 JSON 尝试（带引号）
        condition = json.loads(c_body)
        return condition
    except json.JSONDecodeError:
        pass  # 尝试下一种

    # 4. 非标准 key:value 格式 fallback（无引号）
    kvs = re.findall(r'(\w+)\s*:\s*"?([^",\n}]+)"?', c_body)
    if kvs:
        return {k.strip(): v.strip() for k, v in kvs}

    return {}

def parse_reactive_block(block: str, full_text: str) -> Dict[str, Any]:
    # print(f"Parsing reactive block: {block}")
    # print(f"Full text: {full_text}")
    match = re.search(r'\+ duty\s+(\w+)\.violation\s*=>\s*\+power\s+(\w+)', block)
    if not match:
        return {}

    duty_id, power_id = match.groups()

    # 提取 notify 消息
    notify = re.search(r'consequence\s*:\s*"([^"]+)"', block)
    notify_msg = notify.group(1) if notify else ""

    # 默认 condition
    condition = f"{duty_id}.violation"

    # 查找 violation block from full_text
    pattern = rf'\+\s*duty\s+{duty_id}\s*\{{'
    match_duty_block = re.search(pattern, full_text)
    # print(f"Match duty block: {match_duty_block}")
    if match_duty_block:
        full_block = extract_first_block_from(full_text, match_duty_block.start())
        # print("Extracted full block:", full_block)
        match_condition = re.search(r'condition\s*:\s*\{([\s\S]*?)\}', full_block)
        match_condition = match_condition.group(1) if match_condition else ""
        match_condition = "{"+ match_condition +"}"
        # print(f"Match condition block: {match_condition}")
        condition = match_condition
        try:
            condition = json.loads(match_condition)  # ✅ 解析成真正的 dict
        except json.JSONDecodeError:
            condition = {}
        # if match_condition:
        #     try:
        #         condition = json.loads(match_condition)
        #     except json.JSONDecodeError as e:
        #         print("⚠️ JSON decode failed:", e)
        #         condition = {"raw": match_condition}  # fallback to raw text
        # condition = extract_condition_from_violation(full_block)
        # 找 violation 块
        # v_match = re.search(r'violation\s*:\s*\{([\s\S]*?)\}', full_block)
        # print(f"Match violation block: {v_match}")
        # if v_match:
        #     v_body = v_match.group(1)
        #     fields = dict(re.findall(r'(\w+)\s*:\s*"?([^",\n}}]+)"?', v_body))
        #     if fields:
        #         condition = fields  # ✅ 正确赋值，不能漏掉冒号后面的语句
        # condition = f"{duty_id}.violation"  # fallback

        # v_match = re.search(r'violation\s*:\s*\{([\s\S]*?)\}', full_block)
        # if v_match:
        #     v_body = v_match.group(1)
        #     print("Raw violation body:", v_body)
        #     # 2. 直接提取 condition: {...}
        #     c_match = re.search(r'condition\s*:\s*(\{[\s\S]*?\})', v_body)
        #     print(f"Match condition block: {c_match}")
        #     if c_match:
        #         c_body = c_match.group(1)
        #         print("Raw condition body:", c_body)
        #         try:
        #             condition = json.loads(c_body)
        #         except json.JSONDecodeError as e:
        #             print("⚠️ JSON decode failed:", e)
        #             condition = {"raw": c_body}

    # pattern = rf'\+\s*duty\s+{duty_id}\s*\{{([\s\S]*?)\}}'
    # match_duty_block = re.search(pattern, full_text)
    # print(f"Match duty block: {match_duty_block}")
    # if match_duty_block:
    #     body = match_duty_block.group(1)
    #     v_match = re.search(r'violation\s*:\s*\{{([\s\S]*?)\}}', body)
    #     if v_match:
    #         v_body = v_match.group(1)
    #         fields = dict(re.findall(r'(\w+)\s*:\s*"?([^",\n}]+)"?', v_body))
    #         if fields:
    #             condition = fields
    # print(f"Condition: {condition}")
    return {
        "uid": f"v_{duty_id}",
        "condition": condition,
        "consequence": {
            "operation": [
                {"type": "activate_power", "power_id": clean(power_id)}
            ] + ([{"type": "notify", "message": notify_msg}] if notify_msg else [])
        }
    }

# ----------- Entry Point -----------

def parse_dpcl_full(text: str) -> Dict[str, Any]:
    result = {"powers": [], "actions": [], "duties": [], "violations": [], "rules": []}

    for blk in extract_power_blocks(text):
        parsed = parse_main_power_block(blk)
        result["powers"] += parsed["powers"]
        result["actions"] += parsed["actions"]
        result["duties"] += parsed["duties"]

    for blk in extract_transformational_blocks(text):
        parsed = parse_transformational_block(blk)
        result["powers"] += parsed["powers"]
        result["actions"] += parsed["actions"]
        result["duties"] += parsed["duties"]
        result["rules"] += parsed.get("rules", [])

    # for blk in extract_reactive_blocks(text):
    #     parsed = parse_reactive_block(blk)
    #     if parsed:
    #         result["violations"].append(parsed)
    for blk in extract_reactive_blocks(text):
        parsed = parse_reactive_block(blk, text)
        if parsed:
            result["violations"].append(parsed)



    result["actions"] = list({a["uid"]: a for a in result["actions"]}.values())
    result["powers"] = list({p["uid"]: p for p in result["powers"]}.values())
    result["duties"] = list({d["uid"]: d for d in result["duties"]}.values())

    # Remove empty lists
    if not result["powers"]:
        del result["powers"]
    if not result["actions"]:
        del result["actions"]
    if not result["duties"]:
        del result["duties"]
    if not result["violations"]:
        del result["violations"]
    return result

from pprint import pprint
# parse_dpcl_full(dpcl_text_input_3)
# pprint(parse_dpcl_full(dpcl_text_input_3))
# pprint(parse_dpcl_full("""power request_data{
#     holder: patient
#     action: #request_data
#     consequence: +duty send_data{
# 			holder: hospital 
# 			counterparty: patient 
# 			action: #send_data 
# 			consequence: "data sent"
# 			violation: {condition: {timeout":"72h"}}
#             }
#     }
#     + duty send_data -> + power send_data{
#         action: #send_data
#         consequence: "data sent"
#         holder: hospital               
#     }
#     + duty send_data.violation => +power report_fine{
#     holder: patient 
#     action:#report_fine
#     consequence: "fine issued"
#     }
# """))
# Run parser again
# dpcl_text_input_3 = """power request_data{
#     holder: patient
#     action: #request_data
#     consequence: +duty send_data{
#         holder: hospital 
#         counterparty: patient 
#         action: #send_data 
#         consequence: "data sent"
#         violation: {condition: {"timeout":"75h"}}
#     }
# }
#     + duty send_data -> + power send_data{
#         holder: hospital               
#     }
#     + send_data.violation => +power report_fine{
#         holder: patient 
#         action:#report_fine
#         consequence: "fine issued"
#     }
# """
# #action-consequence block:
# """
# action: #<action_id>
# consequence:
#     <+|- duty> <duty_id> {
#             holder: <target_id>
#             counterparty: <role_id_1> (optional)
#             action: <#action_id_1>
#             consequence: <string1>
#             violation: {
#                 condition: {"timeout": "<duration>"}
#                 }
#             }
#     <+|- power> <power_id> {
#         holder: <role_id_2>
#         action: <#action_id_2>
#         consequence: <string2>
#     } 
#     <string>
# """
# # 解析为：
# {"actions":[
#     {"uid":"<action_id>","action_type":"#<action_id>",
#     "consequences": {"operation":[
#                     {"type":"activate_duty/deactivate_power", "parameter":{"duty_id":"<duty_id>", "counterparty_role_id":"<role_id_1>"}},
#                     {"type":"activate_power/deactivate_power", "parameter":{"power_id":"<power_id>","target_role_id":"<role_id_2>"}},
#                     {"type":"notify", "message":"<string>"}]
#                     }},
#     {"uid":"<action_id_1>","action_type":"#<action_id_1>","consequence": "<string1>"},
#     {"uid":"<action_id_2>","action_type":"#<action_id_2>","consequence": "<string2>"}
#                             ]
# }
# {"duties": {"uid":"<duty_id>","action_type":"#action_id","action_id":"<action_id>","violation_id":"v_<duty_id>"}}
# {"powers": {"uid":"<power_id>","action_type":"#action_id","action_id":"<action_id>"}}

# # power block
# """
# power <uid> {
#     holder: <role_id>
#     action: <#action_id>
#     consequence: 
#         (consequence block)
# }
# optional:
# + <duty_id/power_id> -> + <power_id_enable> {
#     holder: <role_id>
#     action: <#action_id_1>
#     consequence: (consequence block)
# }
# + <duty_id>.violation => + power_id {
#     holder: <role_id>
#     action: <#action_id_2>
#     consequence: (consequence block)
# """
# #解析为：
# "powers":[{"uid":"<uid>","action_type":"#action_id","action_id":"<action_id>"}]
# "actions":[{"uid":"action_id","action_type":"#action_id","consequence":(parsed_consequence_block.get("consequence"))}]

# # transformational  block
# """+/- power|duty <uid_1> -> +/- power|duty <uid_2> {holder: <role_id>, action: <#action_id>, consequence: (consequence block)}"""

# #解析为：
# "powers":[{"uid":"<uid_2>","action_type":"#action_id","action_id":"<action_id>"},]
# "actions":[{"uid":"<action_id>","action_type":"#action_id",
#             "consequence":{
#                 ...(follow the method of parsing consequences)
# }}]

# #reactive block
# """
# + <duty_id>.violation => + power_id {
#     holder: <role_id>
#     action: <#action_id_2>
#     consequence: (consequence block)
# """
# #解析为
# "violations": [{"uid":"v_<duty_id>","condition":duty_id.violation,"consequence":{"operation":[{"type":"activate_power","power_id":"<power_id>"}]}}]


