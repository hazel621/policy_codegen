from mongoengine import Document, StringField, EnumField, DictField, ListField,EmbeddedDocument, EmbeddedDocumentField, DateTimeField
import enum
# from datetime import datetime
# import uuid
# Enum Definitions
# class PowerStateEnum(enum.Enum):
#     # pending = "pending"   
#     active = "active"
#     expired = "expired"

# class DutyStateEnum(enum.Enum):
#     # pending = "pending" #if duty is pending, it can still be executed but will inform counterparty
#     active = "active"   #if duty is active, it has to be fulfilled
#     # fulfilled = "fulfilled"
#     violated = "violated"

class RoleStateEnum(enum.Enum):
    active = "active"
    inactive = "inactive"

# 实体类  
class Violation(Document):
    uid = StringField(primary_key=True)
    violation_name = StringField()
    condition = DictField()  
    consequence = DictField()  

class Action(Document):
    uid = StringField(primary_key=True)
    action_type = StringField(required=True)
    consequence =  DictField()

class Power(Document):
    uid = StringField(primary_key=True)
    action_type = StringField(required=True)
    action_id = StringField(required=True)

class Duty(Document):
    uid = StringField(primary_key=True)
    action_type = StringField(required=True)
    action_id = StringField(required=True)
    counterparty_id = StringField()  # 可选，可能是另一个 Agent 的 ID
    counterparty_role_id = StringField()  # 可选，可能是另一个角色的 ID  
    violation_id = StringField()  # 可选，可能是一个 Violation 的 ID
    # leads_to = DictField()  

class Role(Document):
    uid = StringField(primary_key=True)
    role_name = StringField(required=True)
    description = StringField()
    scope = StringField(required=True)
    powers = ListField()
    duties = ListField()
    temporary_powers = DictField()  # 临时权限
    
class AgentRoleRelation(EmbeddedDocument):
    role_id = StringField(required=True)  # Role ID
    created_at = StringField()  # creation time
    expire_at = StringField()  # expiration time
    state = EnumField(RoleStateEnum, default=RoleStateEnum.active)

class Agent(Document):
    uid = StringField(primary_key=True)
    agent_name  = StringField(required=True)
    roles = ListField(EmbeddedDocumentField(AgentRoleRelation))

# 关联关系类

class AgentPowerRelation(Document):
    uid = StringField(primary_key=True)  # Agent 的唯一标识符
    # agent_id = StringField()
    agent_name = StringField(required=True)
    powers = DictField()  # 使用 DictField 存储 PowerRelation 的列表

class AgentDutyRelation(Document):
    uid = StringField(primary_key=True)  # Agent 的唯一标识符
    agent_name = StringField(required=True)
    duties = DictField()  # 使用 DictField 存储 DutyRelation 的列表
    # ListField(EmbeddedDocumentField(DutyRelation, required=True))

# 日志记录类
    
class LogDutyExecution(Document): # 用户请求，duty被激活，记录, state machine
    uid = StringField(primary_key=True)  
    request_id = StringField(required=True) 
    requester_id = StringField(required=True)  # 请求者的 Agent ID
    action_id = StringField(required=True)  # 关联的 Action ID
    duty_id = StringField(required=True)
    related_agents = DictField(require=True)  # 关联的 Agent ID 列表
    assigned_at = DateTimeField(required=True)    # 分配时间
    started_at = DateTimeField()                  # 开始履责
    fulfilled_at = DateTimeField()                # 成功完成时间
    violated_at = DateTimeField()                 # 违反时间
    violation_pending_at = DateTimeField()  # 违反待定时间
    status = StringField(required=True, choices=["assigned", "executing", "violation_pending", "fulfilled", "violated"])
    status_change_leads_to = ListField()  # 状态变更后可能导致的后续操作或状态
    # [{"from":"", "to":"assigned","operation":[{'power_id': 'send_data',
    #                                             'type': 'activate_power'}]}]  # 状态变更后可能导致的后续操作或状态

# class LogPowerExecution(Document):  
#     uid = StringField(primary_key=True)  #holder role id
#     powers
#     requester_id = StringField(required=True)  # 请求者的 Agent ID
#     power_id = StringField(required=True)  # 关联的 Action ID
#     created_at = DateTimeField(required=True) 
#     expired_at = DateTimeField()  # 可选，表示权限过期时间
#     assigned_by = StringField()  # 可选，表示分配权限的 Agent ID

class LogRequestExecution(Document):
    uid = StringField(required=True)
    requester_id = StringField(required=True)
    action_id = StringField(required=True)  # 关联的 Action ID
    state_check_result = StringField()  # 状态检查结果
    started_at = DateTimeField(required=True) 
    end_at = DateTimeField()  # 可选，表示请求结束时间
    related_duties = ListField() 
    related_powers = ListField()  
    status = StringField(required=True, choices=["pending","failed","succeeded"])
    result = StringField()  # 可选，表示请求的结果或错误信息

# duty任务
class DutyTaskList(Document):
    meta = {'collection': 'duty_task_queue'}
    uid = StringField(primary_key=True)  # task id
    requester_id = StringField(required=True)  # 请求者的 Agent ID
    related_action_id = StringField(required=True)  
    duty_id = StringField(required=True)
    deadline = DateTimeField(required=True)  # 绝对履责截止时间
    status = StringField(choices=["assigned", "executing", "fulfilled", "violated", "waiting","violation_pending"], required=True)