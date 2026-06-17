from django.contrib import admin

from .models import CreditCard, DailyHabit, Expense, Habit, HabitTrackingSettings, MoneyAccount, StudySession, Subscription, TodoItem


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "active")
    list_filter = ("active",)
    search_fields = ("name", "user__username")


@admin.register(DailyHabit)
class DailyHabitAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "date", "completed")
    list_filter = ("completed", "date")
    search_fields = ("name", "user__username")


@admin.register(HabitTrackingSettings)
class HabitTrackingSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "start_date")
    search_fields = ("user__username",)


@admin.register(MoneyAccount)
class MoneyAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "account_type", "balance", "active")
    list_filter = ("account_type", "active")
    search_fields = ("name", "user__username")


@admin.register(TodoItem)
class TodoItemAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "priority", "due_date", "completed")
    list_filter = ("priority", "completed", "due_date")
    search_fields = ("title", "user__username")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "account", "amount", "spent_on")
    list_filter = ("category", "account", "spent_on")
    search_fields = ("title", "user__username")


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ("name", "bank_name", "user", "due_date", "reminder_date", "is_reminder_active")
    list_filter = ("due_date", "bank_name")
    search_fields = ("name", "bank_name", "user__username")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "amount", "renewal_date", "billing_cycle", "active")
    list_filter = ("active", "billing_cycle", "renewal_date")
    search_fields = ("name", "user__username")


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "subject", "minutes", "studied_on")
    list_filter = ("subject", "studied_on")
    search_fields = ("title", "user__username")
