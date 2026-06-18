"""
Management command: python manage.py seed_demo

Seeds the database with a realistic demo household for testing RPT functionality.
Also generates sample WF-format CSV files for the Budget module.

Demo household:
  John (User) — age 40, retiring at 67, life expectancy 84
  Jane (Spouse) — age 37, retiring at 64, life expectancy 87
  Jack (Dependent) — age 12, drives at 16, moves out at 22
  Sally (Dependent) — age 9, drives at 16, moves out at 18
"""

import csv
import os
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

CURRENT_YEAR = date.today().year
CURRENT_DATE = date.today()


class Command(BaseCommand):
    help = "Seed demo household data for testing RPT functionality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing data before seeding",
        )
        parser.add_argument(
            "--csv-only",
            action="store_true",
            help="Only generate CSV files (skip DB seeding)",
        )

    def handle(self, *args, **options):
        from assets.models import Account, Holding, MonthlyContribution
        from debts.models import Loan
        from income.models import Bonus, RaiseSchedule, SocialSecurity, W2Income
        from life.models import LifeEvent
        from people.models import Person
        from retirement.models import RetirementSettings

        if options["clear"] and not options["csv_only"]:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            LifeEvent.objects.all().delete()
            SocialSecurity.objects.all().delete()
            RaiseSchedule.objects.all().delete()
            Bonus.objects.all().delete()
            W2Income.objects.all().delete()
            MonthlyContribution.objects.all().delete()
            Holding.objects.all().delete()
            Account.objects.all().delete()
            Loan.objects.all().delete()
            Person.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared."))

        if not options["csv_only"]:
            self._seed_people(Person)
            self._seed_income(Person, W2Income, Bonus, RaiseSchedule, SocialSecurity)
            self._seed_assets(Account, Holding, MonthlyContribution)
            self._seed_debts(Loan)
            self._seed_life_events(Person, LifeEvent)
            self._seed_retirement_settings(RetirementSettings)

        self._generate_csv_files()

        self.stdout.write(
            self.style.SUCCESS(
                "\n✅ Demo data seeded successfully!\n"
                "   CSV files written to data/demo_checking.csv and data/demo_credit.csv\n"
                "   Import them in the Budget module (select Wells Fargo as the banking source)\n"
            )
        )

    # ── People ────────────────────────────────────────────────────────────────

    def _seed_people(self, Person):
        john_birth = CURRENT_YEAR - 40
        jane_birth = CURRENT_YEAR - 37
        jack_birth = CURRENT_YEAR - 12
        sally_birth = CURRENT_YEAR - 9

        john, created = Person.objects.update_or_create(
            role="user",
            defaults={
                "name": "John",
                "birth_year": john_birth,
                "birth_month": 6,
                "retirement_age": 67,
                "life_expectancy_age": 84,
            },
        )
        jane, created = Person.objects.update_or_create(
            role="spouse",
            defaults={
                "name": "Jane",
                "birth_year": jane_birth,
                "birth_month": 3,
                "retirement_age": 64,
                "life_expectancy_age": 87,
            },
        )
        Person.objects.update_or_create(
            role="dependent",
            name="Jack",
            defaults={
                "birth_year": jack_birth,
                "birth_month": 9,
                "driving_age": 16,
                "move_out_age": 22,
            },
        )
        Person.objects.update_or_create(
            role="dependent",
            name="Sally",
            defaults={
                "birth_year": sally_birth,
                "birth_month": 1,
                "driving_age": 16,
                "move_out_age": 18,
            },
        )
        self.stdout.write("  ✓ People: John, Jane, Jack, Sally")

    # ── Income ────────────────────────────────────────────────────────────────

    def _seed_income(self, Person, W2Income, Bonus, RaiseSchedule, SocialSecurity):
        john = Person.objects.get(role="user")
        jane = Person.objects.get(role="spouse")

        # John W2
        john_w2, _ = W2Income.objects.update_or_create(
            person=john,
            is_current=True,
            defaults={
                "employer": "Acme Corp",
                "annual_salary": Decimal("85000"),
                "effective_date": date(CURRENT_YEAR - 3, 1, 1),
            },
        )
        Bonus.objects.update_or_create(
            w2=john_w2,
            defaults={
                "bonus_type": "pct",
                "amount": Decimal("10.00"),
                "description": "Annual performance bonus",
            },
        )
        RaiseSchedule.objects.update_or_create(
            person=john,
            raise_type="annual_pct",
            defaults={"annual_pct": Decimal("2.00")},
        )
        # John SS: claims at 67 (FRA)
        SocialSecurity.objects.update_or_create(
            person=john,
            defaults={
                "planned_claim_age": 67,
                "monthly_benefit_age_62": Decimal("1850"),
                "monthly_benefit_fra": Decimal("2700"),
                "monthly_benefit_age_70": Decimal("3350"),
            },
        )

        # Jane W2
        jane_w2, _ = W2Income.objects.update_or_create(
            person=jane,
            is_current=True,
            defaults={
                "employer": "Beta Inc",
                "annual_salary": Decimal("60000"),
                "effective_date": date(CURRENT_YEAR - 2, 1, 1),
            },
        )
        Bonus.objects.update_or_create(
            w2=jane_w2,
            defaults={
                "bonus_type": "pct",
                "amount": Decimal("5.00"),
                "description": "Annual bonus",
            },
        )
        RaiseSchedule.objects.update_or_create(
            person=jane,
            raise_type="annual_pct",
            defaults={"annual_pct": Decimal("3.00")},
        )
        # Jane SS: claims at 64
        SocialSecurity.objects.update_or_create(
            person=jane,
            defaults={
                "planned_claim_age": 64,
                "monthly_benefit_age_62": Decimal("1200"),
                "monthly_benefit_fra": Decimal("1750"),
                "monthly_benefit_age_70": Decimal("2175"),
            },
        )
        self.stdout.write(
            "  ✓ Income: John $85k + 10% bonus, Jane $60k + 5% bonus; SS estimates added"
        )

    # ── Assets ────────────────────────────────────────────────────────────────

    def _seed_assets(self, Account, Holding, MonthlyContribution):
        VTI_PRICE = Decimal("285.00")

        accounts = [
            # (name, type, shares, contrib_monthly)
            ("John Traditional 401k", "401k", Decimal("80000") / VTI_PRICE, Decimal("400")),
            ("John Roth 401k", "roth_401k", Decimal("40000") / VTI_PRICE, Decimal("400")),
            ("Jane Traditional 401k", "401k", Decimal("50000") / VTI_PRICE, Decimal("300")),
            ("Jane Roth 401k", "roth_401k", Decimal("20000") / VTI_PRICE, Decimal("300")),
        ]
        for acct_name, acct_type, shares, monthly in accounts:
            acct, _ = Account.objects.update_or_create(
                name=acct_name,
                defaults={"account_type": acct_type, "institution": "Fidelity"},
            )
            holding, _ = Holding.objects.update_or_create(
                account=acct,
                ticker="VTI",
                defaults={
                    "name": "Vanguard Total Stock Market ETF",
                    "shares": shares.quantize(Decimal("0.0001")),
                    "avg_cost_basis": Decimal("220.00"),
                    "last_price": VTI_PRICE,
                    "last_price_updated": CURRENT_DATE,
                },
            )
            MonthlyContribution.objects.update_or_create(
                holding=holding,
                defaults={
                    "monthly_amount": monthly,
                    "description": f"Payroll + employer match into {acct_name}",
                },
            )
        self.stdout.write("  ✓ Assets: 4 accounts (John 401k/Roth, Jane 401k/Roth), VTI holdings")

    # ── Debts ─────────────────────────────────────────────────────────────────

    def _seed_debts(self, Loan):
        # Mortgage: $256k @ 5%, originated 2014, 30-year
        Loan.objects.update_or_create(
            description="Primary Residence",
            defaults={
                "loan_type": "mortgage",
                "property_estimated_value": Decimal("420000"),
                "expected_home_value_growth_pct": Decimal("3.50"),
                "is_primary_residence": True,
                "original_balance": Decimal("256000"),
                "current_balance": Decimal("198000"),  # approx after ~12 yrs payments
                "interest_rate_pct": Decimal("5.000"),
                "origination_date": date(2014, 6, 1),
                "maturity_date": date(2044, 6, 1),
                "monthly_payment": Decimal("1374"),
                "is_active": True,
                "is_escrowed": True,
                "homeowners_insurance_yearly": Decimal("1800"),
                "real_estate_tax_yearly": Decimal("4200"),
            },
        )
        # John car: $30k @ 8%, 5-year, bought 2025
        Loan.objects.update_or_create(
            description="John — 2025 Vehicle",
            defaults={
                "loan_type": "car",
                "original_balance": Decimal("30000"),
                "current_balance": Decimal("28500"),
                "interest_rate_pct": Decimal("8.000"),
                "origination_date": date(2025, 1, 1),
                "maturity_date": date(2030, 1, 1),
                "monthly_payment": Decimal("608"),
                "is_active": True,
                "car_insurance_yearly": Decimal("1400"),
            },
        )
        # Jane car: $18k @ 14%, 6-year, bought 2022
        Loan.objects.update_or_create(
            description="Jane — 2022 Vehicle",
            defaults={
                "loan_type": "car",
                "original_balance": Decimal("18000"),
                "current_balance": Decimal("9800"),  # approx after ~4 yrs payments
                "interest_rate_pct": Decimal("14.000"),
                "origination_date": date(2022, 6, 1),
                "maturity_date": date(2028, 6, 1),
                "monthly_payment": Decimal("368"),
                "is_active": True,
                "car_insurance_yearly": Decimal("1100"),
            },
        )
        self.stdout.write("  ✓ Debts: mortgage ($256k), John car ($30k), Jane car ($18k)")

    # ── Life Events ───────────────────────────────────────────────────────────

    def _seed_life_events(self, Person, LifeEvent):
        jack = Person.objects.get(role="dependent", name="Jack")
        sally = Person.objects.get(role="dependent", name="Sally")
        john = Person.objects.get(role="user")

        events = [
            # Jack: car at 16, move out at 22 (no college, no wedding)
            dict(
                dependent=jack,
                event_type="vehicle",
                dependent_age_at_event=16,
                description="First car for Jack",
                estimated_cost=Decimal("8000"),
            ),
            dict(
                dependent=jack,
                event_type="move_out",
                dependent_age_at_event=22,
                description="Jack leaves household",
            ),
            # Sally: car at 18, community college 18–21 ($3k/yr × 4 years), wedding at 30
            dict(
                dependent=sally,
                event_type="vehicle",
                dependent_age_at_event=18,
                description="First car for Sally",
                estimated_cost=Decimal("10000"),
            ),
            dict(
                dependent=sally,
                event_type="education",
                dependent_age_at_event=18,
                description="Community college year 1",
                estimated_cost=Decimal("3000"),
            ),
            dict(
                dependent=sally,
                event_type="education",
                dependent_age_at_event=19,
                description="Community college year 2",
                estimated_cost=Decimal("3000"),
            ),
            dict(
                dependent=sally,
                event_type="education",
                dependent_age_at_event=20,
                description="Community college year 3",
                estimated_cost=Decimal("3000"),
            ),
            dict(
                dependent=sally,
                event_type="education",
                dependent_age_at_event=21,
                description="Community college year 4",
                estimated_cost=Decimal("3000"),
            ),
            dict(
                dependent=sally,
                event_type="move_out",
                dependent_age_at_event=18,
                description="Sally leaves household",
            ),
            dict(
                dependent=sally,
                event_type="wedding",
                dependent_age_at_event=30,
                description="Sally's wedding",
                estimated_cost=Decimal("15000"),
            ),
        ]
        LifeEvent.objects.filter(dependent__in=[jack, sally]).delete()
        for ev in events:
            LifeEvent.objects.create(**ev)

        # Vacation: $10k/year starting at John's retirement year
        john_retire_year = (
            john.birth_year + john.retirement_age if john.birth_year else CURRENT_YEAR + 27
        )
        LifeEvent.objects.update_or_create(
            person=john,
            event_type="vacation",
            defaults={
                "description": "Annual retirement vacation",
                "event_year_override": john_retire_year,
                "estimated_cost": Decimal("10000"),
                "is_annual": True,
            },
        )
        self.stdout.write(
            "  ✓ Life events: Jack (car, move-out), Sally (car, 4×college, move-out, wedding), John (annual vacation $10k from retirement)"
        )

    # ── Retirement Settings ───────────────────────────────────────────────────

    def _seed_retirement_settings(self, RetirementSettings):
        settings = RetirementSettings.get()
        settings.portfolio_growth_rate_pct = Decimal("7.00")
        settings.expenses_annual_growth_pct = Decimal("3.00")
        settings.ss_cola_pct = Decimal("2.50")
        settings.healthcare_inflation_pct = Decimal("5.00")
        settings.use_budget_cashflow_for_income = True
        settings.dependent_leave_expense_reduction_pct = Decimal("10.00")
        settings.withdrawal_strategy = "traditional"
        settings.save()
        self.stdout.write(
            "  ✓ Retirement settings: 7% growth, 3% CPI, 2.5% SS COLA, 10% dep. reduction"
        )

    # ── CSV Generation ────────────────────────────────────────────────────────

    def _generate_csv_files(self):
        """Generate sample WF checking and credit card CSVs for the Budget module."""
        output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data")
        os.makedirs(output_dir, exist_ok=True)

        checking_rows = self._build_checking_rows()
        credit_rows = self._build_credit_rows()

        checking_path = os.path.join(output_dir, "demo_checking.csv")
        credit_path = os.path.join(output_dir, "demo_credit.csv")

        self._write_wf_csv(checking_path, checking_rows)
        self._write_wf_csv(credit_path, credit_rows)
        self.stdout.write(f"  ✓ CSV: {checking_path}")
        self.stdout.write(f"  ✓ CSV: {credit_path}")

    def _build_checking_rows(self):
        """3 months of checking transactions: payroll + bills."""
        rows = []
        for month_offset in range(3):
            base = date(CURRENT_YEAR, 1, 1) + timedelta(days=28 * month_offset)
            month = base.month
            year = base.year

            def d(day):
                try:
                    return date(year, month, day).strftime("%m/%d/%Y")
                except ValueError:
                    return date(year, month, 28).strftime("%m/%d/%Y")

            # John payroll (bi-weekly): ~$2700 net (85k/26 × 0.82)
            rows += [
                (d(1), "DIRECT DEP ACME CORP PAYROLL", "3265.38", "", "Posted"),
                (d(15), "DIRECT DEP ACME CORP PAYROLL", "3265.38", "", "Posted"),
            ]
            # Jane payroll (bi-weekly): ~$1900 net (60k/26 × 0.82)
            rows += [
                (d(7), "DIRECT DEP BETA INC PAYROLL", "2307.69", "", "Posted"),
                (d(21), "DIRECT DEP BETA INC PAYROLL", "2307.69", "", "Posted"),
            ]
            # Mortgage
            rows.append((d(5), "WELLS FARGO HOME MTG PMT", "-1374.00", "", "Posted"))
            # Cars
            rows.append((d(10), "AUTO LOAN PMT JOHN VEHICLE", "-608.00", "", "Posted"))
            rows.append((d(12), "AUTO LOAN PMT JANE VEHICLE", "-368.00", "", "Posted"))
            # Utilities
            rows += [
                (d(8), "ATMOS ENERGY GAS BILL", "-145.00", "", "Posted"),
                (d(9), "ONCOR ELECTRIC DELIVERY", "-210.00", "", "Posted"),
                (d(11), "AT&T WIRELESS", "-185.00", "", "Posted"),
                (d(13), "SPECTRUM INTERNET CABLE", "-120.00", "", "Posted"),
            ]
            # Groceries (checking)
            rows += [
                (d(3), "HEB GROCERY 1234", "-280.00", "", "Posted"),
                (d(17), "HEB GROCERY 1234", "-265.00", "", "Posted"),
            ]
            # Credit card payment
            rows.append((d(20), "WF Credit Card   AUTO PAY   XXXX", "-1850.00", "", "Posted"))
            # 401k contributions (to be excluded)
            rows += [
                (
                    d(1),
                    "EMPOWER          EMPOWER           401K CONTRIBUTION",
                    "-400.00",
                    "",
                    "Posted",
                ),
                (
                    d(15),
                    "EMPOWER          EMPOWER           401K CONTRIBUTION",
                    "-400.00",
                    "",
                    "Posted",
                ),
            ]
            # Savings transfer (to be excluded)
            rows.append(
                (d(5), "RECURRING TRANSFER TO SAVINGS REF #XXXXXXXX", "-500.00", "", "Posted")
            )

        return rows

    def _build_credit_rows(self):
        """3 months of credit card transactions: everyday expenses."""
        rows = []
        for month_offset in range(3):
            base = date(CURRENT_YEAR, 1, 1) + timedelta(days=28 * month_offset)
            month = base.month
            year = base.year

            def d(day):
                try:
                    return date(year, month, day).strftime("%m/%d/%Y")
                except ValueError:
                    return date(year, month, 28).strftime("%m/%d/%Y")

            # Groceries
            rows += [
                (d(2), "KROGER 1234 GROCERIES", "-195.00", "", "Posted"),
                (d(16), "WALMART GROCERY PICKUP", "-175.00", "", "Posted"),
            ]
            # Dining
            rows += [
                (d(5), "CHICK FIL A 1234", "-42.50", "", "Posted"),
                (d(11), "CHIPOTLE MEXICAN GRILL", "-38.00", "", "Posted"),
                (d(18), "PIZZA HUT 1234", "-55.00", "", "Posted"),
                (d(25), "OLIVE GARDEN 1234", "-78.00", "", "Posted"),
            ]
            # Gas
            rows += [
                (d(4), "EXXON MOBIL GAS 1234", "-65.00", "", "Posted"),
                (d(19), "SHELL GAS STATION 5678", "-70.00", "", "Posted"),
            ]
            # Subscriptions
            rows += [
                (d(1), "NETFLIX.COM", "-22.99", "", "Posted"),
                (d(1), "SPOTIFY USA", "-11.99", "", "Posted"),
                (d(3), "AMAZON PRIME", "-14.99", "", "Posted"),
            ]
            # Kids / misc
            rows += [
                (d(8), "TARGET STORES 1234", "-120.00", "", "Posted"),
                (d(22), "AMAZON.COM AMZN.COM/BILL", "-85.00", "", "Posted"),
                (d(14), "WALGREENS 1234", "-45.00", "", "Posted"),
            ]
            # Credit card payment (income — exclude)
            rows.append((d(20), "AUTOMATIC PAYMENT - THANK YOU", "1850.00", "", "Posted"))

        return rows

    def _write_wf_csv(self, path, rows):
        """Write rows in WF CSV format: DATE,AMOUNT,*,*,DESCRIPTION"""
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["DATE", "AMOUNT", "RUNNING BAL.", "CHECK #", "DESCRIPTION", "STATUS"])
            for date_str, description, amount, check, status in rows:
                writer.writerow([date_str, amount, "", check, description, status])
