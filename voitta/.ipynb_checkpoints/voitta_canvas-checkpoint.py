import json
import asyncio
import uuid
import sys

#import chainlit as cl


class CanvasDescription:
    def __init__(self):
        self.name = "canvas"
        self.prompt = """These functions facilitate basic canvas functionality. 
At all costs avoid sending same content to canvas and to the chat context. """
        self.events = {}
        self.responses = {}


    async def call_function(self, name, arguments, cl, oauth_token):
        if name == "set_canvas":
            print (f"------ {name} ------ ")
            print (cl)
        if name == "send_canvas_delta":
            await cl.send_window_message({"target":"rfk_canvas", "name": "send_canvas_delta", "arguments": arguments})
        elif name == "set_debug":
            await cl.send_window_message({"target":"rfk_canvas", "name": "set_debug", "arguments": arguments})            
        elif name == "send_COT_delta":
            await cl.send_window_message({"target":"cot_canvas", "name": "send_COT_delta", "arguments": arguments})
        elif name == "set_canvas":
            await cl.send_window_message({"target":"rfk_canvas", "name": "set_canvas", "arguments": arguments})
            return json.dumps({"status": "ok"})
        elif name == "get_canvas":
            call_id = str(uuid.uuid4())
            result = await cl.send_window_message({"target":"rfk_canvas", 
                                                   "name": "get_canvas",
                                                   "call_id": call_id})
            self.events[call_id] = asyncio.Event()
            await self.events[call_id].wait()
            response = self.responses[call_id]
            del self.responses[call_id]
            del self.events[call_id]
            
            return json.dumps({"status": "ok", "data": response})
        else:
            return json.dumps({"status": "fail", "message": f"no such function: {name}"})

    def get_prompt(self, prefix, delimiter):
        prompts = [self.prompt]
        for tool in self.get_tools(prefix, delimiter):
            prompts.append(tool["function"]["name"])
        return "\n".join(prompts)
    
    def get_tools(self, prefix, delimiter):
        return [
            {
                "type": "function",
                "function": {
                    "name": f"{prefix}{delimiter}set_canvas",
                    "description": "Set canvas state",
                    "strict": False,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content_type": {
                                "type": "string",
                                "description": "Content type, suct as text/plain, code/python, etc."
                            },
                            "content_topic": {
                                "type": "string",
                                "description": "Topic of the content of the canvas. To be inferrend if not provided"
                            },
                            "content_subtopic": {
                                "type": "string",
                                "description": "Subtopic of the content of the canvas. To be inferrend if not provided"
                            },
                            "value": {
                                "type": "string",
                                "description": "Data to put to canvas"
                            }
                        },
                        "required": ["value", "content_type", "content_topic", "content_subtopic"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": f"{prefix}{delimiter}get_canvas",
                    "description": "Get current canvas state",
                    "strict": False,
                    "properties": {},
                    "parameters": {},
                    "additionalProperties": False
                }
            }
        ]
            
        