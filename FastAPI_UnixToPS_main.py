from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import re
from typing import Optional, Dict, List

app = FastAPI(title="Unix to PowerShell Command Converter", version="1.0.0")

# Load command mappings from JSON file
def load_command_mappings():
    try:
        with open("command_mappings.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback mappings if file doesn't exist
        return {
            "ls": "Get-ChildItem",
            "pwd": "Get-Location",
            "cd": "Set-Location",
            "mkdir": "New-Item -ItemType Directory",
            "rmdir": "Remove-Item -Recurse",
            "rm": "Remove-Item",
            "cp": "Copy-Item",
            "mv": "Move-Item",
            "cat": "Get-Content",
            "grep": "Select-String",
            "find": "Get-ChildItem -Recurse",
            "ps": "Get-Process",
            "kill": "Stop-Process",
            "chmod": "Set-ItemProperty",
            "which": "Get-Command",
            "echo": "Write-Output",
            "env": "Get-ChildItem Env:",
            "history": "Get-History",
            "clear": "Clear-Host",
            "head": "Get-Content | Select-Object -First",
            "tail": "Get-Content | Select-Object -Last",
            "wc": "Measure-Object",
            "sort": "Sort-Object",
            "uniq": "Get-Unique",
            "df": "Get-WmiObject -Class Win32_LogicalDisk",
            "du": "Get-ChildItem | Measure-Object -Property Length -Sum",
            "mount": "Get-WmiObject -Class Win32_Volume",
            "wget": "Invoke-WebRequest",
            "curl": "Invoke-RestMethod",
            "tar": "Expand-Archive / Compress-Archive",
            "ssh": "Enter-PSSession",
            "scp": "Copy-Item -ToSession / Copy-Item -FromSession"
        }

command_mappings = load_command_mappings()

class UnixCommand(BaseModel):
    command: str
    include_explanation: Optional[bool] = False

class PowerShellResponse(BaseModel):
    unix_command: str
    powershell_command: str
    explanation: Optional[str] = None
    status: str

class CommandMappingsResponse(BaseModel):
    mappings: Dict[str, str]
    total_commands: int

def convert_unix_to_powershell(unix_cmd: str) -> tuple[str, str]:
    """
    Convert Unix command to PowerShell equivalent
    Returns tuple of (powershell_command, explanation)
    """
    unix_cmd = unix_cmd.strip()
    
    # Handle command with arguments
    parts = unix_cmd.split()
    base_command = parts[0] if parts else ""
    args = parts[1:] if len(parts) > 1 else []
    
    # Direct mapping for base commands
    if base_command in command_mappings:
        ps_base = command_mappings[base_command]
        
        # Handle specific command patterns with arguments
        if base_command == "ls":
            if "-la" in args or "-l" in args:
                return "Get-ChildItem | Format-List", "Lists files with detailed information"
            elif "-a" in args:
                return "Get-ChildItem -Force", "Lists all files including hidden ones"
            else:
                return ps_base, "Lists files and directories"
        
        elif base_command == "grep":
            if len(args) >= 1:
                pattern = args[0]
                if len(args) >= 2:
                    file = args[1]
                    return f"Select-String -Pattern '{pattern}' -Path '{file}'", f"Searches for pattern '{pattern}' in file '{file}'"
                else:
                    return f"Select-String -Pattern '{pattern}'", f"Searches for pattern '{pattern}' in input"
            else:
                return ps_base, "Searches for patterns in text"
        
        elif base_command == "find":
            if len(args) >= 1:
                if "-name" in args:
                    name_idx = args.index("-name")
                    if name_idx + 1 < len(args):
                        pattern = args[name_idx + 1]
                        return f"Get-ChildItem -Recurse -Name '*{pattern}*'", f"Finds files matching pattern '{pattern}'"
                else:
                    path = args[0]
                    return f"Get-ChildItem -Path '{path}' -Recurse", f"Lists all files in directory '{path}' recursively"
            else:
                return ps_base, "Finds files and directories"
        
        elif base_command == "head":
            if len(args) >= 1 and args[0].startswith("-"):
                lines = args[0][1:]  # Remove the dash
                if len(args) >= 2:
                    file = args[1]
                    return f"Get-Content '{file}' | Select-Object -First {lines}", f"Shows first {lines} lines of file '{file}'"
                else:
                    return f"Select-Object -First {lines}", f"Shows first {lines} lines"
            else:
                return "Get-Content | Select-Object -First 10", "Shows first 10 lines (default)"
        
        elif base_command == "tail":
            if len(args) >= 1 and args[0].startswith("-"):
                lines = args[0][1:]  # Remove the dash
                if len(args) >= 2:
                    file = args[1]
                    return f"Get-Content '{file}' | Select-Object -Last {lines}", f"Shows last {lines} lines of file '{file}'"
                else:
                    return f"Select-Object -Last {lines}", f"Shows last {lines} lines"
            else:
                return "Get-Content | Select-Object -Last 10", "Shows last 10 lines (default)"
        
        elif base_command == "kill":
            if len(args) >= 1:
                pid = args[0]
                return f"Stop-Process -Id {pid}", f"Terminates process with ID {pid}"
            else:
                return ps_base, "Terminates processes"
        
        elif base_command in ["cd", "mkdir", "rmdir", "rm", "cp", "mv", "cat"]:
            if len(args) >= 1:
                target = " ".join(args)
                return f"{ps_base} '{target}'", f"Performs {base_command} operation on '{target}'"
            else:
                return ps_base, f"PowerShell equivalent of {base_command}"
        
        else:
            # Default case - return base mapping with args
            if args:
                return f"{ps_base} {' '.join(args)}", f"PowerShell equivalent of {base_command} with arguments"
            else:
                return ps_base, f"PowerShell equivalent of {base_command}"
    
    else:
        return f"# No direct mapping found for '{base_command}'", f"Command '{base_command}' doesn't have a direct PowerShell equivalent in our database"

@app.get("/")
def read_root():
    return {"message": "Unix to PowerShell Command Converter API", "endpoints": ["/convert", "/mappings", "/docs"]}

@app.post("/convert", response_model=PowerShellResponse)
def convert_command(request: UnixCommand):
    """
    Convert a Unix command to its PowerShell equivalent
    """
    if not request.command.strip():
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    
    try:
        ps_command, explanation = convert_unix_to_powershell(request.command)
        
        response = PowerShellResponse(
            unix_command=request.command,
            powershell_command=ps_command,
            status="success"
        )
        
        if request.include_explanation:
            response.explanation = explanation
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting command: {str(e)}")

@app.get("/mappings", response_model=CommandMappingsResponse)
def get_command_mappings():
    """
    Get all available Unix to PowerShell command mappings
    """
    return CommandMappingsResponse(
        mappings=command_mappings,
        total_commands=len(command_mappings)
    )

@app.get("/mappings/{unix_command}")
def get_specific_mapping(unix_command: str):
    """
    Get PowerShell equivalent for a specific Unix command
    """
    if unix_command in command_mappings:
        return {
            "unix_command": unix_command,
            "powershell_command": command_mappings[unix_command],
            "status": "found"
        }
    else:
        raise HTTPException(status_code=404, detail=f"No mapping found for command: {unix_command}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    