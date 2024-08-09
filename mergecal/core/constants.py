# mergecal/core/constants.py


# Mailjet template ids
class MailjetTemplates:
    FEEDBACK = "6172264"
    BASE = "6190328"
    FOUR_PARAGRAPHS = "6193713"
    THREE_PARAGRAPHS = "6199227"


class CalendarLimits:
    FREE = 0
    PERSONAL = 2
    BUSINESS = 5
    SUPPORTER = float("inf")


class SourceLimits:
    FREE = 0
    PERSONAL = 3
    BUSINESS = 5
    SUPPORTER = float("inf")
