import re
from datetime import date


# Words that name a family of majors rather than one major, e.g.
# "Engineering students" covers Electrical and Mechanical Engineering.
MAJOR_FAMILIES = [
    "engineering",
    "business",
]


def is_student_eligible(
    eligibility: str | None,
    major: str | None,
    graduation_year: int | None,
    today: date | None = None,
) -> bool:
    """
    Decides whether a student may register for an event.

    Eligibility is free text written by the company, for example
    "All majors", "Computer Science and Data Science students", or
    "Graduating seniors (class of 2027)". Empty eligibility means open
    to everyone.
    """

    if not eligibility or not eligibility.strip():
        return True

    text = eligibility.lower()

    if "all majors" in text or "all students" in text or "open to all" in text:
        return True

    if "graduating" in text or "seniors" in text:
        if graduation_year is None:
            return False

        class_year = re.search(r"class of (\d{4})", text)

        if class_year:
            return graduation_year == int(class_year.group(1))

        current_year = (today or date.today()).year
        return graduation_year <= current_year + 1

    if not major:
        return False

    student_major = major.lower()

    if student_major in text:
        return True

    for family in MAJOR_FAMILIES:
        if f"{family} students" in text and family in student_major:
            return True

    return False
