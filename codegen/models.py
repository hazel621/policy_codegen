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

# ---------- Execution Logging ----------

class LogDutyExecutionInput(BaseModel):
    uid: str
    request_id: str
    requester_id: str
    action_id: str
    duty_id: str
    related_agents: Dict
    assigned_at: datetime
    started_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    violated_at: Optional[datetime] = None
    violation_pending_at: Optional[datetime] = None
    status: str  # should be validated separately: ["assigned", "executing", etc.]

class LogRequestExecutionInput(BaseModel):
    uid: str
    requester_id: str
    action_id: str
    started_at: datetime
    end_at: Optional[datetime] = None
    related_duties: List[str] = Field(default_factory=list)
    related_powers: List[str] = Field(default_factory=list)
    status: str  # ["pending","failed","succeeded"]
    result: Optional[str] = None

# ---------- Duty Task ----------

class DutyTaskInput(BaseModel):
    uid: str
    requester_id: str
    related_action_id: str
    duty_id: str
    deadline: datetime
    status: str  # choices=["assigned", "executing", "fulfilled", "violated", "waiting","violation_pending"]
