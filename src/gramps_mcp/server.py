"""Gramps Web MCP server — main entry point."""

import sys
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP

from gramps_mcp.auth import AuthManager
from gramps_mcp.client import GrampsWebAPIClient
from gramps_mcp.tools import register_all_tools


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Initialize auth and API client on startup, clean up on shutdown."""
    auth = AuthManager()
    client = GrampsWebAPIClient(auth)

    # Pre-authenticate to catch config errors early
    token = await auth.get_valid_token()
    if token.startswith("Auth error") or token.startswith("Error"):
        print(f"WARNING: {token}", file=sys.stderr)
        print("Check GRAMPS_API_URL, GRAMPS_USERNAME, GRAMPS_PASSWORD in .env", file=sys.stderr)
    else:
        print("Authenticated successfully to Gramps Web", file=sys.stderr)

    try:
        yield {"auth": auth, "client": client}
    finally:
        await client.close()


mcp = FastMCP(
    "Gramps Web MCP",
    lifespan=server_lifespan,
    instructions="MCP server for Gramps Web — manage family tree data. "
    "Supports full CRUD for people, families, events, places, sources, "
    "citations, media, notes, repositories, and tags.",
)

# ── MCP Prompts ──────────────────────────────────────────────────────


@mcp.prompt()
async def genealogy_data_entry() -> str:
    """Guide for efficient family tree data entry."""
    return """You are a genealogy data entry assistant connected to a Gramps Web family tree.

## Key Workflows

### Quick Data Entry
Use `create_person_full` for entering new people — it handles birth, death, parents, and spouse in one call.

### Updating Data
Use `update_person`, `update_family`, etc. — only specify the fields that changed. The smart merge will preserve all other data.

### Adding Relationships
- `add_child_to_family` — add a child to an existing family
- `add_spouse` — create a marriage between two existing people
- `link_parents` — set or update a person's parents

### Searching
- `search_entities` — full-text search across all data
- `search_entities_gql` — structured queries with expressions
- `list_entities` — paginated listing with optional GQL filters

### Viewing Data
- `get_person_detail` — the primary read tool: shows full person info with timeline, families, and events
- `get_entity_by_handle` / `get_entity_by_gramps_id` — quick lookup

## Data Entry Conventions

### Names
- Use full given names and surnames
- Suffix for patronymics (e.g. "Ivanovich", "Ivanovna")
- Russian names in Cyrillic are fully supported

### Dates
- Use natural date strings: "3 Jan 1900", "about 1885", "between 1914 and 1918"
- Gramps handles date ranges, approximations, and partial dates

### Event Types
- Birth, Death, Marriage, Census, Residence, Occupation, Military Service, Burial, Education, Retirement, Emigration, Immigration, etc.

### Place Types
- City, Town, Village, County, Region, State, Country, etc.
- Create places hierarchically using parent_place_handle

### Gender Codes
- 0 = unknown, 1 = male, 2 = female, 3 = other

### Source hierarchy
- Source (the document/record) → Citation (specific page/entry in that source) → attached to Person/Event/Family
- For example: "Metric book of St. Nicholas Church, 1890" is a Source. "Page 45, entry #23 — birth of Ivan Petrov" is a Citation.

## Workflow Tips

1. **Entering a new person**: Use `create_person_full` with as many details as you have
2. **Adding a census record**: Create a Source → Create a Citation → Create an Event (Census) → Link to people
3. **Building a family**: Create father → Create mother → Create children → `link_parents` for each child
4. **After any create/update**: Call `get_person_detail` to verify the result
5. **Tag important entities**: Use `create_tag` + `tag_entity` for organization

## Error Handling
- If a tool returns an error string starting with "Error:", read it and adjust your parameters
- "Conflict" errors mean the entity changed since you read it — re-read and retry
- If `create_person_full` partially fails, check the `log` field to see what succeeded
"""


@mcp.prompt()
async def russian_genealogy_guide() -> str:
    """Guide for Russian-language genealogy data."""
    return """You are working with a family tree that contains Russian-language data.

## Russian Naming Conventions
- Full name format: Имя Отчество Фамилия (Given name + Patronymic + Surname)
- Patronymics: male -ович/-евич, female -овна/-евна
- Surnames have gender variants: -ов/-ова, -ев/-ева, -ин/-ина, -ский/-ская
- Store patronymics in the `suffix` field of person names
- Maiden names: use alternate_names for women's maiden names

## Common Russian Event Types
- Рождение (Birth)
- Крещение (Christening/Baptism)
- Смерть (Death)
- Брак (Marriage) / Венчание (Church wedding)
- Перепись (Census) — especially 1897, 1926 census records
- Проживание (Residence)
- Сословие (Estate/social class)
- Военная служба (Military service)
- Переезд (Move/relocation)
- Репрессия (Repression)

## Russian Place Hierarchy
- Страна (Country): Российская Империя, СССР, Россия
- Губерния (Governorate)
- Уезд (Uyezd/district)
- Волость (Volost)
- Город (City) / Деревня (Village) / Село (Large village with church)

## Russian Sources
- Метрическая книга (Metric book / parish register)
- Ревизская сказка (Revision list / census)
- Исповедная ведомость (Confession list)
- Посемейный список (Family list)
- Свидетельство о рождении/браке/смерти (Birth/marriage/death certificate)
- Архивная справка (Archival reference)

## Transliteration
- When searching for non-Cyrillic queries, results may include both scripts
- For sources, include both original Russian and transliterated titles
"""

# ── Register all tools ───────────────────────────────────────────────

register_all_tools(mcp)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
