from datetime import datetime
from pydantic import BaseModel, Field


class ListingOut(BaseModel):
    id:          str
    source:      str
    title:       str
    price:       str
    location:    str
    url:         str
    description: str
    notified:    bool
    first_seen:  datetime
    is_active:   bool

    model_config = {"from_attributes": True}


class ListingsPage(BaseModel):
    items:   list[ListingOut]
    total:   int
    page:    int
    pages:   int


class DeploymentOut(BaseModel):
    id:           str
    environment:  str
    version:      str
    image_tag:    str
    deployed_by:  str
    deployed_at:  datetime
    is_current:   bool
    rollback_of:  str | None
    notes:        str

    model_config = {"from_attributes": True}


class DeploymentCreate(BaseModel):
    environment:  str    = Field(..., pattern="^(dev|staging|prod)$")
    version:      str    = Field(..., min_length=1, max_length=80)
    image_tag:    str    = Field(..., min_length=1)
    deployed_by:  str    = "ci"
    notes:        str    = ""


class RollbackRequest(BaseModel):
    target_deployment_id: str  = Field(..., description="ID of the deployment to roll back to")
    reason:               str  = Field("", description="Why are you rolling back?")


class RollbackResponse(BaseModel):
    success:        bool
    new_deployment: DeploymentOut
    message:        str


class CrawlRunOut(BaseModel):
    id:            int
    started_at:    datetime
    finished_at:   datetime | None
    new_listings:  int
    total_scraped: int
    errors:        str
    triggered_by:  str

    model_config = {"from_attributes": True}


class CrawlTriggerResponse(BaseModel):
    run_id:    int
    message:   str


class HealthOut(BaseModel):
    status:      str
    environment: str
    version:     str
    db:          str
    