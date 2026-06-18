from decimal import Decimal


def project_income(person, start_year, end_year):
    """
    Project annual household income for a person from start_year to end_year (inclusive).
    Returns dict[year -> Decimal] of total compensation (salary + avg bonuses).

    Logic:
    - Start from person's current W2 salary (is_current=True, latest effective_date).
    - Apply annual_pct raises each year (compound).
    - Apply one_time raises: in that year salary jumps to the specified amount.
    - Add average annual bonus value to each year's total.
    """
    from .models import W2Income

    current_w2 = (
        W2Income.objects.filter(person=person, is_current=True).order_by("-effective_date").first()
    )
    if not current_w2:
        return {year: Decimal("0") for year in range(start_year, end_year + 1)}

    base_salary = current_w2.annual_salary

    # Compute average annual bonus value
    avg_bonus = Decimal("0")
    for bonus in current_w2.bonuses.all():
        avg_bonus += bonus.resolved_amount()

    # Index raise schedules
    annual_pct = None
    one_time_map = {}  # year -> new salary amount
    for rs in person.raise_schedules.all():
        if rs.raise_type == "annual_pct" and rs.annual_pct:
            annual_pct = rs.annual_pct
        elif rs.raise_type == "one_time" and rs.one_time_year and rs.one_time_amount:
            one_time_map[rs.one_time_year] = rs.one_time_amount

    result = {}
    salary = base_salary
    for year in range(start_year, end_year + 1):
        if year in one_time_map:
            salary = one_time_map[year]
        elif annual_pct and year > start_year:
            salary = salary * (1 + annual_pct / 100)
        result[year] = salary + avg_bonus

    return result
