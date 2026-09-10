from typing import List, Optional
from ninja import Schema


class TagOut(Schema):
    id: int
    name: str


class AuthorOut(Schema):
    id: int
    username: str


class WorkListItemOut(Schema):
    id: int
    title: str
    preview_path: str
    author: AuthorOut
    tags: List[TagOut]
    views: int
    likes: int
    allow_remix: bool
    allow_download: bool
    parent_id: Optional[int] = None
    created_at: str


class WorkCreateIn(Schema):
    title: str
    description: str = ""
    tags: List[str] = []
    source: str
    allow_remix: bool = False
    allow_download: bool = False


class RemixCreateIn(Schema):
    parent_id: int
    title: str = ""
    description: str = ""
    tags: List[str] = []
    source: str
    allow_remix: bool = False
    allow_download: bool = False


class WorkUpdateIn(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    allow_remix: Optional[bool] = None
    allow_download: Optional[bool] = None


class WorkDetailOut(Schema):
    id: int
    title: str
    description: str
    author: AuthorOut
    preview_path: str
    tags: List[TagOut]
    source: str
    allow_remix: bool
    allow_download: bool
    parent_id: Optional[int] = None
    views: int
    likes: int
    downloads: int
    liked: bool = False
    created_at: str
    updated_at: str
    remakes: List["WorkRemakeItemOut"] = []


class WorkRemakeItemOut(Schema):
    id: int
    title: str
    description: str
    preview_path: str
    author: AuthorOut
    allow_download: bool
    created_at: str


WorkDetailOut.update_forward_refs()


class PaginatedWorksOut(Schema):
    total: int
    page: int
    page_size: int
    items: List[WorkListItemOut]
