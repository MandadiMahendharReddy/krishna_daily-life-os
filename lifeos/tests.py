from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Habit, create_today_habits_for_user


class HabitOrderingTests(TestCase):
    def test_today_habits_follow_habit_created_order(self):
        user = get_user_model().objects.create_user(username="krishna", password="secret-pass")
        first = Habit.objects.create(user=user, name="Evening walk")
        second = Habit.objects.create(user=user, name="Aarti")

        base_time = timezone.now()
        Habit.objects.filter(pk=first.pk).update(created_at=base_time)
        Habit.objects.filter(pk=second.pk).update(created_at=base_time + timedelta(minutes=1))

        today_habits = create_today_habits_for_user(user)

        self.assertEqual(
            list(today_habits.values_list("name", flat=True)),
            ["Evening walk", "Aarti"],
        )
