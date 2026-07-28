"""Alerting, Notification & Event Processing package (Ch.16)."""

from src.events.contracts import EVENT_SCHEMA_VERSION, EventObject, EventSeverity, EventState
from src.events.engine import EventEngine

__all__ = ["EventEngine", "EventObject", "EventSeverity", "EventState", "EVENT_SCHEMA_VERSION"]
