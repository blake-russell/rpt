from django import forms

from .models import ExclusionRule, ExpenseCategory


class CSVImportForm(forms.Form):
    BANK_CHOICES = [("wells_fargo", "Wells Fargo")]
    SOURCE_CHOICES = [("checking", "Checking"), ("credit", "Credit Card")]

    bank = forms.ChoiceField(choices=BANK_CHOICES, label="Banking Source")
    source = forms.ChoiceField(choices=SOURCE_CHOICES, label="Account Type")
    csv_file = forms.FileField(label="CSV File", help_text="Export from your banking institution")


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ["name", "color_hex", "is_debt_service"]
        widgets = {
            "color_hex": forms.TextInput(attrs={"type": "color"}),
        }


class MerchantMappingInlineForm(forms.Form):
    raw_description = forms.CharField(widget=forms.HiddenInput())
    friendly_name = forms.CharField(max_length=200)
    category = forms.ModelChoiceField(queryset=ExpenseCategory.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ExpenseCategory.objects.all().order_by("name")


class ExclusionRuleForm(forms.ModelForm):
    class Meta:
        model = ExclusionRule
        fields = ["name", "description_contains", "source", "amount_direction", "note", "is_active"]
