"""Pydantic input models for all entity types."""

from pydantic import BaseModel, Field


# ── Search ───────────────────────────────────────────────────────────

class SearchQuery(BaseModel):
    query: str = Field(..., description="Search text or query string")
    entity_type: str | None = Field(
        None,
        description="Filter: people, families, events, places, sources, citations, media, notes, repositories, tags",
    )
    page: int = Field(default=1, ge=0, description="Page number (0 returns all)")
    pagesize: int = Field(default=20, ge=1, le=200, description="Results per page")


class GQLQuery(BaseModel):
    expression: str = Field(..., description="Gramps Query Language expression")
    entity_type: str = Field(..., description="Entity type to query")
    page: int = Field(default=1, ge=0)
    pagesize: int = Field(default=20, ge=1, le=200)


class EntityLookup(BaseModel):
    entity_type: str = Field(..., description="Entity type: people, families, events, places, etc.")
    handle: str | None = Field(None, description="Gramps handle (UUID)")
    gramps_id: str | None = Field(None, description="User-assigned Gramps ID (e.g. I0001)")


class ListQuery(BaseModel):
    entity_type: str = Field(..., description="Entity type to list")
    page: int = Field(default=1, ge=0)
    pagesize: int = Field(default=20, ge=1, le=200)
    gql: str | None = Field(None, description="Optional GQL filter expression")
    sort: str | None = Field(None, description="Sort key (prefix with - for desc)")


class BatchGetQuery(BaseModel):
    entity_type: str = Field(..., description="Entity type to fetch")
    handles: list[str] = Field(..., description="List of handles (max 50)", max_length=50)


# ── Person ───────────────────────────────────────────────────────────

class PersonName(BaseModel):
    first_name: str | None = None
    surname: str | None = None
    suffix: str | None = None
    title: str | None = None
    call: str | None = None
    nick: str | None = None
    famnick: str | None = None


class CreatePerson(BaseModel):
    """Create a new person."""
    given_name: str = Field(..., description="Given/first name")
    surname: str = Field(..., description="Family/last name")
    suffix: str | None = Field(None, description="Name suffix (e.g. Jr., Sr.)")
    title: str | None = Field(None, description="Title prefix")
    nickname: str | None = Field(None, description="Nickname/call name")
    gender: int = Field(default=0, ge=0, le=3, description="0=unknown, 1=male, 2=female, 3=other")
    gramps_id: str | None = Field(None, description="Custom Gramps ID (auto-generated if omitted)")
    birth_date: str | None = None
    birth_place_handle: str | None = None
    death_date: str | None = None
    death_place_handle: str | None = None
    note_text: str | None = None
    tag_handles: list[str] | None = None
    private: bool = False


class UpdatePerson(BaseModel):
    """Update person fields. Only provide fields you want to change."""
    given_name: str | None = None
    surname: str | None = None
    suffix: str | None = None
    title: str | None = None
    nickname: str | None = None
    gender: int | None = Field(None, ge=0, le=3)
    gramps_id: str | None = None
    private: bool | None = None
    event_refs: list[dict] | None = None
    note_handles: list[str] | None = None
    tag_handles: list[str] | None = None


# ── Family ───────────────────────────────────────────────────────────

class CreateFamily(BaseModel):
    """Create a new family unit."""
    father_handle: str | None = Field(None, description="Handle of father")
    mother_handle: str | None = Field(None, description="Handle of mother")
    relationship_type: str = Field(default="Married", description="Married, Unmarried, Civil Union, etc.")
    child_handles: list[str] | None = Field(None, description="Handles of children to add")
    gramps_id: str | None = None
    private: bool = False


class UpdateFamily(BaseModel):
    father_handle: str | None = None
    mother_handle: str | None = None
    relationship_type: str | None = None
    child_refs: list[dict] | None = None
    event_refs: list[dict] | None = None
    private: bool | None = None


# ── Event ────────────────────────────────────────────────────────────

class CreateEvent(BaseModel):
    """Create a new event."""
    event_type: str = Field(..., description="Event type: Birth, Death, Marriage, Census, Residence, etc.")
    date: str | None = Field(None, description="Date string (e.g. '3 Jan 1900', 'about 1900')")
    description: str | None = None
    place_handle: str | None = None
    gramps_id: str | None = None
    private: bool = False


class UpdateEvent(BaseModel):
    event_type: str | None = None
    date: str | None = None
    description: str | None = None
    place_handle: str | None = None
    private: bool | None = None


# ── Place ────────────────────────────────────────────────────────────

class CreatePlace(BaseModel):
    """Create a new place."""
    name: str = Field(..., description="Place name")
    place_type: str = Field(default="Unknown", description="City, Town, Village, Country, Region, etc.")
    latitude: float | None = None
    longitude: float | None = None
    code: str | None = Field(None, description="Postal code")
    parent_place_handle: str | None = None
    gramps_id: str | None = None
    private: bool = False


class UpdatePlace(BaseModel):
    name: str | None = None
    place_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    code: str | None = None
    private: bool | None = None


# ── Source ───────────────────────────────────────────────────────────

class CreateSource(BaseModel):
    """Create a new source."""
    title: str = Field(..., description="Source title")
    author: str | None = None
    pubinfo: str | None = Field(None, description="Publication information")
    abbrev: str | None = Field(None, description="Abbreviated name")
    gramps_id: str | None = None
    private: bool = False


class UpdateSource(BaseModel):
    title: str | None = None
    author: str | None = None
    pubinfo: str | None = None
    abbrev: str | None = None
    private: bool | None = None


# ── Citation ─────────────────────────────────────────────────────────

class CreateCitation(BaseModel):
    """Create a new citation referencing a source."""
    source_handle: str = Field(..., description="Handle of the source being cited")
    page: str | None = Field(None, description="Page or location within source")
    confidence: int = Field(default=2, ge=0, le=4, description="0=VeryLow, 1=Low, 2=Normal, 3=High, 4=VeryHigh")
    date: str | None = None
    gramps_id: str | None = None
    private: bool = False


class UpdateCitation(BaseModel):
    source_handle: str | None = None
    page: str | None = None
    confidence: int | None = Field(None, ge=0, le=4)
    date: str | None = None
    private: bool | None = None


# ── Media ────────────────────────────────────────────────────────────

class CreateMedia(BaseModel):
    """Create a new media object reference."""
    path: str = Field(..., description="File path or URL to the media")
    mime: str | None = Field(None, description="MIME type (e.g. image/jpeg)")
    desc: str | None = Field(None, description="Description of the media")
    gramps_id: str | None = None
    private: bool = False


class UpdateMedia(BaseModel):
    path: str | None = None
    mime: str | None = None
    desc: str | None = None
    private: bool | None = None


# ── Note ─────────────────────────────────────────────────────────────

class CreateNote(BaseModel):
    """Create a new note."""
    text: str = Field(..., description="Note content")
    note_type: str = Field(default="General", description="General, Research, Transcript, Report, etc.")
    format: int = Field(default=0, description="0=plain text, 1=HTML")
    gramps_id: str | None = None
    private: bool = False


class UpdateNote(BaseModel):
    text: str | None = None
    note_type: str | None = None
    format: int | None = None
    private: bool | None = None


# ── Repository ───────────────────────────────────────────────────────

class CreateRepository(BaseModel):
    """Create a new repository (archive, library, etc.)."""
    name: str = Field(..., description="Repository name")
    repo_type: str = Field(default="Library", description="Library, Archive, Museum, Church, etc.")
    gramps_id: str | None = None
    private: bool = False


class UpdateRepository(BaseModel):
    name: str | None = None
    repo_type: str | None = None
    private: bool | None = None


# ── Tag ──────────────────────────────────────────────────────────────

class CreateTag(BaseModel):
    """Create a new tag."""
    name: str = Field(..., description="Tag name")
    color: str = Field(default="#000000", description="Hex color code (e.g. #FF0000)")
    priority: int = Field(default=0, ge=0, le=100)


class UpdateTag(BaseModel):
    name: str | None = None
    color: str | None = None
    priority: int | None = Field(None, ge=0, le=100)


# ── Convenience ──────────────────────────────────────────────────────

class AddChildToFamilyInput(BaseModel):
    family_handle: str = Field(..., description="Handle of the family to add child to")
    child_handle: str = Field(..., description="Handle of the child person")
    frel: str | None = Field(None, description="Relationship to father: Birth, Adopted, Stepchild, etc.")
    mrel: str | None = Field(None, description="Relationship to mother: Birth, Adopted, Stepchild, etc.")


class AddSpouseInput(BaseModel):
    person1_handle: str = Field(..., description="Handle of first spouse")
    person2_handle: str = Field(..., description="Handle of second spouse")
    relationship_type: str = Field(default="Married", description="Married, Unmarried, Civil Union, etc.")
    marriage_date: str | None = None
    marriage_place_handle: str | None = None


class SetPersonLifeEventInput(BaseModel):
    person_handle: str = Field(..., description="Handle of the person")
    date: str | None = Field(None, description="Date string")
    place_handle: str | None = None
    description: str | None = None


class LinkParentsInput(BaseModel):
    child_handle: str = Field(..., description="Handle of the child")
    father_handle: str | None = Field(None, description="Handle of the father")
    mother_handle: str | None = Field(None, description="Handle of the mother")


class CreatePersonFullInput(BaseModel):
    """Create a person with birth, death, parents, and spouse in one call."""
    given_name: str = Field(..., description="Given/first name")
    surname: str = Field(..., description="Family/last name")
    suffix: str | None = None
    title: str | None = None
    nickname: str | None = None
    gender: int = Field(default=0, ge=0, le=3, description="0=unknown, 1=male, 2=female, 3=other")
    gramps_id: str | None = None
    birth_date: str | None = None
    birth_place: str | None = None
    death_date: str | None = None
    death_place: str | None = None
    father_given: str | None = None
    father_surname: str | None = None
    mother_given: str | None = None
    mother_surname: str | None = None
    spouse_given: str | None = None
    spouse_surname: str | None = None
    marriage_date: str | None = None
    notes: list[str] | None = None
    private: bool = False


# ── Batch Delete ─────────────────────────────────────────────────────

class BatchDeleteInput(BaseModel):
    entity_type: str = Field(..., description="Entity type to delete")
    handles: list[str] = Field(..., description="List of handles to delete", max_length=50)
