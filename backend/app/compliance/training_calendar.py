from datetime import date


ANCHOR_CYCLE_START = date(2025, 9, 1)


def _period_end(start_date, years):
    return date(
        start_date.year + years,
        8,
        31,
    )


def get_cycle(evaluation_date=None):
    if evaluation_date is None:
        evaluation_date = date.today()

    years_from_anchor = (
        evaluation_date.year - ANCHOR_CYCLE_START.year
    )

    if (
        evaluation_date.month,
        evaluation_date.day,
    ) < (9, 1):
        years_from_anchor -= 1

    cycle_offset = years_from_anchor // 4

    cycle_start_year = (
        ANCHOR_CYCLE_START.year
        + (cycle_offset * 4)
    )

    cycle_start = date(
        cycle_start_year,
        9,
        1,
    )

    cycle_end = _period_end(
        cycle_start,
        4,
    )

    return {
        "start": cycle_start,
        "end": cycle_end,
        "cycle_number": cycle_offset + 1,
    }


def get_unit(evaluation_date=None):
    if evaluation_date is None:
        evaluation_date = date.today()

    cycle = get_cycle(evaluation_date)

    unit_two_start = date(
        cycle["start"].year + 2,
        9,
        1,
    )

    if evaluation_date < unit_two_start:
        unit_number = 1
        unit_start = cycle["start"]
        unit_end = _period_end(
            unit_start,
            2,
        )
    else:
        unit_number = 2
        unit_start = unit_two_start
        unit_end = cycle["end"]

    return {
        "start": unit_start,
        "end": unit_end,
        "unit_number": unit_number,
        "cycle_start": cycle["start"],
        "cycle_end": cycle["end"],
        "cycle_number": cycle["cycle_number"],
    }
