"""Search tools: full-text search, GQL queries, entity lookup."""

import json
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context


def register_search_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def search_entities(
        query: str,
        entity_type: str | None = None,
        page: int = 1,
        pagesize: int = 20,
        ctx: Context | None = None,
    ) -> str:
        """Full-text search across Gramps Web entities.

        Search people, families, events, places, sources, citations, media, notes,
        repositories and tags by text query. Returns paginated results with match scores.

        Args:
            query: Search text (e.g. name, place name, source title)
            entity_type: Filter by type (people, families, events, places, sources, citations, media, notes, repositories, tags). Omit to search all.
            page: Page number (0 returns all results)
            pagesize: Results per page (default 20, max 200)
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.search(query, entity_type=entity_type, page=page, pagesize=pagesize)
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def search_entities_gql(
        expression: str,
        entity_type: str,
        page: int = 1,
        pagesize: int = 20,
        ctx: Context | None = None,
    ) -> str:
        """Search entities using Gramps Query Language (GQL).

        GQL allows structured queries like 'gender=1' (males), 'media_list.length>=3' (entities with 3+ media), etc.
        Supports operators: =, !=, >, <, >=, <=, ~ (contains), !~ and logical grouping with and/or/parentheses.

        Args:
            expression: GQL expression (e.g. 'gender=1', 'primary_name.surname_list.0.surname~Kravchenko')
            entity_type: Entity type to query (people, families, events, places, etc.)
            page: Page number
            pagesize: Results per page
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.list_entities(entity_type, page=page, pagesize=pagesize, gql=expression)
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_entity_by_handle(
        entity_type: str,
        handle: str,
        ctx: Context | None = None,
    ) -> str:
        """Retrieve any entity by its Gramps handle (UUID).

        Args:
            entity_type: Entity type (people, families, events, places, sources, citations, media, notes, repositories, tags)
            handle: The Gramps handle (UUID string)
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.get_entity(entity_type, handle)
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_entity_by_gramps_id(
        entity_type: str,
        gramps_id: str,
        ctx: Context | None = None,
    ) -> str:
        """Retrieve any entity by its user-assigned Gramps ID (e.g. I0001, F0001).

        Args:
            entity_type: Entity type (people, families, events, places, etc.)
            gramps_id: The Gramps ID (e.g. 'I0001', 'F0003')
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.get_entity_by_gramps_id(entity_type, gramps_id)
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, ensure_ascii=False)
