from datetime import timedelta
from calendar import monthrange

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Habit(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habits")
    name = models.CharField(max_length=120)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_user_habit_name",
            )
        ]

    def __str__(self):
        return self.name


class DailyHabit(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_habits")
    name = models.CharField(max_length=120)
    date = models.DateField(default=timezone.localdate)
    completed = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["date", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name", "date"],
                name="unique_user_habit_per_day",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.date}"


class HabitTrackingSettings(TimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="habit_tracking_settings",
    )
    start_date = models.DateField(default=timezone.localdate)

    class Meta:
        verbose_name_plural = "habit tracking settings"

    def __str__(self):
        return f"{self.user.username} habits from {self.start_date}"


class TodoItem(TimeStampedModel):
    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="todos")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["completed", "due_date", "-created_at"]

    def __str__(self):
        return self.title


class MoneyAccount(TimeStampedModel):
    ACCOUNT_CASH = "cash"
    ACCOUNT_BANK = "bank"
    ACCOUNT_CHOICES = [
        (ACCOUNT_CASH, "Cash"),
        (ACCOUNT_BANK, "Bank"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="money_accounts")
    name = models.CharField(max_length=120)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_CHOICES, default=ACCOUNT_CASH)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["account_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_user_money_account_name",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.get_account_type_display()}"


class Expense(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("food", "Food"),
        ("family", "Family"),
        ("transport", "Transport"),
        ("bills", "Bills"),
        ("education", "Education"),
        ("health", "Health"),
        ("spiritual", "Spiritual"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")
    title = models.CharField(max_length=160)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account = models.ForeignKey(
        MoneyAccount,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="expenses",
    )
    spent_on = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-spent_on", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.amount}"


class CreditCard(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="credit_cards")
    name = models.CharField(max_length=120)
    bank_name = models.CharField(max_length=120)
    due_date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["due_date", "name"]

    @property
    def reminder_date(self):
        return self.due_date - timedelta(days=5)

    @property
    def is_reminder_active(self):
        today = timezone.localdate()
        return self.reminder_date <= today <= self.due_date

    @property
    def days_until_due(self):
        today = timezone.localdate()
        return (self.due_date - today).days

    def next_month_due_date(self):
        year = self.due_date.year + (1 if self.due_date.month == 12 else 0)
        month = 1 if self.due_date.month == 12 else self.due_date.month + 1
        day = min(self.due_date.day, monthrange(year, month)[1])
        return self.due_date.replace(year=year, month=month, day=day)

    def sync_monthly_due_date(self, today=None, save=True):
        today = today or timezone.localdate()
        updated = False
        while self.due_date < today:
            self.due_date = self.next_month_due_date()
            updated = True
        if updated and save:
            self.save(update_fields=["due_date", "updated_at"])
        return updated

    def __str__(self):
        return f"{self.bank_name} {self.name}"


class Subscription(TimeStampedModel):
    BILLING_MONTHLY = "monthly"
    BILLING_YEARLY = "yearly"
    BILLING_CHOICES = [
        (BILLING_MONTHLY, "Monthly"),
        (BILLING_YEARLY, "Yearly"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    renewal_date = models.DateField()
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CHOICES, default=BILLING_MONTHLY)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["active", "renewal_date"]

    @property
    def is_renewal_due_soon(self):
        today = timezone.localdate()
        return self.active and today <= self.renewal_date <= today + timedelta(days=5)

    @property
    def days_until_renewal(self):
        today = timezone.localdate()
        return (self.renewal_date - today).days

    def __str__(self):
        return self.name


class StudySession(TimeStampedModel):
    SUBJECT_CHOICES = [
        ("gita", "Bhagavad Gita"),
        ("english", "English"),
        ("sanskrit", "Sanskrit"),
        ("vocal", "Vocal Practice"),
        ("career", "Career Study"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="study_sessions")
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, default="gita")
    title = models.CharField(max_length=160)
    minutes = models.PositiveIntegerField(default=15)
    studied_on = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-studied_on", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.minutes} minutes"


def get_habit_tracking_settings(user):
    settings, _ = HabitTrackingSettings.objects.get_or_create(user=user)
    return settings


def create_habits_for_user_on_date(user, date):
    tracking_settings = get_habit_tracking_settings(user)
    if date < tracking_settings.start_date:
        return DailyHabit.objects.none()

    active_habit_names = list(
        Habit.objects.filter(user=user, active=True).values_list("name", flat=True)
    )
    if not active_habit_names:
        return DailyHabit.objects.none()

    habits = [
        DailyHabit(user=user, name=name, date=date)
        for name in active_habit_names
    ]
    DailyHabit.objects.bulk_create(habits, ignore_conflicts=True)
    return DailyHabit.objects.filter(user=user, date=date, name__in=active_habit_names)


def create_today_habits_for_user(user):
    return create_habits_for_user_on_date(user, timezone.localdate())


def habit_score_for_queryset(queryset):
    total = queryset.count()
    if total == 0:
        return 0
    completed = queryset.filter(completed=True).count()
    return round((completed / total) * 100)
