from enum import Enum

from sqlmodel import Field, SQLModel


class WebhookType(Enum):
    """Enum for supported webhook service types."""

    DISCORD = "discord"
    SLACK = "slack"
    TEAMS = "teams"


class WebsiteType(Enum):
    """Enum for website data retrieval types."""

    RSS = "rss"
    SCRAPING = "scraping"


class Article(SQLModel, table=True):
    """Model representing a news article."""

    __tablename__ = "articles"

    id: int = Field(default=None, primary_key=True)
    hash: str = Field(index=True)
    title: str
    url: str
    site_name: str
    created_at: str


class Webhook(SQLModel, table=True):
    """Model representing a webhook notification endpoint."""

    __tablename__ = "webhooks"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    endpoint: str = Field(unique=True)
    service_type: WebhookType
    is_active: bool = Field(default=True)
    created_at: str


class Website(SQLModel, table=True):
    """Model representing a news website source."""

    __tablename__ = "websites"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    type: WebsiteType
    url: str = Field(unique=True)
    avatar: str | None = Field(default=None, unique=True)
    selector: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    needs_translation: bool = Field(default=False)
    target_webhook_ids: str | None = Field(default=None)
    created_at: str
