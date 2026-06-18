from django import forms

from .models import Person

MONTH_CHOICES = [("", "—")] + [
    (i, date_name)
    for i, date_name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
]


class PersonForm(forms.ModelForm):
    birth_month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        required=False,
        label="Birth Month",
    )

    class Meta:
        model = Person
        fields = [
            "role",
            "name",
            "birth_month",
            "birth_year",
            "retirement_age",
            "life_expectancy_age",
            "driving_age",
            "move_out_age",
        ]
        widgets = {
            "birth_year": forms.NumberInput(
                attrs={"placeholder": "e.g. 1985", "min": 1900, "max": 2100}
            ),
            "retirement_age": forms.NumberInput(
                attrs={"placeholder": "e.g. 62", "min": 40, "max": 90}
            ),
            "life_expectancy_age": forms.NumberInput(
                attrs={"placeholder": "e.g. 90", "min": 1, "max": 130}
            ),
            "driving_age": forms.NumberInput(
                attrs={"placeholder": "e.g. 16", "min": 14, "max": 25}
            ),
            "move_out_age": forms.NumberInput(
                attrs={"placeholder": "e.g. 22", "min": 14, "max": 40}
            ),
        }
        help_texts = {
            "retirement_age": "Planned retirement age. Retirement year is calculated from birth year + this age.",
            "life_expectancy_age": "Expected age at end of life. The year is calculated automatically from birth year + this age.",
            "driving_age": "Age they are expected to start driving (for future vehicle expense planning).",
            "move_out_age": "Age they are expected to leave the household (e.g. 22 for college graduation).",
        }
