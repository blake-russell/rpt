from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("budget", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="expensecategory",
            name="is_medical_expense",
            field=models.BooleanField(
                default=False,
                help_text="Mark true for medical/healthcare categories. These inflate at the healthcare inflation rate (not CPI) in retirement projections.",
            ),
        ),
    ]
