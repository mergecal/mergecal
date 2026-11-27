import pytest

from mergecalweb.calendars.meetup import is_meetup_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.meetup.com/some-group/events/ical/",
        "https://meetup.com/some-group/events/ical/",
        "https://WWW.MEETUP.COM:443/some-group/",
    ],
)
def test_meetup_urls_are_recognised(url):
    assert is_meetup_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://notmeetup.com/cal.ics",
        "https://example.com/cal.ics?from=meetup.com",
        "https://example.com/meetup.com/cal.ics",
        "https://meetup.com.example.com/cal.ics",
    ],
)
def test_other_urls_are_not_meetup(url):
    assert not is_meetup_url(url)
