import jwt
import datetime
import os
import sys
import io
import yaml
from fastapi.testclient import TestClient
import requests
import json
import pandas as pd
from jsonpath_ng import parse
import httpx
import urllib.parse
import re
import time


from .voitta_canvas import CanvasDescription
from .voitta_mcp import MCPServerDescription

import dspy
import textwrap

from pydantic import BaseModel, Extra
from typing import Any, Optional, Dict, List

from dotenv import load_dotenv

from asgiref.sync import async_to_sync

import traceback

load_dotenv()

jsonpath_expr = parse("$..['$ref']")

def voitta_log(message):
    return

def urljoin(*parts):
    return "/".join(part.strip("/") for part in parts)


def get_http_client(app=None, _type=""):
    if app is None or _type not in ["web_client"]:
        client = requests
    else:
        client = TestClient(app)
    return client


class VoittaResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[str] = None

    class Config:
        extra = Extra.allow


class ToolDescriptor:
    def __init__(self,
                 path,
                 operationId,
                 name,
                 description,
                 method,
                 schema):
        self.operationId = operationId
        self.name = name
        self.description = description
        self.method = method
        self.schema = schema
        self.path = path


class EndpointDescription:
    def __init__(self, name, description, url, info, app=None):
        self.info = info
        self.url = url
        self.name = name
        self.description = description
        self.tools = []
        self.operationIds = {}
        self.prompt = None
        self.app = app
        self.client = get_http_client(app, info.get("type", ""))
        self.openapi = self.client.get ( urljoin(url,"openapi.json") ).json()
        self.paths = []

        for path in self.openapi["paths"]:
            self.paths.append(path)
            if path == "/__prompt__":
                self.prompt = self.client.get(
                    urljoin(url, "__prompt__")    ).text.strip('"')

                match = ('{"message":"Result for ivan"}' in self.prompt)
                if match:
                    self.prompt = "This server provides function for asset manager interactions"
                continue

            path_data = self.openapi["paths"][path]

            for method in path_data:
                if "CPM" in path_data[method] or "x-CPM" in path_data[method]:
                    if "requestBody" not in path_data[method]:
                        rb = False
                        if "parameters" in path_data[method]:
                            schema = path_data[method]["parameters"]
                        else:
                            schema = None
                    else:
                        rb = True
                        requestBody = path_data[method]["requestBody"]
                        matches = jsonpath_expr.find(requestBody)
                        value = matches[0].value
                        schema_name = value.split("/")[-1]
                        schema = self.openapi["components"]["schemas"][schema_name]

                    tool = ToolDescriptor(
                        path=path,
                        operationId=path_data[method]["operationId"],
                        name=path_data[method].get("summary", "No Name"),
                        description=path_data[method]["description"],
                        method=method,
                        schema=schema
                    )

                    self.operationIds[path_data[method]
                                      ["operationId"]] = len(self.tools)
                    self.tools.append(tool)

                    matches = jsonpath_expr.find(path_data[method])

    async def call_function(self, name, arguments, token, oauth_token):
        voitta_log(f"call_function: {name} ::: {self.operationIds} ::: {arguments}")
        if name not in self.operationIds:
            raise ValueError(f"Name {name} not found")

        tool_id = self.operationIds[name]
        tool = self.tools[tool_id]

        if token is not None:
            headers = {"Authorization": f"{token}",
                       "oauthtoken": f"{oauth_token}"}
        else:
            headers = None

        if tool.method == "get":
            url = urljoin(self.url, tool.path)

            if tool.schema is None or len(tool.schema) == 0:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers)
                    return response.text
            else:
                encoded_arguments = {
                    key: urllib.parse.quote(value, safe='') if type(
                        value) == str else value
                    for key, value in arguments.items()
                }
                formatted_path = tool.path.format(**encoded_arguments)

                url = urljoin(self.url, formatted_path)

                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers)
                    return response.text
        elif tool.method == "post":
            if tool.schema is None or len(tool.schema) == 0:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers)
                    return response.text
            else:
                url = urljoin ( self.url, tool.path )

                data = {}
                files = {}

                asset_name = arguments.get("asset_name", "unknown")

                voitta_log(f"call function/tool.schema: {tool.schema}")

                for argument in arguments:
                    voitta_log(f"--------- {argument} -------")
                    if type(tool.schema) == dict:
                        arg_descriptor = tool.schema["properties"][argument]
                    else:
                        voitta_log(
                            "------------------------------------------------------")
                        voitta_log(tool.schema)
                        for arg in tool.schema:
                            voitta_log(arg)
                            if arg["name"] == argument:
                                arg_descriptor = arg
                                break

                    if "format" in arg_descriptor and arg_descriptor["format"] == "binary":
                        file_obj = io.BytesIO(
                            arguments[argument].encode("utf8"))
                        files[argument] = (asset_name, file_obj, "text/plain")
                    else:
                        data[argument] = arguments[argument]

                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers,
                                                 data=data,
                                                 files=files,
                                                 timeout=60.0)

                return response.text
        else:
            url = urljoin(self.url, tool.path)
            return f"Not implemented yet ({tool.method})"

    def get_tools(self, prefix, delimiter):
        result = []
        for tool in self.tools:
            voitta_log(f"---> schema: {tool.schema}")
            required = []
            properties = {}
            if tool.schema is None:
                pass
            elif type(tool.schema) == dict:
                for p in tool.schema["properties"]:
                    if "anyOf" in tool.schema["properties"][p]:
                        # optional parameter
                        types = [a["type"]
                                 for a in tool.schema["properties"][p]["anyOf"]]
                        tp = types[0]
                    else:
                        tp = tool.schema["properties"][p]["type"]

                    properties[p] = {
                        "type": tp,
                        "description": tool.schema["properties"][p]["description"]
                    }

                required = tool.schema.get("required", [])

            elif type(tool.schema) == list:
                missing_description = False
                for arg in tool.schema:

                    voitta_log(f"------> arg: {arg}")

                    if "description" not in arg:
                        missing_description = True

                    # romaroma
                    voitta_log(f'--- roma: {arg["schema"]}')
                    if "anyOf" in arg["schema"]:
                        types = [a["type"] for a in arg["schema"]["anyOf"]]
                        tp = types[0]
                    else:
                        tp = arg["schema"]["type"]

                    properties[arg["name"]] = {
                        "type": tp,
                        "description": arg.get("description", "--- NO DESCRIPTION PROVIDED ---")
                    }
                    if arg["required"]:
                        required.append(arg["name"])

                    if missing_description:
                        voitta_log(
                            f"--- Description was missing for {arg['name']} in {self.name}")
            else:
                voitta_log(f"strange schema type: {type(type(tool.schema))}")

            voitta_log(f"get_tools: {tool.operationId} -> {properties}")

            result.append({
                "type": "function",
                "function": {
                    "name": f"{prefix}{delimiter}{tool.operationId}",
                    "description": tool.description,
                    "strict": False,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                        "additionalProperties": False
                    }
                }
            })
        return result


class VoittaRouter:
    def __init__(self, endpoints, tool_delimiter="____", mcp_config=None, app=None):
        self.endpoint_directory = {}
        self.endpoints = []
        self.tool_delimiter = tool_delimiter
        self.canvas = None
        self.reference_provider = None
        self.dspy_tools = []
        self.cl = None
        self.mcp = None
        self.app = app

        if type(endpoints) == str:
            with open(endpoints, "r") as file:
                voitta_config = yaml.safe_load(file)

            # Extract MCP configuration if present in the YAML file
            if "mcp_config" in voitta_config:
                mcp_config = voitta_config.pop("mcp_config")

            endpoints = [(r, voitta_config[r]) for r in voitta_config]

        if type(endpoints) != list:
            raise ValueError(
                "Error parsing endpoints, either a yaml file or a valid list needed")

        # Initialize MCP if config is provided
        if mcp_config:
            config_type = mcp_config.get("type", "cline")
            config_path = mcp_config.get("path")
            if config_path:
                self.mcp = MCPServerDescription(config_path, config_type)
                voitta_log(f"MCP initialized with config type: {config_type}")
                # Note: We don't await discover_all_tools here because __init__ can't be async
                # The tools will be discovered when get_tools or get_prompt is called

        for name, info in endpoints:
            url = info["url"]
            if url == "canvas":
                self.canvas = CanvasDescription()
            else:
                try:
                    endpoint = EndpointDescription(
                        name=name,
                        description=info.get("description", url),
                        url=url, info=info, app=self.app)
                    self.endpoints.append(endpoint)
                    self.endpoint_directory[name] = endpoint
                except Exception as e:
                    voitta_log(
                        f"==================  ERROR CREATING ENDPOINT {name}  =======================")
                    voitta_log(e)
                    traceback.print_exc()
                    continue

            if info.get("role", None) == "reference_provider":
                self.reference_provider = endpoint

        type_map = {
            "boolean": "bool",
            "string": "str",
            "integer": "int"
        }

        for j, endpoint in enumerate(self.endpoints + ([self.canvas] if self.canvas else [])):
            voitta_log(f" ===== DSP NAME: {endpoint.name} ==========")
            if endpoint.name in ["asset_manager", "google_agent"]:
                voitta_log("\t skipping auth endpoints for now")
                continue
            if endpoint == self.canvas:
                tools = endpoint.get_tools(str(0), self.tool_delimiter)
            else:
                tools = endpoint.get_tools(str(j+1), self.tool_delimiter)
            for tool in tools:
                function_name = tool["function"]["name"]
                function_desc = tool["function"]["description"]

                p_short = []
                p_long = []
                p_arg = []
                for parameter_name in tool["function"]["parameters"].get("properties", []):
                    parameter_type = type_map[
                        tool["function"]["parameters"]["properties"][parameter_name]["type"]
                    ]
                    parameter_desc =\
                        tool["function"]["parameters"]["properties"][parameter_name]["description"]

                    p_short.append(f"{parameter_name}: {parameter_type}")
                    p_long.append(
                        f"{parameter_name} ({parameter_type}): {parameter_desc}")
                    p_arg.append(f'"{parameter_name}": {parameter_name}')

                if len(p_short) == 0:
                    func_text = f"def f_{function_name} () -> str:\n"
                    func_text += f"\t'''{function_desc}'''\n\n"
                else:
                    func_text = f"def f_{function_name} ({','.join(p_short)}) -> str:\n"
                    func_text += f"\t'''{function_desc}\n\n"
                    func_text += "\tParameters:\n"
                    func_text += "\t\t\n".join(p_long) + "'''\n\n"

                func_text += f"""
\tfrom asgiref.sync import async_to_sync
\timport threading
\timport uuid
\timport sys
\tresult = None
\texception = None
\tcall_id = str(uuid.uuid4())
    
    

\tdef target():
\t\tnonlocal result, exception, call_id
\t\ttry:
\t\t\t#cl = getattr(globals()[sys._getframe().f_code.co_name], 'cl')
"""
                if function_name[0] == "0":
                    func_text += f"""\t\t\tresult = async_to_sync(this.call_function)('{function_name}',{{{','.join(p_arg)}}},cl,'',call_id)
"""
                else:
                    func_text += f"""\t\t\tresult = async_to_sync(this.call_function)('{function_name}',{{{','.join(p_arg)}}},'','',call_id)
"""
                func_text += f"""\t\texcept Exception as e:
\t\t\texception = e
\tthread = threading.Thread(target=target)
\tthread.start()
\tthread.join()

\tif exception:
\t\t#voitta_log("***An exception occurred***:", exception)
\t\traise exception

\treturn result
"""

                namespace = {"this": self}
                exec(func_text, namespace)

                the_function = namespace[f"f_{function_name}"]

                self.dspy_tools.append(the_function)

        voitta_log(f"{len(self.endpoints)} endpoint(s) created")

    async def discover_mcp_tools(self):
        """Discover tools from MCP servers if MCP is initialized"""
        if self.mcp is not None:
            try:
                voitta_log("Starting MCP tool discovery...")
                await self.mcp.discover_all_tools()
                voitta_log("MCP tool discovery completed")
            except Exception as e:
                voitta_log(f"Error during MCP tool discovery: {e}")

    async def get_tools_async(self):
        """Async version of get_tools that ensures MCP tools are discovered first"""
        # Ensure MCP tools are discovered
        await self.discover_mcp_tools()
        return self.get_tools()

    def get_tools(self):
        """Get all tools from OpenAPI endpoints, Canvas, and MCP"""
        tools = []

        # Add tools from OpenAPI endpoints
        for j, endpoint in enumerate(self.endpoints):
            tools += endpoint.get_tools(str(j+1), self.tool_delimiter)

        # Add tools from Canvas
        if self.canvas is not None:
            tools += self.canvas.get_tools(0, self.tool_delimiter)

        # Add tools from MCP
        if self.mcp is not None:
            tools += self.mcp.get_tools("mcp", self.tool_delimiter)

        return tools

    async def get_prompt_async(self, defult_prompt="These functions are available from the given API server:"):
        """Async version of get_prompt that ensures MCP tools are discovered first"""
        # Ensure MCP tools are discovered
        await self.discover_mcp_tools()
        return self.get_prompt(defult_prompt)

    def get_prompt(self, defult_prompt="These functions are available from the given API server:"):
        """Get prompt text describing all available tools"""
        prompts = []

        # Add prompts from OpenAPI endpoints
        for j, endpoint in enumerate(self.endpoints):
            prompt = endpoint.prompt if endpoint.prompt else defult_prompt
            prompts.append(prompt)
            for tool in endpoint.tools:
                prompts.append(f"{j+1}{self.tool_delimiter}{tool.operationId}")
            prompts.append("")

        prompt = "\n".join(prompts)

        # Add prompt from Canvas
        if self.canvas is not None:
            prompt += "\n" + self.canvas.get_prompt(0, self.tool_delimiter)

        # Add prompt from MCP
        if self.mcp is not None:
            prompt += "\n" + self.mcp.prompt + "\n"
            for tool in self.mcp.tools:
                prompt += f"mcp{self.tool_delimiter}{tool['name']}\n"
            prompt += "\n"

        return prompt

    async def call_function(self, name, arguments, token, oauth_token, tool_call_id=""):
        """Call a function from an endpoint, canvas, or MCP server"""
        parts = name.split(self.tool_delimiter)

        # Handle MCP calls
        if parts[0] == "mcp":
            if self.mcp is None:
                return json.dumps({
                    "status": "error",
                    "message": "MCP is not initialized"
                })

            # For MCP calls, the name is "mcp_server_X_tool"
            mcp_name = parts[1]  # This is the server_X_tool part
            result = await self.mcp.call_function(mcp_name, arguments, token, oauth_token)
            return result

        # Handle OpenAPI and Canvas calls
        endpoint_id = int(parts[0])
        function_name = parts[1]

        if endpoint_id == 0:
            endpoint = self.canvas
            if self.reference_provider is not None:
                new_arguments = {}
                for argument in arguments:
                    if bool(re.match(r"^call_[A-Za-z0-9]{24}$", arguments[argument])):
                        new_value = await self.reference_provider.call_function("retrieve_value_api_retrieve_value_post",
                                                                                {"key": arguments[argument]}, token, oauth_token)

                        try:
                            new_value = json.loads(new_value)["data"]
                        except:
                            pass
                        new_arguments[argument] = new_value
                    else:
                        new_arguments[argument] = arguments[argument]

                result = await endpoint.call_function(function_name, new_arguments, token, oauth_token)
            else:
                result = await endpoint.call_function(function_name, arguments, token, oauth_token)

            return result
        else:
            endpoint = self.endpoints[endpoint_id - 1]

            if endpoint == self.reference_provider:
                result = await endpoint.call_function(function_name, arguments, token, oauth_token)
                return result
            else:
                if self.reference_provider is not None:
                    # dereference arguments if nessesary

                    new_arguments = {}
                    for argument in arguments:
                        if type(arguments[argument]) == str and\
                                bool(re.match(r"^call_[A-Za-z0-9]{24}$", arguments[argument])):
                            new_value = await self.reference_provider.call_function("retrieve_value_api_retrieve_value_post",
                                                                                    {"key": arguments[argument]}, token, oauth_token)

                            try:
                                new_value = json.loads(new_value)["data"]
                            except:
                                pass

                            new_arguments[argument] = new_value
                        else:
                            new_arguments[argument] = arguments[argument]

                    result = await endpoint.call_function(function_name, new_arguments, token, oauth_token)

                    """
                    if type(result) == str:
                        with open (f"{time.time()}.txt", "w") as f:
                            f.write(result)
                    else:
                        with open (f"{time.time()}.bin", "wb") as f:
                            f.write(result)
                    """

                    try:
                        result = json.loads(result)["data"]
                    except:
                        voitta_log(">>>> ERROR JSONING RESULT >>>>>")
                        voitta_log(type(result))
                        # voitta_log (result)
                        pass

                    # store the result to the tool call database
                    if tool_call_id:
                        await self.reference_provider.call_function("store_value_api_store_value_post",
                                                                    {"key": tool_call_id,
                                                                        "value": result},
                                                                    token, oauth_token)
                        return f"reference: '{tool_call_id}'"
                    else:
                        return result
                else:
                    result = await endpoint.call_function(function_name, arguments, token, oauth_token)
                    return result

    async def call_function_by_endpoint_name(self, endpoint_name, function_name, arguments, token, oauth_token):
        endpoint = self.endpoint_directory.get(endpoint_name)
        result = await endpoint.call_function(function_name, arguments, token, oauth_token)
        return result

# rfkRouter = RFKRouter(["https://agnitio-assets-be.owlsdont.com"])
# tools = rfkRouter.get_tools()
# tool_prompt = rfkRouter.get_prompt()
