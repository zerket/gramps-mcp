"""Update tools: smart merge update for all 10 entity types."""

import json
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context


def _to_json(result: dict | list | str) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2, ensure_ascii=False)


def _changes_dict(**kwargs) -> dict:
    """Filter None values from kwargs to produce a changes dict."""
    return {k: v for k, v in kwargs.items() if v is not None}


def register_update_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def update_person(
        handle: str,
        given_name: str | None = None,
        surname: str | None = None,
        suffix: str | None = None,
        title: str | None = None,
        nickname: str | None = None,
        gender: int | None = None,
        gramps_id: str | None = None,
        private: bool | None = None,
        tag_handles: list[str] | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Update a person's fields. Only specify the fields you want to change.

        Uses smart merge: fetches current data, applies your changes, then saves.
        Other fields are left unchanged.

        Args:
            handle: Person's handle (UUID)
            given_name: New given name
            surname: New surname
            suffix: New suffix
            title: New title
            nickname: New nickname
            gender: 0=unknown, 1=male, 2=female, 3=other
            gramps_id: New Gramps ID
            private: Privacy flag
            tag_handles: Replace entire tag list
        """
        client = ctx.request_context.lifespan_context["client"]

        # Build changes for primary_name
        name_changes = _changes_dict(
            first_name=given_name,
            suffix=suffix,
            title=title,
            call=nickname,
        )
        if surname:
            name_changes["surname_list"] = [{"surname": surname, "primary": True}]

        changes = _changes_dict(
            gender=gender,
            gramps_id=gramps_id,
            private=private,
            tag_list=tag_handles,
        )
        if name_changes:
            changes["primary_name"] = name_changes

        if not changes:
            return "Error: No changes specified. Provide at least one field to update."

        result = await client.smart_merge_update("people", handle, changes)
        return _to_json(result)

    @mcp.tool()
    async def update_family(
        handle: str,
        father_handle: str | None = None,
        mother_handle: str | None = None,
        relationship_type: str | None = None,
        child_refs: list[dict] | None = None,
        private: bool | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Update a family's fields with smart merge.

        Args:
            handle: Family handle
            father_handle: New father handle
            mother_handle: New mother handle
            relationship_type: Married, Unmarried, Civil Union, etc.
            child_refs: New child reference list (replaces existing)
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        changes = _changes_dict(
            father_handle=father_handle,
            mother_handle=mother_handle,
            type=relationship_type,
            child_ref_list=child_refs,
            private=private,
        )
        if not changes:
            return "Error: No changes specified."
        result = await client.smart_merge_update("families", handle, changes)
        return _to_json(result)

    @mcp.tool()
    async def update_event(
        handle: str,
        event_type: str | None = None,
        date: str | None = None,
        description: str | None = None,
        place_handle: str | None = None,
        private: bool | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Update an event's fields.

        Args:
            handle: Event handle
            event_type: New event type (Birth, Death, Marriage, etc.)
            date: New date string
            description: New description
            place_handle: New place handle
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        changes = _changes_dict(
            type=event_type,
            description=description,
            place=place_handle,
            private=private,
        )
        if date:
            changes["date"] = {"text": date}
        if not changes:
            return "Error: No changes specified."
        result = await client.smart_merge_update("events", handle, changes)
        return _to_json(result)

    @mcp.tool()
    async def update_place(
        handle: str,
        name: str | None = None,
        place_type: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        code: str | None = None,
        private: bool | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Update a place's fields.

        Args:
            handle: Place handle
            name: New name
            place_type: City, Town, Country, etc.
            latitude: New latitude
            longitude: New longitude
            code: New postal code
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        changes = _changes_dict(
            type=place_type,
            code=code,
            private=private,
        )
        if name:
            changes["name"] = {"value": name}
        if latitude is not None:
            changes["lat"] = str(latitude)
        if longitude is not None:
            changes["long"] = str(longitude)
        if not changes:
            return "Error: No changes specified."
        result = await client.smart_merge_update("places", handle, changes)
        return _to_json(result)

    @mcp.tool()
    async def update_source(
        handle: str,
        title: str | None = None,
        author: str | None = None,
        pubinfo: str | None = None,
        abbrev: str | None = None,
        private: bool | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Update a source's fields.

        Args:
            handle: Source handle
            title: New title
            author: New author
            pubinfo: New publication info
            abbrev: New abbreviation
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        changes = _changes_dict(
            title=title,
            author=author,
            pubinfo=pubinfo,
            abbrev=abbrev,
            private=private,
        )
        if not changes:
            return "Error: No changes specified."
        result = await client.smart_merge_update("sources", handle, changes)
        return _to_json(result)

    @mcp.tool()
    async def update_citation(
        handle: str,
        source_handle: str | None = None,
        page: str | None = None,
        confidence: int | None = None,
        date: str | None = None,
        private: bool | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Update a citation's fields.

        Args:
            handle: Citation handle
            source_handle: New source handle
            page: New page reference
            confidence: 0=VeryLow, 1=Low, 2=Normal, 3=High, 4=VeryHigh
            date: New date string
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        changes = _changes_dict(
            source_handle=source_handle,
            page=page,
            confidence=confidence,
            private=private,
        )
        if date:
            changes["date"] = {"text": date}
        if not changes:
            return "Error: No changes specified."
        result = await client.smart_merge_update("citations", handle, changes)
        return _to_json(result)

    @mcp.tool()
    async def update_media(
        handle: str,
        path: str | None = None,
        mime: str | None = None,
        desc: str | None = None,
        private: bool | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Update a media object's fields.

        Args:
            handle: Media handle
            path: New file path or URL
            mime: New MIME type
            desc: New description
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        changes = _changes_dict(
            path=path,
            mime=mime,
            desc=desc,
            private=private,
        )
        if not changes:
            return "Error: No changes specified."
        result = await client.smart_merge_update("media", handle, changes)
        return _to_json(result)

    @mcp.tool()
    async def update_note(
        handle: str,
        text: str | None = None,
        note_type: str | None = None,
        format: int | None = None,
        private: bool | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Update a note's fields.

        Args:
            handle: Note handle
            text: New note content
            note_type: New type (General, Research, Transcript, etc.)
            format: 0=plain text, 1=HTML
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        changes = _changes_dict(
            type=note_type,
            format=format,
            private=private,
        )
        if text:
            changes["text"] = {"string": text}
        if not changes:
            return "Error: No changes specified."
        result = await client.smart_merge_update("notes", handle, changes)
        return _to_json(result)

    @mcp.tool()
    async def update_repository(
        handle: str,
        name: str | None = None,
        repo_type: str | None = None,
        private: bool | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Update a repository's fields.

        Args:
            handle: Repository handle
            name: New name
            repo_type: Library, Archive, Museum, etc.
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        changes = _changes_dict(
            name=name,
            type=repo_type,
            private=private,
        )
        if not changes:
            return "Error: No changes specified."
        result = await client.smart_merge_update("repositories", handle, changes)
        return _to_json(result)

    @mcp.tool()
    async def update_tag(
        handle: str,
        name: str | None = None,
        color: str | None = None,
        priority: int | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Update a tag's fields.

        Args:
            handle: Tag handle
            name: New name
            color: New hex color (e.g. '#FF0000')
            priority: New priority (0-100)
        """
        client = ctx.request_context.lifespan_context["client"]
        changes = _changes_dict(
            name=name,
            color=color,
            priority=priority,
        )
        if not changes:
            return "Error: No changes specified."
        result = await client.smart_merge_update("tags", handle, changes)
        return _to_json(result)
