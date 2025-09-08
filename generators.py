"""Generate fake values for form fields."""

from __future__ import annotations

import random
from typing import Any

from faker import Faker
import rstr

fake = Faker()


def generate_value(field_type: str, field) -> Any:
    """Return a fake value for ``field_type``.

    ``field`` is a :class:`FieldSchema` instance from ``schema_extractor``.
    Only a small subset of generators are implemented for the demo.
    """

    if field_type == "email":
        return fake.email()
    if field_type == "phone":
        return fake.phone_number()
    if field_type == "name":
        return fake.name()
    if field_type == "date":
        return fake.date()
    if field_type == "zip":
        return fake.postcode()
    if field_type == "password":
        return fake.password(length=12)
    if field_type == "select":
        # for selects we simply choose a random option value from DOM
        options = field.constraints.get("options", [])
        if options:
            return random.choice(options)
        return None

    # default
    return fake.word()
