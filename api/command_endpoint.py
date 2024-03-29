from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import shlex
import uvicorn

app = FastAPI()


class CommandRequest(BaseModel):
    command: str


@app.post("/execute")
async def execute_command(request: CommandRequest):
    command = request.command.strip()
    try:
        # Use shlex.split() to safely split the command string
        command_parts = shlex.split(command)

        # Handle specific commands
        if command_parts[0] == "ping":
            # Add a limit to the ping command to prevent it from running indefinitely
            command_parts.append("-c")
            command_parts.append("4")  # Adjust the count as needed
        elif (
            command_parts[0] == "sudo"
            and command_parts[1] == "apt"
            and command_parts[2] == "install"
        ):
            # Add the -y flag to automatically answer yes to prompts
            command_parts.append("-y")

        result = subprocess.run(command_parts, capture_output=True, text=True)
        return {"output": result.stdout, "error": result.stderr}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=18880)
