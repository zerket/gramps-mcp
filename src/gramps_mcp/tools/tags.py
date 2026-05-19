"""Tag management tools: list, tag entities, untag entities."""

import json
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context


def register_tags_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_tags(
        ctx: Context | None = None,
    ) -> str:
        """List all tags in the database with their details."""
        client = ctx.request_context.lifespan_context["client"]
        result = await client.list_entities("tags", page=0)
        if isinstance(result, str):
            return result

        tags = result if isinstance(result, list) else result.get("items", result.get("objects", []))
        return json.dumps(tags, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def tag_entity(
        entity_type: str,
        handle: str,
        tag_handle: str,
        ctx: Context | None = None,
    ) -> str:
        """Add a tag to an entity.

        Uses smart merge to add the tag to the entity's tag_list without
        removing existing tags.

        Args:
            entity_type: Type of entity to tag (people, families, events, places, etc.)
            handle: Entity handle
            tag_handle: Tag handle to add
        """
        client = ctx.request_context.lifespan_context["client"]

        # Get current entity to see existing tags
        entity = await client.get_entity(entity_type, handle)
        if isinstance(entity, str):
            return f"Error: Could not fetch entity — {entity}"

        existing_tags = list(entity.get("tag_list", []))

        if tag_handle in existing_tags:
            return json.dumps({"status": "already_tagged", "handle": handle, "tag_handle": tag_handle}, ensure_ascii=False)

        new_tags = existing_tags + [tag_handle]
        result = await client.smart_merge_update(entity_type, handle, {"tag_list": new_tags})
        if isinstance(result, str):
            return result
        return json.dumps({"status": "tagged", "handle": handle, "tag_handle": tag_handle, "tag_list": new_tags}, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def untag_entity(
        entity_type: str,
        handle: str,
        tag_handle: str,
        ctx: Context | None = None,
    ) -> str:
        """Remove a tag from an entity.

        Args:
            entity_type: Type of entity to untag
            handle: Entity handle
            tag_handle: Tag handle to remove
        """
        client = ctx.request_context.lifespan_context["client"]

        entity = await client.get_entity(entity_type, handle)
        if isinstance(entity, str):
            return f"Error: Could not fetch entity — {entity}"

        existing_tags = list(entity.get("tag_list", []))

        if tag_handle not in existing_tags:
            return json.dumps({"status": "not_tagged", "handle": handle, "tag_handle": tag_handle}, ensure_ascii=False)

        new_tags = [t for t in existing_tags if t != tag_handle]
        result = await client.smart_merge_update(entity_type, handle, {"tag_list": new_tags})
        if isinstance(result, str):
            return result
        return json.dumps({"status": "untagged", "handle": handle, "tag_handle": tag_handle, "tag_list": new_tags}, indent=2, ensure_ascii=False)
