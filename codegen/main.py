from codegen.models import  RoleInput, ActionInput, DutyInput, PowerInput, ViolationInput, ActionHandlerInput
from database.connection import connect_to_mongo
from codegen.generate_code import store_role,store_action, generate_action_handler,store_duty,store_power,store_violation
from codegen.dpcl_parser import parse_dpcl_full
from typing import List
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

db_connect = connect_to_mongo()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定 http://localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/dpcl")
async def process_dpcl(request: Request):
    try:
        text = await request.body()
        dpcl_text = text.decode("utf-8")
        parsed = parse_dpcl_full(dpcl_text)
        print(f"Parsed DPCL: {parsed}")

        logs = []
        if "actions" in parsed:
            msg = store_action(parsed["actions"])
            logs.append(f"Stored actions: {msg}")

        if "powers" in parsed:
            msg = store_power(parsed["powers"])
            logs.append(f"Stored powers: {msg}")

        if "violations" in parsed:
            msg = store_violation(parsed["violations"])
            logs.append(f"Stored violations: {msg}")

        if "duties" in parsed:
            msg = store_duty(parsed["duties"])
            logs.append(f"Stored duties: {msg}")

        return {
            "status": "finished",
            "message": "; ".join(logs)
        }

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

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
async def create_handler(input: ActionHandlerInput):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("codegen/template"))
    template = env.get_template("action_handler_async.py.j2")
    msg = generate_action_handler(
        template=template,
        action_id=input.action_id,
        action_type=input.action_type,
        action_scope=input.action_scope,
        operation=input.operation,
    )
    return msg