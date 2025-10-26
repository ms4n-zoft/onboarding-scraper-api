#!/usr/bin/env python
"""Test that tool response message format is correct for Azure OpenAI."""
import json
from src.ai.utils.tool_handler import ToolHandler, ToolRegistry, ToolResult

# Create a test registry and handler
registry = ToolRegistry()
registry.register(
    "test_tool",
    {
        "name": "test_tool",
        "description": "Test tool",
        "parameters": {"type": "object", "properties": {}}
    },
    lambda: "test result"
)
handler = ToolHandler(registry)

# Create sample tool results
results = [
    ToolResult(
        call_id="call_123",
        name="test_tool",
        content='{"result": "success"}',
        success=True
    ),
    ToolResult(
        call_id="call_456",
        name="test_tool",
        content='{"result": "also success"}',
        success=True
    )
]

# Build response messages (should return a list now)
messages = handler.build_tool_response_messages(results)

print("Tool response messages:")
print(json.dumps(messages, indent=2))

print("\n✅ Message format check:")
for i, msg in enumerate(messages):
    print(f"Message {i}:")
    print(f"  - role: {msg.get('role')} (should be 'tool')")
    print(f"  - tool_call_id: {msg.get('tool_call_id')} (present: {bool(msg.get('tool_call_id'))})")
    print(f"  - name: {msg.get('name')} (present: {bool(msg.get('name'))})")
    print(f"  - content: {len(msg.get('content', ''))} chars")
    
    # Validate format
    assert msg.get('role') == 'tool', f"Expected role='tool', got {msg.get('role')}"
    assert 'tool_call_id' in msg, "Missing tool_call_id"
    assert 'name' in msg, "Missing name"
    assert 'content' in msg, "Missing content"
    assert 'type' not in msg, "Should not have 'type' field (Azure uses 'role')"
    
print("\n✅ All message format checks passed!")
