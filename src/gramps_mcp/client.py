import httpx
from gramps_mcp.config import settings
from gramps_mcp.auth import AuthManager

# Entity type -> API path mapping
ENTITY_PATHS: dict[str, str] = {
    "people": "people",
    "families": "families",
    "events": "events",
    "places": "places",
    "sources": "sources",
    "citations": "citations",
    "media": "media",
    "notes": "notes",
    "repositories": "repositories",
    "tags": "tags",
}

VALID_ENTITY_TYPES = list(ENTITY_PATHS.keys())


class GrampsWebAPIClient:
    """Async HTTP client for Gramps Web REST API.

    Handles JWT auth via AuthManager, 401 retry, ETags for updates,
    and smart merge for safe partial updates.
    """

    def __init__(self, auth: AuthManager) -> None:
        self.auth = auth
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.gramps_api_url,
                timeout=settings.request_timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Core request method ──────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
        retried: bool = False,
    ) -> dict | list | str:
        """Make an authenticated API request. Returns parsed JSON or error string."""
        client = await self._ensure_client()

        token = await self.auth.get_valid_token()
        if token.startswith("Auth error") or token.startswith("Error"):
            return token

        req_headers = {"Authorization": f"Bearer {token}"}
        if headers:
            req_headers.update(headers)

        try:
            resp = await client.request(
                method, path, params=params, json=json, headers=req_headers
            )
        except httpx.RequestError as e:
            return f"Error: Cannot connect to Gramps Web at {settings.gramps_api_url} — {e}"

        # 401 retry once with fresh credentials
        if resp.status_code == 401 and not retried:
            self.auth.invalidate()
            return await self._request(
                method, path, params=params, json=json, headers=headers, retried=True
            )

        if resp.status_code == 404:
            return f"Error: Not found — {path}"
        if resp.status_code == 403:
            return f"Error: Forbidden — insufficient permissions for {path}"
        if resp.status_code == 409:
            return f"Error: Conflict — {path}"
        if resp.status_code == 412:
            return f"Error: Precondition failed — object was modified by another session. Retry."
        if resp.status_code == 422:
            detail = ""
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            return f"Error: Validation failed — {detail}"
        if resp.status_code >= 400:
            return f"Error: HTTP {resp.status_code} — {resp.text[:500]}"

        try:
            return resp.json()
        except Exception:
            return resp.text

    async def _get_etag(self, entity_type: str, handle: str) -> str | None:
        """Get ETag for an entity via HEAD request."""
        client = await self._ensure_client()
        token = await self.auth.get_valid_token()
        if token.startswith("Auth error"):
            return None

        path = f"/api/{ENTITY_PATHS[entity_type]}/{handle}/"
        try:
            resp = await client.head(
                path, headers={"Authorization": f"Bearer {token}"}
            )
            return resp.headers.get("etag")
        except Exception:
            return None

    # ── CRUD: List / Get / Create / Update / Delete (per entity type) ─

    async def list_entities(
        self,
        entity_type: str,
        page: int = 1,
        pagesize: int = 20,
        gql: str | None = None,
        sort: str | None = None,
        profile: str | None = None,
    ) -> dict | list | str:
        path = f"/api/{ENTITY_PATHS[entity_type]}/"
        params: dict = {"page": page, "pagesize": pagesize}
        if gql:
            params["gql"] = gql
        if sort:
            params["sort"] = sort
        if profile:
            params["profile"] = profile
        return await self._request("GET", path, params=params)

    async def get_entity(self, entity_type: str, handle: str) -> dict | str:
        path = f"/api/{ENTITY_PATHS[entity_type]}/{handle}/"
        return await self._request("GET", path)

    async def get_entity_by_gramps_id(self, entity_type: str, gramps_id: str) -> dict | str:
        path = f"/api/{ENTITY_PATHS[entity_type]}/"
        return await self._request("GET", path, params={"gramps_id": gramps_id})

    async def create_entity(self, entity_type: str, data: dict) -> dict | str:
        path = f"/api/{ENTITY_PATHS[entity_type]}/"
        result = await self._request("POST", path, json=data)
        # POST returns a list with the new object at [0]
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result

    async def update_entity(
        self, entity_type: str, handle: str, data: dict, etag: str
    ) -> dict | str:
        path = f"/api/{ENTITY_PATHS[entity_type]}/{handle}/"
        result = await self._request("PUT", path, json=data, headers={"If-Match": etag})
        # PUT returns a list with the updated object at [0]
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result

    async def delete_entity(self, entity_type: str, handle: str) -> dict | str:
        path = f"/api/{ENTITY_PATHS[entity_type]}/{handle}/"
        result = await self._request("DELETE", path)
        # DELETE returns a list (usually [True] or [transaction_ids])
        if isinstance(result, list):
            return {"deleted": True, "handle": handle, "details": result}
        return result

    # ── Smart Merge Update ───────────────────────────────────────────

    async def smart_merge_update(
        self, entity_type: str, handle: str, changes: dict
    ) -> dict | str:
        """Safely update an entity: GET existing → merge changes → PUT with ETag.

        For list fields, merges by handle/gramps_id to avoid duplicates.
        Only keys present in `changes` are modified; others stay unchanged.
        """
        client = await self._ensure_client()
        token = await self.auth.get_valid_token()
        if token.startswith("Auth error") or token.startswith("Error"):
            return token

        path = f"/api/{ENTITY_PATHS[entity_type]}/{handle}/"
        headers = {"Authorization": f"Bearer {token}"}

        # Step 1: GET existing object
        try:
            get_resp = await client.get(path, headers=headers)
            if get_resp.status_code != 200:
                return f"Error: Cannot fetch existing {entity_type} for merge — HTTP {get_resp.status_code}"
        except httpx.RequestError as e:
            return f"Error: Connection failed during merge GET — {e}"

        etag = get_resp.headers.get("etag", "")
        existing = get_resp.json()

        # Step 2: Merge changes
        merged = dict(existing)

        # List fields that should be merged by handle (deduplicated)
        list_fields = {
            "event_ref_list", "child_ref_list", "person_ref_list",
            "media_list", "citation_list", "note_list", "tag_list",
            "address_list", "attribute_list", "alternate_names",
            "urls", "lds_ord_list", "reporef_list", "placeref_list",
            "alt_loc", "alt_names",
        }

        for key, value in changes.items():
            if key in list_fields and isinstance(value, list) and isinstance(merged.get(key), list):
                # Deduplicate by handle or gramps_id
                merged[key] = self._merge_lists(merged[key], value)
            elif key == "primary_name" and isinstance(value, dict):
                # Merge name dict into existing primary_name
                merged["primary_name"] = {**merged.get("primary_name", {}), **value}
            else:
                merged[key] = value

        # Step 3: PUT with ETag
        put_headers = {
            "Authorization": f"Bearer {token}",
            "If-Match": etag,
        }
        try:
            put_resp = await client.put(path, headers=put_headers, json=merged)
            if put_resp.status_code in (200, 201):
                result = put_resp.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0]
                return result
            if put_resp.status_code == 412:
                return "Error: Conflict — object was modified by another session. Please retry."
            return f"Error: Update failed — HTTP {put_resp.status_code} {put_resp.text[:300]}"
        except httpx.RequestError as e:
            return f"Error: Connection failed during merge PUT — {e}"

    @staticmethod
    def _merge_lists(existing_items: list, new_items: list) -> list:
        """Merge two lists of dicts, deduplicating by handle/gramps_id."""
        seen: dict[str, dict] = {}
        for item in existing_items:
            key = GrampsWebAPIClient._item_key(item)
            seen[key] = item
        for item in new_items:
            key = GrampsWebAPIClient._item_key(item)
            seen[key] = item
        return list(seen.values())

    @staticmethod
    def _item_key(item: dict | str) -> str:
        """Get a stable deduplication key for a list item."""
        if isinstance(item, dict):
            return item.get("handle") or item.get("gramps_id") or str(item)
        return str(item)

    # ── Search ───────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        entity_type: str | None = None,
        page: int = 1,
        pagesize: int = 20,
    ) -> dict | list | str:
        params: dict = {"query": query, "page": page, "pagesize": pagesize}
        if entity_type:
            params["type"] = entity_type
        return await self._request("GET", "/api/search/", params=params)

    # ── Metadata ─────────────────────────────────────────────────────

    async def get_metadata(self) -> dict | str:
        return await self._request("GET", "/api/metadata/")

    # ── Relationships ────────────────────────────────────────────────

    async def get_relationship(
        self, handle1: str, handle2: str, all_paths: bool = False
    ) -> dict | str:
        path = f"/api/relations/{handle1}/{handle2}"
        if all_paths:
            path += "/all"
        return await self._request("GET", path + "/")

    # ── Timeline ─────────────────────────────────────────────────────

    async def get_person_timeline(self, handle: str) -> dict | list | str:
        return await self._request("GET", f"/api/people/{handle}/timeline/")

    # ── Family Timeline ──────────────────────────────────────────────

    async def get_family_timeline(self, handle: str) -> dict | list | str:
        return await self._request("GET", f"/api/families/{handle}/timeline/")

    # ── Living Status ────────────────────────────────────────────────

    async def get_living_status(self, handle: str) -> dict | str:
        return await self._request("GET", f"/api/living/{handle}/")

    async def get_living_dates(self, handle: str) -> dict | str:
        return await self._request("GET", f"/api/living/{handle}/dates/")

    # ── Event Span ───────────────────────────────────────────────────

    async def get_event_span(
        self, handle1: str, handle2: str, as_age: bool = True, precision: int = 3
    ) -> dict | str:
        params = {"as_age": str(as_age).lower(), "precision": precision}
        return await self._request("GET", f"/api/events/{handle1}/span/{handle2}/", params=params)

    # ── Facts ────────────────────────────────────────────────────────

    async def get_facts(
        self,
        person_handle: str | None = None,
        living: bool | None = None,
    ) -> dict | list | str:
        params: dict = {}
        if person_handle:
            params["person"] = person_handle
        if living is not None:
            params["living"] = str(living).lower()
        return await self._request("GET", "/api/facts/", params=params)

    # ── DNA ──────────────────────────────────────────────────────────

    async def get_dna_matches(self, handle: str) -> dict | list | str:
        return await self._request("GET", f"/api/people/{handle}/dna/matches/")

    # ── Batch Create ─────────────────────────────────────────────────

    async def batch_create(self, objects: list[dict]) -> dict | list | str:
        return await self._request("POST", "/api/objects/", json=objects)

    # ── Search Reindex ───────────────────────────────────────────────

    async def search_reindex(self, full: bool = False, semantic: bool = False) -> dict | str:
        params = {"full": str(full).lower(), "semantic": str(semantic).lower()}
        return await self._request("POST", "/api/search/index/", params=params)

    # ── Tasks ────────────────────────────────────────────────────────

    async def get_task_status(self, task_id: str) -> dict | str:
        return await self._request("GET", f"/api/tasks/{task_id}/")

    # ── Person Detail (enriched) ─────────────────────────────────────

    async def get_person_detail_enriched(self, handle: str) -> dict | str:
        """Get a person with extended data: profile, families, events, timeline."""
        # Get base person with extensions
        base = await self._request(
            "GET",
            f"/api/people/{handle}/",
            params={
                "profile": "all",
                "extend": "all",
                "backlinks": "true",
            },
        )
        if isinstance(base, str):
            return base

        # Get timeline
        timeline = await self.get_person_timeline(handle)

        # Collect family details
        families = []
        for fh in base.get("family_list", []):
            f = await self.get_entity("families", fh)
            if not isinstance(f, str):
                families.append(f)

        parent_families = []
        for fh in base.get("parent_family_list", []):
            f = await self.get_entity("families", fh)
            if not isinstance(f, str):
                parent_families.append(f)

        return {
            "person": base,
            "timeline": timeline if not isinstance(timeline, str) else [],
            "families": families,
            "parent_families": parent_families,
        }

    # ── Recent Changes ───────────────────────────────────────────────

    async def list_recent_changes(self, limit: int = 20) -> dict | list | str:
        """Get recently changed objects across all types via search."""
        return await self._request(
            "GET",
            "/api/search/",
            params={"query": "*", "sort": "-change", "pagesize": limit},
        )

    # ── Batch Operations ─────────────────────────────────────────────

    async def batch_get(
        self, entity_type: str, handles: list[str]
    ) -> list[dict | str]:
        """Fetch multiple entities of the same type."""
        results = []
        for handle in handles:
            result = await self.get_entity(entity_type, handle)
            results.append(result)
        return results

    async def batch_delete(
        self, entity_type: str, handles: list[str]
    ) -> dict:
        """Delete multiple entities, reporting each result."""
        results: dict = {"succeeded": [], "failed": []}
        for handle in handles:
            result = await self.delete_entity(entity_type, handle)
            if isinstance(result, dict) and result.get("deleted"):
                results["succeeded"].append(handle)
            else:
                results["failed"].append({"handle": handle, "error": str(result)})
        return results
