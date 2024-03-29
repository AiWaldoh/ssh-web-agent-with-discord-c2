import paramiko
import sys
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class SSHCredentials(BaseModel):
    """
    Pydantic model for SSH credentials.
    """

    hostname: str
    username: str
    key_filename: str


class SSHCommand(BaseModel):
    """
    Pydantic model for an SSH command.
    """

    command: str


class SSHClient:
    """
    A client for managing SSH connections and executing commands over SSH.

    Attributes:
        hostname (str): The hostname of the SSH server.
        username (str): The username for the SSH connection.
        key_filename (str): The path to the SSH private key file.
        client (paramiko.SSHClient): The Paramiko SSH client.
        shell (paramiko.Channel): The SSH shell for executing commands.
    """

    def __init__(self, hostname, username, key_filename):
        """
        Initializes the SSHClient instance with given credentials.

        Args:
            hostname (str): The hostname of the SSH server.
            username (str): The username for the SSH connection.
            key_filename (str): The path to the SSH private key file.
        """
        self.hostname = hostname
        self.username = username
        self.key_filename = key_filename
        self.client = None
        self.shell = None

    def connect(self):
        """
        Establishes an SSH connection and initializes the shell.

        Raises:
            Exception: If the connection fails.
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                self.hostname, username=self.username, key_filename=self.key_filename
            )
            self.shell = self.client.invoke_shell()
            self._discard_initial_prompt()
        except Exception as e:
            print(f"Failed to connect to {self.hostname}: {e}")
            sys.exit(1)

    def _discard_initial_prompt(self):
        """
        Discards the initial prompt text from the SSH shell.
        """
        output = ""
        while not self.shell.recv_ready():
            time.sleep(0.1)
        while self.shell.recv_ready():
            data = self.shell.recv(1024)
            output += data.decode("utf-8")

    def execute_command(self, command):
        """
        Executes a command on the SSH server.

        Args:
            command (str): The command to execute.

        Returns:
            str: The output from the command execution.

        Raises:
            RuntimeError: If the connection is not established.
        """
        if self.shell:
            output = ""
            self.shell.send(command + "\n")
            while not self.shell.recv_ready():
                time.sleep(0.1)
            while self.shell.recv_ready():
                data = self.shell.recv(1024)
                output += data.decode("utf-8")
            return output.strip()
        else:
            print("Connection not established.")

    def close(self):
        """
        Closes the SSH connection.
        """
        if self.client:
            self.client.close()


ssh_client = None


@app.post("/connect")
async def connect(credentials: SSHCredentials):
    """
    FastAPI endpoint to establish an SSH connection.

    Args:
        credentials (SSHCredentials): The SSH credentials.

    Returns:
        dict: A status message indicating connection success.

    Raises:
        HTTPException: If an SSH connection is already established.
    """
    global ssh_client
    if ssh_client is None:
        ssh_client = SSHClient(
            credentials.hostname, credentials.username, credentials.key_filename
        )
        ssh_client.connect()
        return {"status": "connected"}
    else:
        raise HTTPException(
            status_code=400, detail="SSH connection already established"
        )


@app.post("/execute-command")
async def execute_command(command: SSHCommand):
    """
    FastAPI endpoint to execute a command over an established SSH connection.

    Args:
        command (SSHCommand): The command to execute.

    Returns:
        dict: The output from the command execution.

    Raises:
        HTTPException: If no SSH connection is established.
    """
    global ssh_client
    if ssh_client is not None:
        output = ssh_client.execute_command(command.command)
        if command.command.strip() == "exit":
            ssh_client.close()
            ssh_client = None
        return {"output": output}
    else:
        raise HTTPException(status_code=400, detail="SSH connection not established")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=18880)
