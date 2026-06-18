from django.db import models


class LifeEvent(models.Model):
    EVENT_TYPES = [
        ("vehicle", "Vehicle Purchase"),
        ("education", "Secondary Education"),
        ("move_out", "Leaves Household"),
        ("vacation", "Vacation / Travel"),
        ("wedding", "Wedding"),
        ("other", "Other Expense"),
    ]

    # --- Dependent-tied events (vehicle, education, move_out, wedding, other) ---
    dependent = models.ForeignKey(
        "people.Person",
        on_delete=models.CASCADE,
        related_name="life_events",
        null=True,
        blank=True,
        limit_choices_to={"role": "dependent"},
    )
    # Age-based year derivation (used when dependent is set)
    dependent_age_at_event = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age of dependent when this event occurs (required for dependent events)",
    )

    # --- Household-tied events (vacation) ---
    person = models.ForeignKey(
        "people.Person",
        on_delete=models.CASCADE,
        related_name="household_events",
        null=True,
        blank=True,
        limit_choices_to={"role__in": ["user", "spouse"]},
        help_text="Household member this event is tied to (vacation events)",
    )
    # Explicit year (required when person is set instead of dependent)
    event_year_override = models.IntegerField(
        null=True,
        blank=True,
        help_text="Year this event occurs (required for vacation / household events)",
    )

    # --- Common fields ---
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    description = models.CharField(max_length=200, blank=True)
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost in today's dollars (per occurrence)",
    )
    is_annual = models.BooleanField(
        default=False,
        help_text="If checked, this expense repeats every year starting from event year (e.g. annual vacation budget)",
    )

    class Meta:
        ordering = ["event_year_override", "dependent__name", "dependent_age_at_event"]

    @property
    def event_year(self):
        if self.event_year_override:
            return self.event_year_override
        if self.dependent and self.dependent.birth_year and self.dependent_age_at_event is not None:
            return self.dependent.birth_year + self.dependent_age_at_event
        return None

    @property
    def owner_name(self):
        if self.dependent:
            return self.dependent.name
        if self.person:
            return self.person.name
        return "—"

    def __str__(self):
        year = self.event_year if self.event_year is not None else "Unknown Year"
        annual = " (annual)" if self.is_annual else ""
        return f"{self.owner_name} — {self.get_event_type_display()} ({year}){annual}"
