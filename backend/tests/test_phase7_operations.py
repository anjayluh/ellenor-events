from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.tasks import get_task_or_404
from app.schemas.testimonial import TestimonialCreate as CreateTestimonialSchema


class EmptyTaskQuery:
    def filter(self, *args):
        return self

    def first(self):
        return None


class EmptyTaskDb:
    def query(self, model):
        return EmptyTaskQuery()


def test_testimonial_requires_external_url():
    with pytest.raises(ValidationError):
        CreateTestimonialSchema(type="video", url="not-a-url", caption="Beautiful moment")


def test_testimonial_accepts_external_url_only_payload():
    testimonial = CreateTestimonialSchema(type="video", url="https://youtube.com/watch?v=abc", caption="Beautiful moment")
    assert str(testimonial.url).startswith("https://youtube.com")


def test_task_lookup_is_project_scoped():
    with pytest.raises(HTTPException) as exc_info:
        get_task_or_404(EmptyTaskDb(), project_id=uuid4(), task_id=uuid4())
    assert exc_info.value.status_code == 404
