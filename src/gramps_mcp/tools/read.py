"""Read tools: list entities, get person detail, batch fetch, recent changes."""

import json
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context


def register_read_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_entities(
        entity_type: str,
        page: int = 1,
        pagesize: int = 20,
        gql: str | None = None,
        sort: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """List entities of a given type with optional filtering and sorting.

        Args:
            entity_type: Type of entity to list (people, families, events, places, sources, citations, media, notes, repositories, tags)
            page: Page number (0 returns all)
            pagesize: Items per page (default 20, max 200)
            gql: Optional GQL filter expression
            sort: Sort key (e.g. 'surname', 'change', 'gramps_id'; prefix with '-' for descending)
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.list_entities(
            entity_type, page=page, pagesize=pagesize, gql=gql, sort=sort
        )
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_person_detail(
        handle: str,
        ctx: Context | None = None,
    ) -> str:
        """Get comprehensive details about a person.

        Returns the person's full data including: profile, extended relations,
        family memberships (as parent and child), chronological timeline of events,
        and all resolved references. This is the primary tool for viewing person data.

        Args:
            handle: Person's Gramps handle (UUID)
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.get_person_detail_enriched(handle)
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def batch_get_entities(
        entity_type: str,
        handles: list[str],
        ctx: Context | None = None,
    ) -> str:
        """Fetch multiple entities of the same type by their handles.

        Args:
            entity_type: Entity type to fetch
            handles: List of handles (max 50)
        """
        client = ctx.request_context.lifespan_context["client"]
        results = await client.batch_get(entity_type, handles)
        formatted = []
        for i, r in enumerate(results):
            if isinstance(r, str):
                formatted.append({"handle": handles[i], "error": r})
            else:
                formatted.append(r)
        return json.dumps(formatted, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def list_recent_changes(
        limit: int = 20,
        ctx: Context | None = None,
    ) -> str:
        """Get recently modified entities across the database.

        Args:
            limit: Maximum number of recent changes to return (default 20)
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.list_recent_changes(limit)
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, ensure_ascii=False)
