from django.db import models


class ExpenseCategory(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="e.g. 'Mortgage', 'TV Entertainment', 'Phone Plan'",
    )
    color_hex = models.CharField(
        max_length=7,
        default="#6c757d",
        help_text="Bootstrap/Chart.js color for pie chart",
    )
    is_debt_service = models.BooleanField(
        default=False,
        help_text="Mark true for categories like mortgage/car/student loan payments.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MerchantMapping(models.Model):
    raw_description = models.CharField(
        max_length=500,
        unique=True,
        help_text="Exact string from CSV DESCRIPTION column",
    )
    friendly_name = models.CharField(
        max_length=200,
        help_text="e.g. 'Home Gas Bill'",
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["raw_description"]

    def __str__(self):
        return f"{self.raw_description} -> {self.friendly_name}"


class ExclusionRule(models.Model):
    SOURCE_CHOICES = [
        ("", "All Sources"),
        ("checking", "Checking"),
        ("credit", "Credit Card"),
    ]
    AMOUNT_DIR_CHOICES = [
        ("either", "Either (positive or negative)"),
        ("negative", "Negative only (expenses/outflows)"),
        ("positive", "Positive only (credits/inflows)"),
    ]

    name = models.CharField(max_length=120)
    description_contains = models.CharField(
        max_length=200,
        help_text="Case-insensitive substring match against CSV DESCRIPTION",
    )
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, blank=True, default="")
    amount_direction = models.CharField(
        max_length=8,
        choices=AMOUNT_DIR_CHOICES,
        default="either",
        help_text="Restrict rule to only positive or only negative amounts, or match either.",
    )
    note = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        src = self.get_source_display() if self.source else "All Sources"
        return f"{self.name} ({src})"


class Transaction(models.Model):
    SOURCE_CHOICES = [("checking", "Checking"), ("credit", "Credit Card")]

    date = models.DateField()
    raw_description = models.CharField(max_length=500)
    friendly_name = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Negative = expense, Positive = income/credit",
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    check_number = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, blank=True)
    import_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA256 of date+description+amount to prevent duplicate imports",
    )
    is_excluded = models.BooleanField(
        default=False,
        help_text="Exclude from budget math/charts (e.g., internal transfers).",
    )
    exclusion_note = models.CharField(max_length=200, blank=True)
    is_pending_duplicate = models.BooleanField(
        default=False,
        help_text="Staged for review — same date/description/amount/source already exists.",
    )
    duplicate_source_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="import_hash of the original transaction this may duplicate.",
    )

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.date} {self.raw_description} ({self.amount})"


class ImportLog(models.Model):
    BANK_DISPLAY = {"wells_fargo": "Wells Fargo"}

    imported_at = models.DateTimeField(auto_now_add=True)
    bank = models.CharField(max_length=30)
    source = models.CharField(max_length=10)
    imported_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    staged_count = models.IntegerField(default=0)
    skip_details_json = models.TextField(
        blank=True,
        help_text="JSON array of {date, description, amount, reason} for each skipped row.",
    )

    class Meta:
        ordering = ["-imported_at"]

    def __str__(self):
        return f"{self.imported_at:%Y-%m-%d %H:%M} {self.BANK_DISPLAY.get(self.bank, self.bank)} {self.source}"
