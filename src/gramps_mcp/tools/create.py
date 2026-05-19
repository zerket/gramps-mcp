"""Create tools: one tool per entity type (10 total)."""

import json
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context


def _to_json(result: dict | list | str) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2, ensure_ascii=False)


def register_create_tools(mcp: FastMCP) -> None:

    # ── People ───────────────────────────────────────────────────────

    @mcp.tool()
    async def create_person(
        given_name: str,
        surname: str,
        suffix: str | None = None,
        title: str | None = None,
        nickname: str | None = None,
        gender: int = 0,
        gramps_id: str | None = None,
        birth_date: str | None = None,
        birth_place_handle: str | None = None,
        death_date: str | None = None,
        death_place_handle: str | None = None,
        note_text: str | None = None,
        tag_handles: list[str] | None = None,
        private: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Create a new person in Gramps Web.

        Args:
            given_name: Given/first name of the person
            surname: Family/last name
            suffix: Name suffix (e.g. Jr., Sr., Ivanovich)
            title: Title prefix
            nickname: Nickname or call name
            gender: 0=unknown, 1=male, 2=female, 3=other
            gramps_id: Custom Gramps ID (auto-generated if blank)
            birth_date: Birth date string (e.g. '3 Jan 1900')
            birth_place_handle: Handle of place where person was born
            death_date: Death date string
            death_place_handle: Handle of place where person died
            note_text: Text of a note to create and link to this person
            tag_handles: Handles of tags to apply
            private: Whether this record is private
        """
        client = ctx.request_context.lifespan_context["client"]

        name_data = {"first_name": given_name, "surname_list": [{"surname": surname, "primary": True}]}
        if suffix:
            name_data["suffix"] = suffix
        if title:
            name_data["title"] = title
        if nickname:
            name_data["call"] = nickname

        person_data: dict = {
            "_class": "Person",
            "gender": gender,
            "primary_name": name_data,
        }
        if gramps_id:
            person_data["gramps_id"] = gramps_id
        if private:
            person_data["private"] = True
        if tag_handles:
            person_data["tag_list"] = tag_handles

        result = await client.create_entity("people", person_data)
        if isinstance(result, str):
            return result

        person = result if isinstance(result, dict) else {}
        person_handle = person.get("handle", "")

        # Create birth event if date or place provided
        if birth_date or birth_place_handle:
            birth_event = {"_class": "Event", "type": "Birth"}
            if birth_date:
                birth_event["date"] = {"text": birth_date}
            if birth_place_handle:
                birth_event["place"] = birth_place_handle
            birth_result = await client.create_entity("events", birth_event)
            if not isinstance(birth_result, str):
                ref = {"ref": birth_result.get("handle", "")}
                await client.smart_merge_update("people", person_handle, {"event_ref_list": [ref]})

        # Create death event if date or place provided
        if death_date or death_place_handle:
            death_event = {"_class": "Event", "type": "Death"}
            if death_date:
                death_event["date"] = {"text": death_date}
            if death_place_handle:
                death_event["place"] = death_place_handle
            death_result = await client.create_entity("events", death_event)
            if not isinstance(death_result, str):
                ref = {"ref": death_result.get("handle", "")}
                await client.smart_merge_update("people", person_handle, {"event_ref_list": [ref]})

        # Create note if text provided
        if note_text:
            note_data = {"_class": "Note", "text": {"string": note_text}, "type": "General"}
            note_result = await client.create_entity("notes", note_data)
            if not isinstance(note_result, str):
                await client.smart_merge_update("people", person_handle, {"note_list": [note_result.get("handle", "")]})

        # Fetch final enriched result
        final = await client.get_person_detail_enriched(person_handle)
        return _to_json(final)

    # ── Families ─────────────────────────────────────────────────────

    @mcp.tool()
    async def create_family(
        father_handle: str | None = None,
        mother_handle: str | None = None,
        relationship_type: str = "Married",
        child_handles: list[str] | None = None,
        gramps_id: str | None = None,
        private: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Create a new family unit linking parents and children.

        Args:
            father_handle: Handle of the father
            mother_handle: Handle of the mother
            relationship_type: Married, Unmarried, Civil Union, etc.
            child_handles: List of child person handles
            gramps_id: Custom Gramps ID
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        family_data: dict = {
            "_class": "Family",
            "type": relationship_type,
        }
        if father_handle:
            family_data["father_handle"] = father_handle
        if mother_handle:
            family_data["mother_handle"] = mother_handle
        if child_handles:
            family_data["child_ref_list"] = [{"ref": h} for h in child_handles]
        if gramps_id:
            family_data["gramps_id"] = gramps_id
        if private:
            family_data["private"] = True

        result = await client.create_entity("families", family_data)
        return _to_json(result)

    # ── Events ───────────────────────────────────────────────────────

    @mcp.tool()
    async def create_event(
        event_type: str,
        date: str | None = None,
        description: str | None = None,
        place_handle: str | None = None,
        gramps_id: str | None = None,
        private: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Create a new event.

        Args:
            event_type: Event type: Birth, Death, Marriage, Census, Residence, Occupation, Military Service, Burial, etc.
            date: Date string in natural format (e.g. '3 Jan 1900', 'about 1885', 'between 1914 and 1918')
            description: Description of the event
            place_handle: Handle of the place where event occurred
            gramps_id: Custom Gramps ID
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        event_data: dict = {"_class": "Event", "type": event_type}
        if date:
            event_data["date"] = {"text": date}
        if description:
            event_data["description"] = description
        if place_handle:
            event_data["place"] = place_handle
        if gramps_id:
            event_data["gramps_id"] = gramps_id
        if private:
            event_data["private"] = True
        result = await client.create_entity("events", event_data)
        return _to_json(result)

    # ── Places ───────────────────────────────────────────────────────

    @mcp.tool()
    async def create_place(
        name: str,
        place_type: str = "Unknown",
        latitude: float | None = None,
        longitude: float | None = None,
        code: str | None = None,
        parent_place_handle: str | None = None,
        gramps_id: str | None = None,
        private: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Create a new place.

        Args:
            name: Place name (e.g. 'Москва', 'Twin Falls, ID')
            place_type: City, Town, Village, County, State, Country, Region, etc.
            latitude: Latitude as decimal
            longitude: Longitude as decimal
            code: Postal code or other code
            parent_place_handle: Handle of parent place (for hierarchy)
            gramps_id: Custom Gramps ID
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        place_data: dict = {
            "_class": "Place",
            "name": {"value": name},
            "type": place_type,
        }
        if latitude is not None:
            place_data["lat"] = str(latitude)
        if longitude is not None:
            place_data["long"] = str(longitude)
        if code:
            place_data["code"] = code
        if parent_place_handle:
            place_data["placeref_list"] = [{"ref": parent_place_handle}]
        if gramps_id:
            place_data["gramps_id"] = gramps_id
        if private:
            place_data["private"] = True
        result = await client.create_entity("places", place_data)
        return _to_json(result)

    # ── Sources ──────────────────────────────────────────────────────

    @mcp.tool()
    async def create_source(
        title: str,
        author: str | None = None,
        pubinfo: str | None = None,
        abbrev: str | None = None,
        gramps_id: str | None = None,
        private: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Create a new source (book, document, archive record, website, etc.).

        Args:
            title: Source title (required)
            author: Author or creator
            pubinfo: Publication information (publisher, date, URL, etc.)
            abbrev: Abbreviated name for citations
            gramps_id: Custom Gramps ID
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        source_data: dict = {"_class": "Source", "title": title}
        if author:
            source_data["author"] = author
        if pubinfo:
            source_data["pubinfo"] = pubinfo
        if abbrev:
            source_data["abbrev"] = abbrev
        if gramps_id:
            source_data["gramps_id"] = gramps_id
        if private:
            source_data["private"] = True
        result = await client.create_entity("sources", source_data)
        return _to_json(result)

    # ── Citations ────────────────────────────────────────────────────

    @mcp.tool()
    async def create_citation(
        source_handle: str,
        page: str | None = None,
        confidence: int = 2,
        date: str | None = None,
        gramps_id: str | None = None,
        private: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Create a citation referencing a source.

        Args:
            source_handle: Handle of the source being cited
            page: Page or location within the source
            confidence: Confidence level: 0=VeryLow, 1=Low, 2=Normal, 3=High, 4=VeryHigh
            date: Date associated with the citation
            gramps_id: Custom Gramps ID
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        citation_data: dict = {"_class": "Citation", "source_handle": source_handle, "confidence": confidence}
        if page:
            citation_data["page"] = page
        if date:
            citation_data["date"] = {"text": date}
        if gramps_id:
            citation_data["gramps_id"] = gramps_id
        if private:
            citation_data["private"] = True
        result = await client.create_entity("citations", citation_data)
        return _to_json(result)

    # ── Media ────────────────────────────────────────────────────────

    @mcp.tool()
    async def create_media(
        path: str,
        mime: str | None = None,
        desc: str | None = None,
        gramps_id: str | None = None,
        private: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Create a new media object reference (photo, document scan, etc.).

        Note: This creates a media reference record. To upload the actual file,
        use the Gramps Web upload interface.

        Args:
            path: File path or URL to the media
            mime: MIME type (e.g. 'image/jpeg', 'application/pdf')
            desc: Description of the media
            gramps_id: Custom Gramps ID
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        media_data: dict = {"_class": "Media", "path": path}
        if mime:
            media_data["mime"] = mime
        if desc:
            media_data["desc"] = desc
        if gramps_id:
            media_data["gramps_id"] = gramps_id
        if private:
            media_data["private"] = True
        result = await client.create_entity("media", media_data)
        return _to_json(result)

    # ── Notes ────────────────────────────────────────────────────────

    @mcp.tool()
    async def create_note(
        text: str,
        note_type: str = "General",
        format: int = 0,
        gramps_id: str | None = None,
        private: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Create a new note.

        Args:
            text: Note content (text or HTML)
            note_type: Note type: General, Research, Transcript, Source text, Report, etc.
            format: 0=plain text, 1=HTML
            gramps_id: Custom Gramps ID
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        note_data: dict = {
            "_class": "Note",
            "text": {"string": text},
            "type": note_type,
            "format": format,
        }
        if gramps_id:
            note_data["gramps_id"] = gramps_id
        if private:
            note_data["private"] = True
        result = await client.create_entity("notes", note_data)
        return _to_json(result)

    # ── Repositories ─────────────────────────────────────────────────

    @mcp.tool()
    async def create_repository(
        name: str,
        repo_type: str = "Library",
        gramps_id: str | None = None,
        private: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Create a new repository (archive, library, museum, church, etc.).

        Args:
            name: Repository name
            repo_type: Repository type: Library, Archive, Museum, Church, etc.
            gramps_id: Custom Gramps ID
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        repo_data: dict = {"_class": "Repository", "name": name, "type": repo_type}
        if gramps_id:
            repo_data["gramps_id"] = gramps_id
        if private:
            repo_data["private"] = True
        result = await client.create_entity("repositories", repo_data)
        return _to_json(result)

    # ── Tags ─────────────────────────────────────────────────────────

    @mcp.tool()
    async def create_tag(
        name: str,
        color: str = "#000000",
        priority: int = 0,
        ctx: Context | None = None,
    ) -> str:
        """Create a new tag for organizing entities.

        Args:
            name: Tag name
            color: Hex color code (e.g. '#FF0000' for red)
            priority: Display priority (0-100, higher = more important)
        """
        client = ctx.request_context.lifespan_context["client"]
        tag_data: dict = {
            "_class": "Tag",
            "name": name,
            "color": color,
            "priority": priority,
        }
        result = await client.create_entity("tags", tag_data)
        return _to_json(result)
