"""Tool handler for managing LLM tool calls."""
from __future__ import annotations

import json
from typing import Callable, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class ToolResult:
    """Result from executing a tool."""
    call_id: str
    name: str
    content: str
    success: bool


class ToolRegistry:
    """Registry mapping tool names to their implementations and schemas."""
    
    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, Callable] = {}
    
    def register(self, name: str, schema: dict, handler: Callable) -> None:
        """Register a tool with its schema and handler function."""
        self._tools[name] = schema
        self._handlers[name] = handler
    
    def get_schema(self, name: str) -> Optional[dict]:
        """Get tool schema by name."""
        return self._tools.get(name)
    
    def get_handler(self, name: str) -> Optional[Callable]:
        """Get tool handler by name."""
        return self._handlers.get(name)
    
    def get_all_schemas(self) -> list[dict]:
        """Get all tool schemas for LLM."""
        return [{"type": "function", "function": schema} for schema in self._tools.values()]
    
    def has_tool(self, name: str) -> bool:
        """Check if tool exists in registry."""
        return name in self._tools


class ToolHandler:
    """Handle tool calls from LLM, execute them in parallel, and format responses."""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
    
    def execute_tool_call(self, tool_call: Any) -> ToolResult:
        """Execute a single tool call."""
        name = tool_call.function.name
        call_id = tool_call.id
        
        handler = self.registry.get_handler(name)
        if not handler:
            logger.warning(f"Unknown tool: {name}")
            return ToolResult(
                call_id=call_id,
                name=name,
                content=json.dumps({"success": False, "error": f"Unknown tool: {name}"}),
                success=False
            )
        
        try:
            args = json.loads(tool_call.function.arguments)
            result = handler(**args)
            return ToolResult(
                call_id=call_id,
                name=name,
                content=result if isinstance(result, str) else json.dumps(result),
                success=True
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {name} - {str(e)}", extra={"call_id": call_id})
            return ToolResult(
                call_id=call_id,
                name=name,
                content=json.dumps({"success": False, "error": str(e)}),
                success=False
            )
    
    def execute_parallel(self, tool_calls: list[Any]) -> list[ToolResult]:
        """Execute multiple tool calls in parallel."""
        import concurrent.futures
        
        logger.info(f"Executing {len(tool_calls)} tool call(s)")
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.execute_tool_call, tc) for tc in tool_calls]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        sorted_results = sorted(results, key=lambda r: tool_calls.index(next(tc for tc in tool_calls if tc.id == r.call_id)))
        return sorted_results
    
    def build_tool_response_messages(self, results: list[ToolResult]) -> list[dict]:
        """Build tool response messages to append to conversation.
        
        Azure OpenAI requires separate messages for each tool result with role='tool'.
        Returns a list of messages to append to the conversation.
        """
        return [
            {
                "role": "tool",
                "tool_call_id": result.call_id,
                "name": result.name,
                "content": result.content
            }
            for result in results
        ]
