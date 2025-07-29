from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime

# Enum for Role State
class RoleStateEnum(str, Enum):
    active = "active"
    inactive = "inactive"

# ---------- Core Entity Schemas ----------

class ViolationInput(BaseModel):
    uid: str
    violation_name: Optional[str]= None
    condition: Dict
    consequence: Dict

class ActionInput(BaseModel):
    uid: str
    action_type: str
    consequence: Dict  

class ActionHandlerInput(BaseModel):
    action_id: str
    action_type: str
    operation: list
    action_scope: str 

class PowerInput(BaseModel):
    uid: str
    action_type: str
    action_id: str

class DutyInput(BaseModel):
    uid: str
    action_type: str
    action_id: str
    counterparty_id: Optional[str] = None
    counterparty_role_id: Optional[str] = None
    violation_id: Optional[str] = None
# ---------- Role Schemas ----------
class RolePowerEntry(BaseModel):
    power_id: str
    initial_state: Optional[str]
    scope: Optional[str]

class RoleDutyEntry(BaseModel):
    duty_id: str
    initial_state: Optional[str]
    counterparty_role_id: Optional[str]
    scope: Optional[str]

class RoleInput(BaseModel):
    uid: str
    role_name: str
    description: Optional[str]= None
    scope: str
    powers: List[RolePowerEntry] = []
    duties: List[RoleDutyEntry] = []


# ---------- Agent and Role Relations ----------

class AgentRoleRelationInput(BaseModel):
    role_id: str
    created_at: Optional[str] = None
    expire_at: Optional[str] = None
    state: RoleStateEnum = RoleStateEnum.active

class AgentInput(BaseModel):
    uid: str
    agent_name: str
    roles: List[AgentRoleRelationInput] = Field(default_factory=list)