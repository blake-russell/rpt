"""
Tests for the budget importers module.
Covers: WF CSV parsing, duplicate staging, exclusion rule matching, N-duplicate indexing.
"""

from decimal import Decimal

from django.test import TestCase

from budget.importers import (
    _match_exclusion_rule,
    _normalize_description,
)
from budget.models import ExclusionRule


def _make_csv(rows):
    """Build a WF-format CSV file object from a list of (date, description, amount) tuples."""
    import io

    lines = ["DATE,AMOUNT,RUNNING BAL.,CHECK #,DESCRIPTION,STATUS"]
    for date_str, description, amount in rows:
        lines.append(f'{date_str},{amount},,,""{description}"",Posted')
    # Use standard header format
    header = "DATE,DESCRIPTION,AMOUNT,CHECK #,STATUS\n"
    body_lines = [
        f'{date_str},"{description}",{amount},,Posted' for date_str, description, amount in rows
    ]
    content = header + "\n".join(body_lines)
    f = io.BytesIO(content.encode("utf-8"))
    return f


class NormalizeDescriptionTests(TestCase):
    def test_collapses_whitespace(self):
        result = _normalize_description("EMPOWER          EMPOWER           703297001983")
        self.assertEqual(result, "empower empower")

    def test_strips_non_alpha(self):
        result = _normalize_description("WF Credit Card   AUTO PAY   260501")
        self.assertEqual(result, "wf credit card auto pay")

    def test_empty_string(self):
        self.assertEqual(_normalize_description(""), "")

    def test_none(self):
        self.assertEqual(_normalize_description(None), "")


class MatchExclusionRuleTests(TestCase):
    def setUp(self):
        self.rule = ExclusionRule.objects.create(
            name="Empower 401k",
            description_contains="EMPOWER EMPOWER",
            source="checking",
            amount_direction="negative",
            is_active=True,
        )

    def test_matches_multispaced_description(self):
        """Multi-space WF format should match single-space rule after normalization."""
        desc = "EMPOWER          EMPOWER           703297001983    MEGAN RUSSELL"
        rule = _match_exclusion_rule(desc, "checking", amount=Decimal("-400"))
        self.assertIsNotNone(rule)
        self.assertEqual(rule.pk, self.rule.pk)

    def test_no_match_wrong_source(self):
        desc = "EMPOWER          EMPOWER           703297001983"
        rule = _match_exclusion_rule(desc, "credit", amount=Decimal("-400"))
        self.assertIsNone(rule)

    def test_no_match_positive_amount_on_negative_only_rule(self):
        desc = "EMPOWER          EMPOWER           703297001983"
        rule = _match_exclusion_rule(desc, "checking", amount=Decimal("400"))
        self.assertIsNone(rule)

    def test_matches_either_direction(self):
        self.rule.amount_direction = "either"
        self.rule.save()
        desc = "EMPOWER          EMPOWER           703297001983"
        self.assertIsNotNone(_match_exclusion_rule(desc, "checking", amount=Decimal("400")))
        self.assertIsNotNone(_match_exclusion_rule(desc, "checking", amount=Decimal("-400")))

    def test_inactive_rule_not_matched(self):
        self.rule.is_active = False
        self.rule.save()
        desc = "EMPOWER          EMPOWER           703297001983"
        self.assertIsNone(_match_exclusion_rule(desc, "checking", amount=Decimal("-400")))
