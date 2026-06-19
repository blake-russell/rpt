from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("debts", "0001_initial")]

    operations = [migrations.DeleteModel(name="DebtInfo")]
