"""Convenience tools: multi-step genealogy operations in single calls."""

import json
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context


def _to_json(result: dict | list | str) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2, ensure_ascii=False)


def register_convenience_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def add_child_to_family(
        family_handle: str,
        child_handle: str,
        frel: str | None = None,
        mrel: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Add an existing person as a child to an existing family.

        Updates both the family's child_ref_list and the child's parent_family_list.

        Args:
            family_handle: Handle of the family to add child to
            child_handle: Handle of the child person
            frel: Relationship to father (Birth, Adopted, Stepchild, etc.)
            mrel: Relationship to mother (Birth, Adopted, Stepchild, etc.)
        """
        client = ctx.request_context.lifespan_context["client"]

        # 1. Get current family
        family = await client.get_entity("families", family_handle)
        if isinstance(family, str):
            return f"Error: Could not fetch family — {family}"

        # 2. Build new child ref
        child_ref: dict = {"ref": child_handle}
        if frel:
            child_ref["frel"] = frel
        if mrel:
            child_ref["mrel"] = mrel

        # 3. Add to family via smart merge
        existing_children = family.get("child_ref_list", [])
        new_children = existing_children + [child_ref]
        result = await client.smart_merge_update("families", family_handle, {"child_ref_list": new_children})
        if isinstance(result, str):
            return f"Error updating family: {result}"

        # 4. Add parent family to child
        child = await client.get_entity("people", child_handle)
        if isinstance(child, str):
            return f"Family updated but could not update child's parent_family_list: {child}"

        parent_families = list(child.get("parent_family_list", []))
        if family_handle not in parent_families:
            parent_families.append(family_handle)
            await client.smart_merge_update("people", child_handle, {"parent_family_list": parent_families})

        return json.dumps({
            "status": "success",
            "family_handle": family_handle,
            "child_handle": child_handle,
            "child_ref": child_ref,
        }, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def add_spouse(
        person1_handle: str,
        person2_handle: str,
        relationship_type: str = "Married",
        marriage_date: str | None = None,
        marriage_place_handle: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Create a marriage/relationship between two existing people.

        Creates a new family with both spouses, and optionally a marriage event.

        Args:
            person1_handle: Handle of first spouse (typically husband)
            person2_handle: Handle of second spouse (typically wife)
            relationship_type: Married, Unmarried, Civil Union, etc.
            marriage_date: Date of marriage (e.g. '15 May 1925')
            marriage_place_handle: Handle of place where marriage occurred
        """
        client = ctx.request_context.lifespan_context["client"]

        # Determine father/mother based on gender
        p1 = await client.get_entity("people", person1_handle)
        p2 = await client.get_entity("people", person2_handle)
        if isinstance(p1, str) or isinstance(p2, str):
            return "Error: Could not fetch one or both persons."

        g1 = p1.get("gender", 0)
        g2 = p2.get("gender", 0)

        father_handle = person1_handle if g1 == 1 else (person2_handle if g2 == 1 else person1_handle)
        mother_handle = person2_handle if g1 == 1 else (person1_handle if g2 == 1 else person2_handle)

        # Create family
        family_data: dict = {
            "_class": "Family",
            "type": relationship_type,
            "father_handle": father_handle,
            "mother_handle": mother_handle,
        }
        family_result = await client.create_entity("families", family_data)
        if isinstance(family_result, str):
            return f"Error creating family: {family_result}"

        family_handle = family_result.get("handle", "") if isinstance(family_result, dict) else ""

        # Create marriage event if date or place provided
        created_events = []
        if marriage_date or marriage_place_handle:
            event_data: dict = {"_class": "Event", "type": "Marriage"}
            if marriage_date:
                event_data["date"] = {"text": marriage_date}
            if marriage_place_handle:
                event_data["place"] = marriage_place_handle
            event_result = await client.create_entity("events", event_data)
            if not isinstance(event_result, str):
                created_events.append(event_result.get("handle") if isinstance(event_result, dict) else "")
                # Link event to family
                event_ref = {"ref": created_events[-1]}
                await client.smart_merge_update("families", family_handle, {"event_ref_list": [event_ref]})

        # Update both persons' family_list
        for person_h in [person1_handle, person2_handle]:
            person = await client.get_entity("people", person_h)
            if not isinstance(person, str):
                flist = list(person.get("family_list", []))
                if family_handle not in flist:
                    flist.append(family_handle)
                    await client.smart_merge_update("people", person_h, {"family_list": flist})

        return json.dumps({
            "status": "success",
            "family_handle": family_handle,
            "father_handle": father_handle,
            "mother_handle": mother_handle,
            "relationship_type": relationship_type,
            "marriage_events": created_events,
        }, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def set_person_birth(
        person_handle: str,
        date: str | None = None,
        place_handle: str | None = None,
        description: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Set or update a person's birth event.

        Creates a new birth event and links it to the person.
        If the person already has a birth event (birth_ref_index >= 0), the existing
        event is updated instead.

        Args:
            person_handle: Handle of the person
            date: Birth date string (e.g. '3 Jan 1900')
            place_handle: Handle of the birth place
            description: Additional description
        """
        client = ctx.request_context.lifespan_context["client"]
        person = await client.get_entity("people", person_handle)
        if isinstance(person, str):
            return f"Error: {person}"

        birth_idx = person.get("birth_ref_index", -1)
        event_refs = person.get("event_ref_list", [])

        if birth_idx >= 0 and birth_idx < len(event_refs):
            # Update existing birth event
            event_handle = event_refs[birth_idx].get("ref", "")
            changes: dict = {}
            if date:
                changes["date"] = {"text": date}
            if description:
                changes["description"] = description
            if place_handle:
                changes["place"] = place_handle
            if changes:
                result = await client.smart_merge_update("events", event_handle, changes)
                return _to_json(result)
            return "Error: No date, place, or description provided."
        else:
            # Create new birth event
            event_data: dict = {"_class": "Event", "type": "Birth"}
            if date:
                event_data["date"] = {"text": date}
            if description:
                event_data["description"] = description
            if place_handle:
                event_data["place"] = place_handle

            event_result = await client.create_entity("events", event_data)
            if isinstance(event_result, str):
                return f"Error creating birth event: {event_result}"

            event_handle = event_result.get("handle", "") if isinstance(event_result, dict) else ""

            # Link to person
            new_ref = {"ref": event_handle}
            new_refs = event_refs + [new_ref]
            birth_index = len(new_refs) - 1
            merge_result = await client.smart_merge_update("people", person_handle, {
                "event_ref_list": new_refs,
                "birth_ref_index": birth_index,
            })
            return _to_json(merge_result)

    @mcp.tool()
    async def set_person_death(
        person_handle: str,
        date: str | None = None,
        place_handle: str | None = None,
        description: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Set or update a person's death event.

        Creates a new death event and links it to the person.
        If the person already has a death event (death_ref_index >= 0), the existing
        event is updated instead.

        Args:
            person_handle: Handle of the person
            date: Death date string
            place_handle: Handle of the death place
            description: Additional description
        """
        client = ctx.request_context.lifespan_context["client"]
        person = await client.get_entity("people", person_handle)
        if isinstance(person, str):
            return f"Error: {person}"

        death_idx = person.get("death_ref_index", -1)
        event_refs = person.get("event_ref_list", [])

        if death_idx >= 0 and death_idx < len(event_refs):
            event_handle = event_refs[death_idx].get("ref", "")
            changes: dict = {}
            if date:
                changes["date"] = {"text": date}
            if description:
                changes["description"] = description
            if place_handle:
                changes["place"] = place_handle
            if changes:
                result = await client.smart_merge_update("events", event_handle, changes)
                return _to_json(result)
            return "Error: No date, place, or description provided."
        else:
            event_data: dict = {"_class": "Event", "type": "Death"}
            if date:
                event_data["date"] = {"text": date}
            if description:
                event_data["description"] = description
            if place_handle:
                event_data["place"] = place_handle

            event_result = await client.create_entity("events", event_data)
            if isinstance(event_result, str):
                return f"Error creating death event: {event_result}"

            event_handle = event_result.get("handle", "") if isinstance(event_result, dict) else ""

            new_ref = {"ref": event_handle}
            new_refs = event_refs + [new_ref]
            death_index = len(new_refs) - 1
            merge_result = await client.smart_merge_update("people", person_handle, {
                "event_ref_list": new_refs,
                "death_ref_index": death_index,
            })
            return _to_json(merge_result)

    @mcp.tool()
    async def link_parents(
        child_handle: str,
        father_handle: str | None = None,
        mother_handle: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Link a person to their parents. Creates a family if needed.

        If a family with these parents already exists, adds the child to it.
        Otherwise creates a new family.

        Args:
            child_handle: Handle of the child
            father_handle: Handle of the father (optional)
            mother_handle: Handle of the mother (optional)
        """
        client = ctx.request_context.lifespan_context["client"]

        if not father_handle and not mother_handle:
            return "Error: At least one parent handle is required."

        # Check if a family with these parents already exists
        family_handle: str | None = None
        if father_handle:
            father = await client.get_entity("people", father_handle)
            if not isinstance(father, str):
                for fh in father.get("family_list", []):
                    fam = await client.get_entity("families", fh)
                    if not isinstance(fam, str):
                        if (not father_handle or fam.get("father_handle") == father_handle) and \
                           (not mother_handle or fam.get("mother_handle") == mother_handle):
                            family_handle = fh
                            break

        if family_handle:
            # Add child to existing family
            return await add_child_to_family(family_handle, child_handle, ctx=ctx)

        # Create new family
        family_data: dict = {"_class": "Family", "type": "Married"}
        if father_handle:
            family_data["father_handle"] = father_handle
        if mother_handle:
            family_data["mother_handle"] = mother_handle
        family_data["child_ref_list"] = [{"ref": child_handle}]

        result = await client.create_entity("families", family_data)
        if isinstance(result, str):
            return f"Error creating family: {result}"

        new_family_handle = result.get("handle", "") if isinstance(result, dict) else ""

        # Update parents' family_list
        for parent_h in [father_handle, mother_handle]:
            if parent_h:
                parent = await client.get_entity("people", parent_h)
                if not isinstance(parent, str):
                    flist = list(parent.get("family_list", []))
                    if new_family_handle not in flist:
                        flist.append(new_family_handle)
                        await client.smart_merge_update("people", parent_h, {"family_list": flist})

        # Update child's parent_family_list
        child = await client.get_entity("people", child_handle)
        if not isinstance(child, str):
            pfl = list(child.get("parent_family_list", []))
            if new_family_handle not in pfl:
                pfl.append(new_family_handle)
                await client.smart_merge_update("people", child_handle, {"parent_family_list": pfl})

        return json.dumps({
            "status": "success",
            "family_handle": new_family_handle,
            "father_handle": father_handle,
            "mother_handle": mother_handle,
            "child_handle": child_handle,
        }, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def create_person_full(
        given_name: str,
        surname: str,
        suffix: str | None = None,
        title: str | None = None,
        nickname: str | None = None,
        gender: int = 0,
        gramps_id: str | None = None,
        birth_date: str | None = None,
        birth_place: str | None = None,
        death_date: str | None = None,
        death_place: str | None = None,
        father_given: str | None = None,
        father_surname: str | None = None,
        mother_given: str | None = None,
        mother_surname: str | None = None,
        spouse_given: str | None = None,
        spouse_surname: str | None = None,
        marriage_date: str | None = None,
        notes: list[str] | None = None,
        private: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """Create a person with full details in a single call.

        This is the most efficient way to enter family tree data. It creates the person,
        optionally their birth/death events, parents, spouse, and notes — all in one operation.
        Each step is independent: if one part fails, earlier parts are preserved.

        Args:
            given_name: Given/first name (required)
            surname: Family/last name (required)
            suffix: Name suffix (e.g. Ivanovich, Jr.)
            title: Title prefix
            nickname: Nickname or call name
            gender: 0=unknown, 1=male, 2=female, 3=other
            gramps_id: Custom Gramps ID
            birth_date: Birth date (e.g. '3 Jan 1900', 'about 1885')
            birth_place: Name of birth place (will be created if not found)
            death_date: Death date
            death_place: Name of death place
            father_given: Father's given name (creates father if provided)
            father_surname: Father's surname
            mother_given: Mother's given name (creates mother if provided)
            mother_surname: Mother's surname
            spouse_given: Spouse's given name (creates spouse if provided)
            spouse_surname: Spouse's surname
            marriage_date: Marriage date
            notes: List of note texts to create and link
            private: Privacy flag
        """
        client = ctx.request_context.lifespan_context["client"]
        log: list[dict] = []

        # Helper: find or create place by name
        async def resolve_place(name: str) -> str | None:
            if not name:
                return None
            # Search for existing place
            result = await client.list_entities("places", gql=f"name.value~'{name}'")
            if isinstance(result, dict):
                items = result.get("items", result.get("objects", []))
                if items:
                    return items[0].get("handle", "")
            # Create new place
            place_result = await client.create_entity("places", {
                "_class": "Place",
                "name": {"value": name},
                "type": "Unknown",
            })
            if isinstance(place_result, dict):
                return place_result.get("handle", "")
            return None

        # Step 1: Create the person
        name_data = {"first_name": given_name, "surname_list": [{"surname": surname, "primary": True}]}
        if suffix:
            name_data["suffix"] = suffix
        if title:
            name_data["title"] = title
        if nickname:
            name_data["call"] = nickname

        person_data: dict = {"_class": "Person", "gender": gender, "primary_name": name_data}
        if gramps_id:
            person_data["gramps_id"] = gramps_id
        if private:
            person_data["private"] = True

        person_result = await client.create_entity("people", person_data)
        if isinstance(person_result, str):
            return f"Error creating person: {person_result}"
        person_handle = person_result.get("handle", "") if isinstance(person_result, dict) else ""
        log.append({"step": "person_created", "handle": person_handle, "name": f"{given_name} {surname}"})

        # Step 2: Birth event
        if birth_date or birth_place:
            birth_place_handle = await resolve_place(birth_place) if birth_place else None
            birth_data: dict = {"_class": "Event", "type": "Birth"}
            if birth_date:
                birth_data["date"] = {"text": birth_date}
            if birth_place_handle:
                birth_data["place"] = birth_place_handle
            be_result = await client.create_entity("events", birth_data)
            if isinstance(be_result, str):
                log.append({"step": "birth_event_error", "error": be_result})
            else:
                be_handle = be_result.get("handle", "") if isinstance(be_result, dict) else ""
                # Link to person
                merge_r = await client.smart_merge_update("people", person_handle, {
                    "event_ref_list": [{"ref": be_handle}],
                    "birth_ref_index": 0,
                })
                log.append({
                    "step": "birth_created",
                    "event_handle": be_handle,
                    "date": birth_date,
                    "place": birth_place,
                })

        # Step 3: Death event
        if death_date or death_place:
            death_place_handle = await resolve_place(death_place) if death_place else None
            death_data: dict = {"_class": "Event", "type": "Death"}
            if death_date:
                death_data["date"] = {"text": death_date}
            if death_place_handle:
                death_data["place"] = death_place_handle
            de_result = await client.create_entity("events", death_data)
            if isinstance(de_result, str):
                log.append({"step": "death_event_error", "error": de_result})
            else:
                de_handle = de_result.get("handle", "") if isinstance(de_result, dict) else ""
                # Link to person — need to preserve birth ref index
                current = await client.get_entity("people", person_handle)
                if not isinstance(current, str):
                    existing_refs = list(current.get("event_ref_list", []))
                    new_refs = existing_refs + [{"ref": de_handle}]
                    death_idx = len(new_refs) - 1
                    await client.smart_merge_update("people", person_handle, {
                        "event_ref_list": new_refs,
                        "death_ref_index": death_idx,
                    })
                log.append({
                    "step": "death_created",
                    "event_handle": de_handle,
                    "date": death_date,
                    "place": death_place,
                })

        # Step 4: Create parents
        father_handle: str | None = None
        mother_handle: str | None = None

        if father_given:
            father_result = await client.create_entity("people", {
                "_class": "Person",
                "gender": 1,
                "primary_name": {"first_name": father_given, "surname_list": [{"surname": father_surname or surname, "primary": True}]},
            })
            if isinstance(father_result, str):
                log.append({"step": "father_error", "error": father_result})
            else:
                father_handle = father_result.get("handle", "") if isinstance(father_result, dict) else ""
                log.append({"step": "father_created", "handle": father_handle, "name": f"{father_given} {father_surname or surname}"})

        if mother_given:
            mother_result = await client.create_entity("people", {
                "_class": "Person",
                "gender": 2,
                "primary_name": {"first_name": mother_given, "surname_list": [{"surname": mother_surname or surname, "primary": True}]},
            })
            if isinstance(mother_result, str):
                log.append({"step": "mother_error", "error": mother_result})
            else:
                mother_handle = mother_result.get("handle", "") if isinstance(mother_result, dict) else ""
                log.append({"step": "mother_created", "handle": mother_handle, "name": f"{mother_given} {mother_surname or surname}"})

        # Link parents to child
        if father_handle or mother_handle:
            parent_link_result = await link_parents(
                child_handle=person_handle,
                father_handle=father_handle,
                mother_handle=mother_handle,
                ctx=ctx,
            )
            log.append({"step": "parents_linked", "result": parent_link_result[:200]})

        # Step 5: Create spouse
        if spouse_given:
            spouse_result = await client.create_entity("people", {
                "_class": "Person",
                "gender": 2 if gender == 1 else 1,
                "primary_name": {"first_name": spouse_given, "surname_list": [{"surname": spouse_surname or "", "primary": True}]},
            })
            if isinstance(spouse_result, str):
                log.append({"step": "spouse_error", "error": spouse_result})
            else:
                spouse_handle = spouse_result.get("handle", "") if isinstance(spouse_result, dict) else ""
                log.append({"step": "spouse_created", "handle": spouse_handle, "name": f"{spouse_given} {spouse_surname or ''}"})

                # Create marriage family
                family_data: dict = {
                    "_class": "Family",
                    "type": "Married",
                    "father_handle": person_handle if gender == 1 else spouse_handle,
                    "mother_handle": spouse_handle if gender == 1 else person_handle,
                }
                fam_result = await client.create_entity("families", family_data)
                if not isinstance(fam_result, str):
                    fam_handle = fam_result.get("handle", "") if isinstance(fam_result, dict) else ""

                    # Marriage event
                    if marriage_date:
                        me_data: dict = {"_class": "Event", "type": "Marriage", "date": {"text": marriage_date}}
                        me_result = await client.create_entity("events", me_data)
                        if not isinstance(me_result, str):
                            me_handle = me_result.get("handle", "") if isinstance(me_result, dict) else ""
                            await client.smart_merge_update("families", fam_handle, {"event_ref_list": [{"ref": me_handle}]})

                    # Update both persons' family_list
                    for ph in [person_handle, spouse_handle]:
                        p = await client.get_entity("people", ph)
                        if not isinstance(p, str):
                            fl = list(p.get("family_list", []))
                            if fam_handle not in fl:
                                fl.append(fam_handle)
                                await client.smart_merge_update("people", ph, {"family_list": fl})

                    log.append({"step": "spouse_linked", "family_handle": fam_handle, "marriage_date": marriage_date})

        # Step 6: Create notes
        if notes:
            note_handles = []
            for note_text in notes:
                note_result = await client.create_entity("notes", {
                    "_class": "Note",
                    "text": {"string": note_text},
                    "type": "General",
                })
                if not isinstance(note_result, str):
                    nh = note_result.get("handle", "") if isinstance(note_result, dict) else ""
                    note_handles.append(nh)
            if note_handles:
                await client.smart_merge_update("people", person_handle, {"note_list": note_handles})
                log.append({"step": "notes_created", "count": len(note_handles)})

        # Final: get enriched result
        final = await client.get_person_detail_enriched(person_handle)
        return json.dumps({
            "status": "success",
            "person_handle": person_handle,
            "log": log,
            "person": final if not isinstance(final, str) else {"error": final},
        }, indent=2, ensure_ascii=False)
