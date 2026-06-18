from django import forms

from people.models import Person

from .models import LifeEvent

# Event types that are always tied to a dependent
DEPENDENT_TYPES = {"vehicle", "education", "move_out", "wedding", "other"}
# Event types tied to the household user
HOUSEHOLD_TYPES = {"vacation"}


class LifeEventForm(forms.ModelForm):
    class Meta:
        model = LifeEvent
        fields = [
            "event_type",
            "dependent",
            "dependent_age_at_event",
            "person",
            "event_year_override",
            "description",
            "estimated_cost",
            "is_annual",
        ]
        widgets = {
            "description": forms.TextInput(attrs={"placeholder": "Optional note"}),
            "dependent_age_at_event": forms.NumberInput(
                attrs={"min": "0", "max": "120", "placeholder": "e.g. 18"}
            ),
            "event_year_override": forms.NumberInput(
                attrs={"min": "2000", "max": "2200", "placeholder": "e.g. 2027"}
            ),
            "estimated_cost": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "placeholder": "Optional"}
            ),
        }
        help_texts = {
            "event_year_override": "Year this event first occurs.",
            "is_annual": "Check to repeat this expense every year from the event year onward in retirement projections.",
            "estimated_cost": "Cost in today's dollars. For annual events, this amount is added each year.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dependent"].queryset = Person.objects.filter(role="dependent").order_by("name")
        self.fields["dependent"].required = False
        self.fields["person"].queryset = Person.objects.filter(
            role__in=["user", "spouse"]
        ).order_by("name")
        self.fields["person"].required = False
        self.fields["person"].label = "Household Member"

    def clean(self):
        cleaned = super().clean()
        event_type = cleaned.get("event_type", "")
        if event_type in HOUSEHOLD_TYPES:
            if not cleaned.get("person"):
                self.add_error("person", "Select a household member for vacation events.")
            if not cleaned.get("event_year_override"):
                self.add_error("event_year_override", "Year is required for vacation events.")
        else:
            if not cleaned.get("dependent"):
                self.add_error("dependent", "Select a dependent for this event type.")
            if cleaned.get("dependent_age_at_event") is None:
                self.add_error("dependent_age_at_event", "Dependent's age at event is required.")
        return cleaned
