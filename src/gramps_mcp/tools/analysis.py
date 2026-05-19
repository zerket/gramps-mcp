"""Analysis tools: tree statistics, ancestry, relationships, timeline, orphaned entities."""

import json
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context


def register_analysis_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_tree_stats(
        ctx: Context | None = None,
    ) -> str:
        """Get database statistics: total counts of all entity types.

        Returns counts for people, families, events, places, sources, citations,
        media, notes, repositories, and tags.
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.get_metadata()
        if isinstance(result, str):
            return result

        # Extract useful stats
        counts = result.get("object_counts", {})
        db_info = result.get("database", {})
        return json.dumps({
            "database": db_info.get("name", "unknown"),
            "gramps_version": result.get("gramps_version", ""),
            "object_counts": counts,
        }, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_ancestors(
        handle: str,
        max_generations: int = 5,
        ctx: Context | None = None,
    ) -> str:
        """Get the ancestors of a person by walking up the family tree.

        Traverses parent families to build a list of ancestors organized by generation.

        Args:
            handle: Person's handle
            max_generations: Maximum generations to traverse (default 5, max 10)
        """
        if max_generations > 10:
            max_generations = 10

        client = ctx.request_context.lifespan_context["client"]

        ancestors: dict[int, list[dict]] = {}
        visited: set[str] = set()

        async def walk(person_handle: str, generation: int) -> None:
            if generation > max_generations or person_handle in visited:
                return
            visited.add(person_handle)

            person = await client.get_entity("people", person_handle)
            if isinstance(person, str):
                return

            name = person.get("primary_name", {})
            name_str = f"{name.get('first_name', '')} {name.get('surname_list', [{}])[0].get('surname', '') if name.get('surname_list') else ''}".strip()

            if generation not in ancestors:
                ancestors[generation] = []
            ancestors[generation].append({"handle": person_handle, "name": name_str})

            # Walk parent families
            for fam_handle in person.get("parent_family_list", []):
                family = await client.get_entity("families", fam_handle)
                if isinstance(family, str):
                    continue
                for parent_h in [family.get("father_handle"), family.get("mother_handle")]:
                    if parent_h and parent_h not in visited:
                        await walk(parent_h, generation + 1)

        await walk(handle, 1)
        return json.dumps({"person_handle": handle, "generations": ancestors}, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_descendants(
        handle: str,
        max_generations: int = 5,
        ctx: Context | None = None,
    ) -> str:
        """Get the descendants of a person by walking down the family tree.

        Traverses families where this person is a parent and follows children.

        Args:
            handle: Person's handle
            max_generations: Maximum generations to traverse (default 5, max 10)
        """
        if max_generations > 10:
            max_generations = 10

        client = ctx.request_context.lifespan_context["client"]

        descendants: dict[int, list[dict]] = {}
        visited: set[str] = set()

        async def walk(person_handle: str, generation: int) -> None:
            if generation > max_generations or person_handle in visited:
                return
            visited.add(person_handle)

            person = await client.get_entity("people", person_handle)
            if isinstance(person, str):
                return

            name = person.get("primary_name", {})
            name_str = f"{name.get('first_name', '')} {name.get('surname_list', [{}])[0].get('surname', '') if name.get('surname_list') else ''}".strip()

            if generation not in descendants:
                descendants[generation] = []
            descendants[generation].append({"handle": person_handle, "name": name_str})

            # Walk families where this person is a parent
            for fam_handle in person.get("family_list", []):
                family = await client.get_entity("families", fam_handle)
                if isinstance(family, str):
                    continue
                for child_ref in family.get("child_ref_list", []):
                    child_h = child_ref.get("ref") if isinstance(child_ref, dict) else child_ref
                    if child_h and child_h not in visited:
                        await walk(child_h, generation + 1)

        await walk(handle, 1)
        return json.dumps({"person_handle": handle, "generations": descendants}, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_relationship(
        person1_handle: str,
        person2_handle: str,
        all_paths: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Calculate the genealogical relationship between two people.

        Uses Gramps Web's built-in relationship calculator. Returns relationship
        description (e.g. 'third cousin', 'great-grandfather', 'uncle').

        Args:
            person1_handle: Handle of the first person
            person2_handle: Handle of the second person
            all_paths: If True, returns all possible relationship paths
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.get_relationship(person1_handle, person2_handle, all_paths)
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_person_timeline(
        handle: str,
        ctx: Context | None = None,
    ) -> str:
        """Get a chronological timeline of events for a person.

        Includes the person's own events plus events from their families
        (parents' marriage, siblings' births, etc.).

        Args:
            handle: Person's handle
        """
        client = ctx.request_context.lifespan_context["client"]
        result = await client.get_person_timeline(handle)
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def find_orphaned(
        entity_type: str = "people",
        ctx: Context | None = None,
    ) -> str:
        """Find entities with potentially missing references.

        For people: finds those with no family connections.
        For citations: finds those not linked to any source.
        For events: finds those not linked to any person or family.

        Args:
            entity_type: Type to check for orphans (people, citations, events)
        """
        client = ctx.request_context.lifespan_context["client"]

        if entity_type == "people":
            # People with no family_list and no parent_family_list
            result = await client.list_entities("people", page=0, gql="family_list.length=0 and parent_family_list.length=0")
            if isinstance(result, str):
                return result

            items = result if isinstance(result, list) else result.get("items", result.get("objects", []))
            orphans = []
            for p in items:
                name = p.get("primary_name", {})
                orphans.append({
                    "handle": p.get("handle", ""),
                    "gramps_id": p.get("gramps_id", ""),
                    "name": f"{name.get('first_name', '')} {name.get('surname_list', [{}])[0].get('surname', '') if name.get('surname_list') else ''}".strip(),
                })
            return json.dumps({"type": "people_without_families", "count": len(orphans), "items": orphans}, indent=2, ensure_ascii=False)

        elif entity_type == "citations":
            # Citations potentially missing source
            result = await client.list_entities("citations", page=1, pagesize=200)
            if isinstance(result, str):
                return result

            items = result if isinstance(result, list) else result.get("items", result.get("objects", []))
            orphans = []
            for c in items:
                sh = c.get("source_handle", "")
                if not sh:
                    orphans.append({"handle": c.get("handle", ""), "gramps_id": c.get("gramps_id", ""), "page": c.get("page", "")})
            return json.dumps({"type": "citations_without_source", "count": len(orphans), "items": orphans}, indent=2, ensure_ascii=False)

        elif entity_type == "events":
            # Events without backlinks to people/families
            result = await client.list_entities("events", page=1, pagesize=200)
            if isinstance(result, str):
                return result

            items = result if isinstance(result, list) else result.get("items", result.get("objects", []))
            orphans = []
            for e in items:
                bl = e.get("backlinks", {})
                if not bl:
                    orphans.append({
                        "handle": e.get("handle", ""),
                        "gramps_id": e.get("gramps_id", ""),
                        "type": e.get("type", ""),
                        "date": e.get("date", {}).get("text", ""),
                    })
            return json.dumps({"type": "events_without_references", "count": len(orphans), "items": orphans}, indent=2, ensure_ascii=False)

        else:
            return f"Error: Orphan detection for '{entity_type}' is not supported. Use 'people', 'citations', or 'events'."
