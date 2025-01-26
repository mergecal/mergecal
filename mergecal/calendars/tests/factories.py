# ruff: noqa: FBT001
from uuid import uuid4

import factory
from factory import Faker
from factory import SubFactory
from factory.django import DjangoModelFactory

from mergecal.calendars.models import Calendar
from mergecal.calendars.models import Source
from mergecal.users.tests.factories import UserFactory


class CalendarFactory(DjangoModelFactory):
    class Meta:
        model = Calendar
        django_get_or_create = ["uuid"]

    name = Faker("sentence", nb_words=3)
    uuid = factory.LazyFunction(uuid4)
    owner = SubFactory(UserFactory)
    timezone = factory.LazyFunction(lambda: "America/New_York")  # Default timezone
    update_frequency_seconds = 43200
    remove_branding = False


class SourceFactory(DjangoModelFactory):
    class Meta:
        model = Source

    name = Faker("company")
    url = Faker("url", schemes=["https"])
    calendar = SubFactory(CalendarFactory)
    include_title = True
    include_description = True
    include_location = True
    custom_prefix = ""
    exclude_keywords = ""

    class Params:
        """Declare traits that add special behaviors to your generated instances"""

        with_prefix = factory.Trait(
            custom_prefix=factory.LazyFunction(lambda: f"[{Faker('word').generate()}]"),
        )
        with_keywords = factory.Trait(
            exclude_keywords=factory.LazyFunction(
                lambda: ", ".join(Faker("words", nb=3).generate()),
            ),
        )
        meetup = factory.Trait(
            url=factory.LazyFunction(
                lambda: f"https://www.meetup.com/{Faker('slug').generate()}/events/ical/",
            ),
        )
