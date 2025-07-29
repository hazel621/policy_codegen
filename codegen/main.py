from codegen.models import  RoleInput, ActionInput, DutyInput, PowerInput, ViolationInput
from database.connection import connect_to_mongo
from codegen.generate_code import store_role,store_action, generate_action_handler,store_duty,store_power,store_violation
from typing import List
from fastapi import FastAPI

db_connect = connect_to_mongo()
print(db_connect)

app = FastAPI()


# ---- Endpoints ----
@app.post("/roles")
async def add_roles(input: List[RoleInput]):
    msg = store_role(input)
    return msg

@app.post("/actions")
async def create_actions(input: List[ActionInput]):
    msg = store_action(input)
    return msg

@app.post("/duties")
async def add_duties(input: List[DutyInput]):
    msg = store_duty(input)
    return msg

@app.post("/powers")
async def add_powers(input: List[PowerInput]):
    msg = store_power(input)
    return msg

@app.post("/violations")
async def add_violations(input: List[ViolationInput]):
    msg = store_violation(input)
    return msg

@app.post("/action-handlers")
async def create_handler(input: ActionInput):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("template"))
    template = env.get_template("action_handler.py.j2")
    generate_action_handler(
        template=template,
        action_id=input.action_id,
        action_type=input.action_type,
        operation=input.consequence
    )
    return {"message": f"{input.action_type}_handler generated"}