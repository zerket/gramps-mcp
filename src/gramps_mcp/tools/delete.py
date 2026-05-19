"""Delete tools: single and batch entity deletion."""

import json
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context


def register_delete_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def delete_entity(
        entity_type: str,
        handle: str,
        ctx: Context | None = None,
    ) -> str:
        """Delete a single entity by its handle.

        WARNING: This is irreversible. Always verify the handle before deleting.

        Args:
            entity_type: Type of entity to delete (people, families, events, places, sources, citations, media, notes, repositories, tags)
            handle: The entity's Gramps handle (UUID)
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.delete_entity(entity_type, handle)
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def batch_delete_entities(
        entity_type: str,
        handles: list[str],
        ctx: Context | None = None,
    ) -> str:
        """Delete multiple entities of the same type.

        Each deletion is attempted independently. Returns summary of successes and failures.

        WARNING: This is irreversible. Verify each handle before deleting.

        Args:
            entity_type: Type of entity to delete
            handles: List of handles to delete (max 50)
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.batch_delete(entity_type, handles)
        return json.dumps(result, indent=2, ensure_ascii=False)
