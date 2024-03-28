from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import shlex

app = FastAPI()

# List of allowed commands
ALLOWED_COMMANDS = ["ls", "pwd", "whoami"]


class CommandRequest(BaseModel):
    command: str


@app.post("/execute")
async def execute_command(request: CommandRequest):
    command = request.command

    if command not in ALLOWED_COMMANDS:
        raise HTTPException(status_code=403, detail="Command not allowed")

    try:
        # Use shlex.split() to safely split the command string
        command_parts = shlex.split(command)
        result = subprocess.run(command_parts, capture_output=True, text=True)
        return {"output": result.stdout, "error": result.stderr}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))
