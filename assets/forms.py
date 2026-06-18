from django import forms

from .models import Account, Holding, MonthlyContribution


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["name", "account_type", "institution"]
        widgets = {
            "institution": forms.TextInput(
                attrs={"placeholder": "e.g. Fidelity, Vanguard, Coinbase"}
            ),
        }


class HoldingForm(forms.ModelForm):
    class Meta:
        model = Holding
        fields = ["account", "ticker", "name", "shares", "avg_cost_basis", "last_price"]
        widgets = {
            "ticker": forms.TextInput(
                attrs={
                    "placeholder": "e.g. VTI, ETH-USD, or N/A",
                    "style": "text-transform:uppercase",
                }
            ),
            "name": forms.TextInput(attrs={"placeholder": "e.g. Vanguard Total Stock Market ETF"}),
            "shares": forms.NumberInput(
                attrs={"placeholder": "e.g. 42.5", "step": "0.000001", "min": "0"}
            ),
            "avg_cost_basis": forms.NumberInput(
                attrs={"placeholder": "e.g. 185.42", "step": "0.0001", "min": "0"}
            ),
            "last_price": forms.NumberInput(
                attrs={
                    "placeholder": "Optional — leave blank for market tickers",
                    "step": "0.0001",
                    "min": "0",
                }
            ),
        }
        labels = {
            "last_price": "Current Price / Value per Share (manual override)",
        }
        help_texts = {
            "last_price": "For non-market assets (e.g. pension with ticker N/A), enter the current value per unit here manually.",
        }

    def __init__(self, *args, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        if account:
            self.fields["account"].initial = account
            self.fields["account"].widget = forms.HiddenInput()

    def clean_ticker(self):
        return self.cleaned_data["ticker"].upper().strip()


class MonthlyContributionForm(forms.ModelForm):
    class Meta:
        model = MonthlyContribution
        fields = ["holding", "monthly_amount", "description"]
        widgets = {
            "monthly_amount": forms.NumberInput(
                attrs={"placeholder": "e.g. 500.00", "step": "0.01", "min": "0"}
            ),
            "description": forms.TextInput(attrs={"placeholder": "e.g. 401k payroll deduction"}),
        }

    def __init__(self, *args, holding=None, **kwargs):
        super().__init__(*args, **kwargs)
        if holding:
            self.fields["holding"].initial = holding
            self.fields["holding"].widget = forms.HiddenInput()
        else:
            # Group holdings by account name for readability
            self.fields["holding"].queryset = Holding.objects.select_related("account").order_by(
                "account__name", "ticker"
            )
