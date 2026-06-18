from datetime import date

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Person(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("spouse", "Spouse"),
        ("dependent", "Dependent"),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    name = models.CharField(max_length=100)
    birth_month = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Birth month (1–12)",
    )
    birth_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Birth year (e.g. 1985)",
    )
    life_expectancy_age = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(130)],
        help_text="Expected age at end of life — used in retirement drawdown calculations (user/spouse only)",
    )
    retirement_age = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(40), MaxValueValidator(90)],
        help_text="Planned retirement age (user/spouse only). Used to derive retirement year.",
    )
    # Dependent-only fields
    driving_age = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(14), MaxValueValidator(25)],
        help_text="Age dependent is expected to start driving (for future vehicle expense planning)",
    )
    move_out_age = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(14), MaxValueValidator(40)],
        help_text="Age dependent is expected to leave the household (for future expense reduction planning)",
    )

    class Meta:
        # Allow multiple dependents but only one user and one spouse
        constraints = [
            models.UniqueConstraint(
                fields=["role"],
                condition=models.Q(role__in=["user", "spouse"]),
                name="unique_people_user_and_spouse_role",
            )
        ]

    @property
    def life_expectancy_year(self):
        """Derived from birth_year + life_expectancy_age."""
        if self.birth_year and self.life_expectancy_age:
            return self.birth_year + self.life_expectancy_age
        return None

    @property
    def current_age(self):
        if not self.birth_year:
            return None
        today = date.today()
        age = today.year - self.birth_year
        if self.birth_month and (today.month, today.day) < (self.birth_month, 1):
            age -= 1
        return age

    def __str__(self):
        age = self.current_age
        age_str = f", age {age}" if age is not None else ""
        return f"{self.name} ({self.get_role_display()}{age_str})"
