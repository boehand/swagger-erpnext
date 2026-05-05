from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocTypeCreateModel(BaseModel):
    doctype: str = Field(..., description="DocType name, e.g. 'Customer'")
    data: Dict[str, Any] = Field(default_factory=dict, description="Field values for the new document")


class DocTypeUpdateModel(BaseModel):
    doctype: str = Field(..., description="DocType name")
    name: str = Field(..., description="Document name / primary key")
    data: Dict[str, Any] = Field(default_factory=dict, description="Fields to update")


class DocTypeListFilterModel(BaseModel):
    doctype: str = Field(..., description="DocType name")
    filters: Optional[List[Any]] = Field(None, description="Frappe-style filter list, e.g. [[\"field\",\"=\",\"value\"]]")
    fields: Optional[List[str]] = Field(None, description="Fields to return, e.g. [\"name\",\"modified\"]")
    limit: int = Field(20, ge=1, le=500, description="Maximum number of results")
    start: int = Field(0, ge=0, description="Pagination offset")
    order_by: str = Field("modified desc", description="Sort expression")


class DocTypeDeleteModel(BaseModel):
    doctype: str = Field(..., description="DocType name")
    name: str = Field(..., description="Document name / primary key")
