import os
import sys

import pytest
from mcp import Client, StdioServerParameters

from printready.mcp_server import mcp


@pytest.mark.asyncio
async def test_mcp_contract_has_typed_generation_and_no_physical_actions():
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    assert {"generate_part", "search_design_knowledge", "plan_part", "slice_design"} <= names
    assert not any("print_start" in name or "upload" in name for name in names)
    generate = next(tool for tool in tools if tool.name == "generate_part")
    assert "spec" in generate.input_schema["properties"]


@pytest.mark.asyncio
async def test_real_stdio_client_can_retrieve_and_plan(tmp_path):
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "printready.mcp_server"],
        env={**os.environ, "PRINTREADY_DATA_DIR": str(tmp_path / "mcp-data")},
    )
    async with Client(server) as client:
        tools = await client.list_tools()
        assert "generate_part" in {tool.name for tool in tools.tools}
        result = await client.call_tool("plan_part", {"brief": "enclosure 80 x 55 x 28 mm"})
        assert not result.is_error
        resources = await client.list_resources()
        assert "printready://profiles" in {str(resource.uri) for resource in resources.resources}
