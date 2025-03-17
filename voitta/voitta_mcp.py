import json
import os
import asyncio
import subprocess
import shlex
import signal
import sys
import time
import importlib.util
from typing import Dict, List, Any, Optional, Tuple
import tempfile
import uuid


class MCPProcess:
    """
    Class to manage an MCP server process using asyncio.subprocess.
    """

    def __init__(self, command, args=None, env=None):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.process = None
        self.request_id_counter = 0
        self.pending_requests = {}
        self.consecutive_timeouts = 0
        self._stdout_task = None
        self._stderr_task = None
        self._is_starting = False

    async def start(self):
        """Start the MCP server process asynchronously."""
        if self.is_running() or self._is_starting:
            return

        self._is_starting = True
        try:
            # Combine command and args
            full_command = [self.command] + self.args

            # Create environment with both system env and server-specific env
            full_env = os.environ.copy()
            full_env.update(self.env)

            print(f"Starting MCP process: {' '.join(full_command)}")

            # Start the server process
            self.process = await asyncio.create_subprocess_exec(
                *full_command,
                env=full_env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            print(f"MCP process started with PID: {self.process.pid}")

            # Start background tasks to read stdout and stderr
            if self._stdout_task is None or self._stdout_task.done():
                self._stdout_task = asyncio.create_task(self._read_stdout())

            if self._stderr_task is None or self._stderr_task.done():
                self._stderr_task = asyncio.create_task(self._read_stderr())

            # Wait for the server to start
            await asyncio.sleep(1)
        finally:
            self._is_starting = False

    def is_running(self):
        """Check if the process is running."""
        if self.process is None:
            return False

        return self.process.returncode is None

    async def stop(self):
        """Stop the MCP server process."""
        if not self.is_running():
            return

        print(f"Stopping MCP process with PID: {self.process.pid}")

        try:
            # Try to terminate gracefully first
            self.process.terminate()

            # Wait for process to terminate
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                print("Process didn't terminate gracefully, killing it")
                self.process.kill()
                await self.process.wait()
        except Exception as e:
            print(f"Error stopping process: {e}")

        # Cancel background tasks
        if self._stdout_task and not self._stdout_task.done():
            self._stdout_task.cancel()
            try:
                await self._stdout_task
            except asyncio.CancelledError:
                pass

        if self._stderr_task and not self._stderr_task.done():
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass

        self.process = None
        self._stdout_task = None
        self._stderr_task = None

    async def _read_stdout(self):
        """Read from stdout and process MCP responses."""
        try:
            while self.is_running():
                line = await self.process.stdout.readline()
                if not line:
                    if self.is_running():
                        print(
                            "Stdout closed unexpectedly while process is still running")
                    break

                line_str = line.decode('utf-8').strip()
                if not line_str:
                    continue

                try:
                    print(f"Received from MCP: {line_str}")
                    response = json.loads(line_str)

                    # Validate that this is a proper JSON-RPC 2.0 response
                    if "jsonrpc" not in response or response["jsonrpc"] != "2.0":
                        print(
                            f"Warning: Response missing or invalid jsonrpc version: {response}")

                    # Get the request ID from the response
                    request_id = response.get("id")
                    if request_id is None:
                        print(f"Warning: Response missing ID: {response}")
                        continue

                    if request_id in self.pending_requests:
                        future = self.pending_requests[request_id]
                        if not future.done():
                            future.set_result(response)
                        del self.pending_requests[request_id]
                    else:
                        print(
                            f"Received response for unknown request ID: {request_id}")
                except json.JSONDecodeError:
                    print(f"Failed to parse MCP response: {line_str}")
                except Exception as e:
                    print(f"Error processing MCP response: {e}")
        except asyncio.CancelledError:
            print("Stdout reader task cancelled")
            raise
        except Exception as e:
            print(f"Unexpected error in stdout reader: {e}")

    async def _read_stderr(self):
        """Read from stderr and log errors."""
        try:
            while self.is_running():
                line = await self.process.stderr.readline()
                if not line:
                    if self.is_running():
                        print(
                            "Stderr closed unexpectedly while process is still running")
                    break

                line_str = line.decode('utf-8').strip()
                if line_str:
                    print(f"MCP stderr: {line_str}")
        except asyncio.CancelledError:
            print("Stderr reader task cancelled")
            raise
        except Exception as e:
            print(f"Unexpected error in stderr reader: {e}")

    async def send_request(self, method, params=None):
        """Send a request to the MCP server and wait for a response."""
        if not self.is_running():
            await self.start()

            # Double-check that the process started successfully
            if not self.is_running():
                print("Failed to start MCP process")
                return None

        request_id = str(self.request_id_counter)
        self.request_id_counter += 1

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        # Create a future to wait for the response
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        # Send the request
        request_json = json.dumps(request) + "\n"
        print(f"Sending request to MCP: {request_json.strip()}")

        try:
            self.process.stdin.write(request_json.encode('utf-8'))
            await self.process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as e:
            print(f"Pipe error when sending request: {e}")
            del self.pending_requests[request_id]
            # Try to restart the process
            await self.stop()
            await self.start()
            return None
        except Exception as e:
            print(f"Error sending request: {e}")
            del self.pending_requests[request_id]
            return None

        # Wait for the response with a timeout
        try:
            response = await asyncio.wait_for(future, timeout=30)
            self.consecutive_timeouts = 0  # Reset timeout counter on success

            # Proper JSON-RPC 2.0 response handling
            if "error" in response:
                error = response["error"]
                print(
                    f"MCP server error: code={error.get('code')}, message={error.get('message')}")
                return None

            # Return the result field as per JSON-RPC 2.0 specification
            if "result" in response:
                return response["result"]
            else:
                print(
                    f"Invalid JSON-RPC response: missing 'result' field: {response}")
                return None
        except asyncio.TimeoutError:
            del self.pending_requests[request_id]
            print(f"Timeout waiting for MCP server response to {method}")

            # Track consecutive timeouts
            self.consecutive_timeouts += 1
            if self.consecutive_timeouts > 3:
                print("Too many consecutive timeouts, restarting process")
                await self.stop()
                await asyncio.sleep(1)
                await self.start()
                self.consecutive_timeouts = 0

            return None
        except Exception as e:
            print(f"Error waiting for response: {e}")
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            return None

    async def check_health(self):
        """Check if the process is healthy."""
        if not self.is_running():
            print("Process not running during health check")
            return False

        # For now, just check if the process is running
        # We'll assume it's healthy if it's running
        return True


class MCPServerDescription:
    """
    Class to handle MCP servers configuration and interaction.
    """

    def __init__(self, config_path, config_type="cline"):
        self.config_path = os.path.expanduser(config_path)
        self.config_type = config_type
        self.servers = {}
        self.tools = []
        self.operationIds = {}
        self.prompt = "These functions are available from MCP servers:"
        self.server_processes = {}

        # Load MCP configuration
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)

        # Process servers based on config type
        if self.config_type == "cline":
            self._process_cline_config()

    def _process_cline_config(self):
        """Process Cline MCP configuration format"""
        if 'mcpServers' not in self.config:
            return

        # Store servers for later async discovery
        for server_name, server_config in self.config['mcpServers'].items():
            # Skip disabled servers
            if server_config.get('disabled', False):
                continue

            self.servers[server_name] = server_config

    async def discover_all_tools(self):
        """Discover tools from all configured MCP servers"""
        discovery_tasks = []

        for server_name, server_config in self.servers.items():
            discovery_tasks.append(
                self._discover_server_tools(server_name, server_config))

        # Run all discovery tasks concurrently
        await asyncio.gather(*discovery_tasks)

    async def _discover_server_tools(self, server_name, server_config):
        """
        Discover tools available from an MCP server by querying the server.

        This method attempts to start the MCP server (if not already running)
        and query it for its available tools.
        """
        print(f"Discovering tools for MCP server: {server_name}")

        # Start the server process if it's not already running
        if server_name not in self.server_processes:
            command = server_config.get('command')
            args = server_config.get('args', [])
            env = server_config.get('env', {})

            if command:
                process = MCPProcess(command, args, env)
                self.server_processes[server_name] = process
                await process.start()

        # Get the server process
        process = self.server_processes.get(server_name)
        if not process or not process.is_running():
            print(f"Failed to start MCP server: {server_name}")
            return

        # Check process health before sending important requests
        is_healthy = await process.check_health()
        if not is_healthy:
            print(f"MCP server {server_name} failed health check, restarting")
            await process.stop()
            await asyncio.sleep(1)
            await process.start()

            # Check again after restart
            is_healthy = await process.check_health()
            if not is_healthy:
                print(
                    f"MCP server {server_name} still unhealthy after restart, skipping")
                return

        # Query the server for its available tools
        print(f"Requesting tools from MCP server: {server_name}")

        # Use the standard MCP method name for listing tools according to the specification
        print(
            f"For {server_name}, requesting tools using standard MCP method: tools/list")
        tools_result = await process.send_request("tools/list")

        if not tools_result:
            print(
                f"No tools result from MCP server: {server_name} after trying multiple methods")
            return

        # Register each tool
        for tool in tools_result["tools"]:
            tool_name = tool.get("name")
            description = tool.get("description", f"Tool from {server_name}")
            input_schema = tool.get("inputSchema", {})

            # Extract parameters and required fields from the input schema
            parameters = {}
            required = []

            if "properties" in input_schema:
                for param_name, param_schema in input_schema["properties"].items():
                    param_type = param_schema.get("type", "string")
                    param_desc = param_schema.get(
                        "description", f"Parameter {param_name}")

                    parameters[param_name] = {
                        "type": param_type,
                        "description": param_desc
                    }

            if "required" in input_schema:
                required = input_schema["required"]

            self._add_tool(
                server_name=server_name,
                tool_name=tool_name,
                description=description,
                parameters=parameters,
                required=required
            )
        print(f"Found {len(self.tools)} tools")

    def _add_tool(self, server_name, tool_name, description, parameters, required=None):
        """Helper method to add a tool to the tools list"""
        if required is None:
            required = []

        # Sanitize server_name and tool_name to ensure they only contain allowed characters
        import re
        sanitized_server = re.sub(r'[^a-zA-Z0-9_-]', '_', server_name)
        sanitized_tool = re.sub(r'[^a-zA-Z0-9_-]', '_', tool_name)

        # Replace colon with X to avoid issues with Chainlit and keep names shorter
        full_name = f"{sanitized_server}_X_{sanitized_tool}"

        tool_id = len(self.tools)
        self.operationIds[full_name] = tool_id
        self.tools.append({
            "name": full_name,
            "server": server_name,
            "tool": tool_name,
            "description": description,
            "parameters": parameters,
            "required": required
        })

    def get_tools(self, prefix, delimiter="__"):
        """Get tool definitions in the format expected by OpenAI"""
        result = []
        # Keep track of used names for disambiguation
        used_names = {}

        for i, tool in enumerate(self.tools):
            # Process properties to handle array types properly
            properties = {}
            for param, param_info in tool["parameters"].items():
                param_type = param_info["type"]
                param_schema = {
                    "type": param_type,
                    "description": param_info["description"]
                }

                # Add items property for array parameters
                if param_type == "array":
                    # For paths parameter, assume it's an array of strings
                    if param == "paths":
                        param_schema["items"] = {"type": "string"}
                    else:
                        # For other arrays, use a generic string type if we don't know
                        param_schema["items"] = {"type": "string"}

                properties[param] = param_schema

            # Create function name and ensure it doesn't exceed 64 characters
            base_name = f"{prefix}{delimiter}{tool['name']}"

            if len(base_name) <= 64:
                # Name is short enough, use it directly
                full_name = base_name
            else:
                # Name is too long, need to shorten it
                # Extract server and tool parts
                parts = tool['name'].split('_X_')
                if len(parts) == 2:
                    server_part, tool_part = parts

                    # Try to shorten server name if it's too long
                    if len(server_part) > 20:
                        # Keep first 10 chars of server name
                        server_part = server_part[:10]

                    # Try to shorten tool name if it's too long
                    if len(tool_part) > 20:
                        # Keep first 15 chars of tool name
                        tool_part = tool_part[:15]

                    # Create shortened name
                    shortened_name = f"{prefix}{delimiter}{server_part}_X_{tool_part}"

                    # Check if we need to disambiguate
                    if shortened_name in used_names:
                        # Add sequence number for disambiguation
                        count = used_names[shortened_name] + 1
                        used_names[shortened_name] = count
                        full_name = f"{shortened_name}{count}"

                        # If still too long, truncate more
                        if len(full_name) > 64:
                            # Further shorten and add sequence number
                            server_part = server_part[:5]
                            tool_part = tool_part[:10]
                            full_name = f"{prefix}{delimiter}{server_part}_X_{tool_part}{count}"
                    else:
                        used_names[shortened_name] = 1
                        full_name = shortened_name
                else:
                    # Fallback to simple truncation if the name format is unexpected
                    full_name = base_name[:64]

                # Final check - if still too long, use MD5 hash as last resort
                if len(full_name) > 64:
                    import hashlib
                    name_hash = hashlib.md5(
                        tool['name'].encode()).hexdigest()[:8]
                    full_name = f"{prefix}{delimiter}tool_{name_hash}"

                print(f"Shortened tool name: {tool['name']} -> {full_name}")

            # Final sanitization to ensure the function name only contains allowed characters
            import re
            sanitized_full_name = re.sub(r'[^a-zA-Z0-9_-]', '_', full_name)

            result.append({
                "type": "function",
                "function": {
                    "name": sanitized_full_name,
                    "description": tool["description"],
                    "strict": False,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": tool.get("required", []),
                        "additionalProperties": False
                    }
                }
            })
        return result

    async def call_function(self, name, arguments, token, oauth_token):
        """Call an MCP tool function"""
        if name not in self.operationIds:
            raise ValueError(f"Name {name} not found")

        tool_id = self.operationIds[name]
        tool = self.tools[tool_id]
        server_name = tool["server"]
        tool_name = tool["tool"]

        # Get the server process
        process = self.server_processes.get(server_name)
        if not process or not process.is_running():
            return json.dumps({
                "status": "error",
                "message": f"MCP server {server_name} is not running"
            })

        # Call the MCP server with the standard method name and parameters according to the specification
        result = await process.send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })

        if not result:
            return json.dumps({
                "status": "error",
                "message": f"Failed to call MCP tool {tool_name} on server {server_name}"
            })

        # Format the response according to the expected format
        # Check if the result is already a string (possibly JSON)
        if isinstance(result, str):
            try:
                # Try to parse it as JSON to ensure it's valid
                json.loads(result)
                return result  # Return as is if it's valid JSON
            except json.JSONDecodeError:
                # If it's not valid JSON, wrap it in a JSON object
                return json.dumps({"content": result})
        else:
            # If it's not a string, convert it to JSON
            return json.dumps(result)
