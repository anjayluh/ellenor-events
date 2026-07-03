from enum import StrEnum


class EventType(StrEnum):
    wedding = "wedding"
    introduction = "introduction"
    linked = "linked"


class ApiMessage(dict):
    pass
