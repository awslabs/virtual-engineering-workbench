import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception

MINUTE_VALUES = r"(0?[0-9]|[1-5][0-9])"
HOUR_VALUES = r"(0?[0-9]|1[0-9]|2[0-3])"
DAY_OF_MONTH_VALUES = r"(0?[1-9]|[1-2][0-9]|3[0-1])"
MONTH_VALUES = r"(0?[1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
DAY_OF_WEEK_VALUES = r"([1-7]|SUN|MON|TUE|WED|THU|FRI|SAT)"
YEAR_VALUES = r"((19[7-9][0-9])|(2[0-1][0-9][0-9]))"
DAY_OF_WEEK_HASHES = rf"({DAY_OF_WEEK_VALUES}#[1-5])"
NATURAL_NUMBERS = r"([0-9]*[1-9][0-9]*)"


@dataclass(frozen=True)
class PipelineScheduleValueObject:
    value: str


def __range_regex(values: str) -> str:
    return rf"({values}|(\*\-{values})|({values}\-{values})|({values}\-\*))"


def __list_regex(values: str) -> str:
    range_regex = __range_regex(values=values)

    return rf"({range_regex}(\,{range_regex})*)"


def __slash_regex(values: str) -> str:
    range_regex = __range_regex(values=values)

    return rf"((\*|{range_regex}|{range_regex})\/{NATURAL_NUMBERS})"


def __common_regex(values: str) -> str:
    return rf"({__list_regex(values=values)}|\*|{__slash_regex(values=values)})"


def __validate_field(regex: str, field_value: str, field_name: str) -> None:
    if not re.fullmatch(regex, field_value):
        raise domain_exception.DomainException(f"Field {field_name} doesn't match the required cron pattern.")


def from_str(value: str) -> PipelineScheduleValueObject:
    if not value:
        raise domain_exception.DomainException("Pipeline schedule cannot be empty.")
    if len(value.split(" ")) != 6:
        raise domain_exception.DomainException("Pipeline schedule must contain exactly 6 fields.")

    minute, hour, day_of_month, month, day_of_week, year = value.split(" ")

    if not ((day_of_month == "?" and day_of_week != "?") or (day_of_month != "?" and day_of_week == "?")):
        raise domain_exception.DomainException("Invalid combination of day-of-month and day-of-week - One must be a ?.")

    __validate_field(rf"^({__common_regex(values=MINUTE_VALUES)})$", minute, "minute")
    __validate_field(rf"^({__common_regex(values=HOUR_VALUES)})$", hour, "hour")
    __validate_field(
        rf"^({__common_regex(values=DAY_OF_MONTH_VALUES)}|\?|L|{DAY_OF_MONTH_VALUES}W)$", day_of_month, "day-of-month"
    )
    __validate_field(rf"^({__common_regex(values=MONTH_VALUES)})$", month, "month")
    __validate_field(
        rf"^({__list_regex(values=DAY_OF_WEEK_VALUES)}|\*|\?|L|{DAY_OF_WEEK_HASHES})$", day_of_week, "day-of-week"
    )
    __validate_field(rf"^({__common_regex(values=YEAR_VALUES)})$", year, "year")

    return PipelineScheduleValueObject(value=value)
