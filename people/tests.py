"""
Tests for the people app — Person model properties and constraints.
"""

from datetime import date

from django.db import IntegrityError
from django.test import TestCase

from people.models import Person


class PersonModelTests(TestCase):
    def _make_person(self, **kwargs):
        defaults = {"role": "dependent", "name": "Test"}
        defaults.update(kwargs)
        return Person.objects.create(**defaults)

    def test_life_expectancy_year_computed(self):
        p = self._make_person(birth_year=1980, life_expectancy_age=85)
        self.assertEqual(p.life_expectancy_year, 2065)

    def test_life_expectancy_year_none_when_missing_birth(self):
        p = self._make_person(life_expectancy_age=85)
        self.assertIsNone(p.life_expectancy_year)

    def test_current_age_computed(self):
        today = date.today()
        p = self._make_person(birth_year=today.year - 30, birth_month=today.month)
        self.assertEqual(p.current_age, 30)

    def test_current_age_none_when_no_birth_year(self):
        p = self._make_person()
        self.assertIsNone(p.current_age)

    def test_str_includes_role_and_age(self):
        p = self._make_person(
            name="Alice", role="dependent", birth_year=date.today().year - 10, birth_month=1
        )
        s = str(p)
        self.assertIn("Alice", s)
        self.assertIn("Dependent", s)

    def test_unique_user_constraint(self):
        Person.objects.create(role="user", name="UserA")
        with self.assertRaises(IntegrityError):
            Person.objects.create(role="user", name="UserB")

    def test_unique_spouse_constraint(self):
        Person.objects.create(role="spouse", name="SpouseA")
        with self.assertRaises(IntegrityError):
            Person.objects.create(role="spouse", name="SpouseB")

    def test_multiple_dependents_allowed(self):
        Person.objects.create(role="dependent", name="Child A")
        Person.objects.create(role="dependent", name="Child B")
        self.assertEqual(Person.objects.filter(role="dependent").count(), 2)
