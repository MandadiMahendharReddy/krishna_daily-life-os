import csv
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.db.models import Sum
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    CreditCardForm,
    ExpenseForm,
    HabitForm,
    HabitImportForm,
    HabitTrackingSettingsForm,
    MoneyAccountForm,
    RegisterForm,
    StudySessionForm,
    SubscriptionForm,
    TodoForm,
)
from .models import (
    CreditCard,
    DailyHabit,
    Expense,
    Habit,
    MoneyAccount,
    StudySession,
    Subscription,
    TodoItem,
    create_today_habits_for_user,
    get_habit_tracking_settings,
    habit_score_for_queryset,
)


def sync_credit_cards_for_user(user):
    cards = CreditCard.objects.filter(user=user)
    for card in cards:
        card.sync_monthly_due_date()
    return cards


HABIT_NAME_HEADERS = {"habit", "habits", "habit_name", "habit name", "name"}
HABIT_START_HEADERS = {"start", "start_time", "start time", "from", "from_time", "from time"}
HABIT_END_HEADERS = {"end", "end_time", "end time", "to", "to_time", "to time"}


def normalized_csv_header(value):
    return " ".join(value.strip().lower().replace("_", " ").split())


def parse_habit_time(value):
    value = " ".join(value.strip().upper().replace(".", ":").split())
    if not value:
        return None

    for suffix in ("AM", "PM"):
        value = value.replace(f" {suffix}", suffix)
    for fmt in ("%I:%M%p", "%I%p", "%H:%M", "%H"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            pass
    return None


def habit_rows_from_uploaded_file(uploaded_file):
    raw_content = uploaded_file.read()
    try:
        text = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw_content.decode("latin-1")

    rows = []
    reader = csv.reader(text.splitlines())
    headers = None
    column_indexes = {"name": 0, "start_time": 1, "end_time": 2}

    for row in reader:
        if not any(cell.strip() for cell in row):
            continue

        if headers is None:
            possible_headers = [normalized_csv_header(cell) for cell in row]
            has_header = bool(
                set(possible_headers)
                & (HABIT_NAME_HEADERS | HABIT_START_HEADERS | HABIT_END_HEADERS)
            )
            if has_header:
                headers = possible_headers
                for index, header in enumerate(headers):
                    if header in HABIT_NAME_HEADERS:
                        column_indexes["name"] = index
                    elif header in HABIT_START_HEADERS:
                        column_indexes["start_time"] = index
                    elif header in HABIT_END_HEADERS:
                        column_indexes["end_time"] = index
                continue
            headers = []

        def cell_at(column_name):
            index = column_indexes[column_name]
            if index >= len(row):
                return ""
            return " ".join(row[index].split())

        name = cell_at("name")
        if not name:
            continue

        start_value = cell_at("start_time")
        end_value = cell_at("end_time")
        rows.append(
            {
                "name": name,
                "start_time": parse_habit_time(start_value) if start_value else None,
                "end_time": parse_habit_time(end_value) if end_value else None,
                "has_schedule": bool(start_value or end_value),
            }
        )
    return rows


def save_habit_for_user(user, name, start_time=None, end_time=None):
    habit, created = Habit.objects.get_or_create(
        user=user,
        name=name,
        defaults={
            "active": True,
            "start_time": start_time,
            "end_time": end_time,
        },
    )
    if not created:
        update_fields = []
        status = "skipped"
        if not habit.active:
            habit.active = True
            update_fields.append("active")
            status = "reactivated"
        if start_time is not None and habit.start_time != start_time:
            habit.start_time = start_time
            update_fields.append("start_time")
            status = "updated" if status == "skipped" else status
        if end_time is not None and habit.end_time != end_time:
            habit.end_time = end_time
            update_fields.append("end_time")
            status = "updated" if status == "skipped" else status
        if update_fields:
            update_fields.append("updated_at")
            habit.save(update_fields=update_fields)
        return status
    if created:
        return "created"
    return "skipped"


def save_money_account_for_user(user, form):
    account, created = MoneyAccount.objects.get_or_create(
        user=user,
        name=form.cleaned_data["name"],
        defaults={
            "account_type": form.cleaned_data["account_type"],
            "balance": form.cleaned_data["balance"],
            "active": True,
        },
    )
    if created:
        return "created"

    account.account_type = form.cleaned_data["account_type"]
    account.balance = form.cleaned_data["balance"]
    account.active = True
    account.save(update_fields=["account_type", "balance", "active", "updated_at"])
    return "updated"


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Account created. Your daily system is ready.")
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    today = timezone.localdate()
    today_habits = create_today_habits_for_user(request.user)
    habit_settings = get_habit_tracking_settings(request.user)
    habit_score = habit_score_for_queryset(today_habits)
    month_start = today.replace(day=1)
    credit_cards = sync_credit_cards_for_user(request.user)
    credit_card_alerts = credit_cards.order_by("due_date")
    subscription_alerts = Subscription.objects.filter(user=request.user, active=True).order_by("renewal_date")
    money_accounts = MoneyAccount.objects.filter(user=request.user, active=True)

    context = {
        "today_habits": today_habits,
        "habit_score": habit_score,
        "habit_start_date": habit_settings.start_date,
        "habits_tracking_started": today >= habit_settings.start_date,
        "total_money": money_accounts.aggregate(total=Sum("balance"))["total"] or 0,
        "open_todos": TodoItem.objects.filter(user=request.user, completed=False)[:5],
        "monthly_expense": Expense.objects.filter(
            user=request.user,
            spent_on__gte=month_start,
            spent_on__lte=today,
        ).aggregate(total=Sum("amount"))["total"] or 0,
        "study_minutes_today": StudySession.objects.filter(
            user=request.user,
            studied_on=today,
        ).aggregate(total=Sum("minutes"))["total"] or 0,
        "card_reminders": credit_cards.filter(due_date__gte=today, due_date__lte=today + timedelta(days=5)),
        "credit_card_alerts": credit_card_alerts,
        "subscription_reminders": subscription_alerts.filter(renewal_date__gte=today, renewal_date__lte=today + timedelta(days=5)),
        "subscription_alerts": subscription_alerts,
    }
    return render(request, "lifeos/dashboard.html", context)


@login_required
def profile(request):
    return render(request, "lifeos/profile.html")


@login_required
def habits(request):
    today = timezone.localdate()
    habit_settings = get_habit_tracking_settings(request.user)
    settings_form = HabitTrackingSettingsForm(instance=habit_settings)
    habit_form = HabitForm()
    import_form = HabitImportForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "settings":
            settings_form = HabitTrackingSettingsForm(request.POST, instance=habit_settings)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "Habit tracking start date saved.")
                return redirect("habits")
        elif action == "add_habit":
            habit_form = HabitForm(request.POST)
            if habit_form.is_valid():
                status = save_habit_for_user(
                    request.user,
                    habit_form.cleaned_data["name"],
                    habit_form.cleaned_data["start_time"],
                    habit_form.cleaned_data["end_time"],
                )
                if status == "skipped":
                    messages.info(request, "That habit is already in your list.")
                elif status == "updated":
                    messages.success(request, "Habit time updated.")
                else:
                    messages.success(request, "Habit saved.")
                return redirect("habits")
        elif action == "import_habits":
            import_form = HabitImportForm(request.POST, request.FILES)
            if import_form.is_valid():
                habit_rows = habit_rows_from_uploaded_file(import_form.cleaned_data["file"])
                created = 0
                reactivated = 0
                updated = 0
                skipped = 0
                invalid = 0
                seen = set()
                for row in habit_rows:
                    name = row["name"]
                    if len(name) > 120:
                        invalid += 1
                        continue
                    if row["has_schedule"] and (not row["start_time"] or not row["end_time"]):
                        invalid += 1
                        continue
                    if name in seen:
                        skipped += 1
                        continue
                    seen.add(name)
                    status = save_habit_for_user(
                        request.user,
                        name,
                        row["start_time"],
                        row["end_time"],
                    )
                    if status == "created":
                        created += 1
                    elif status == "reactivated":
                        reactivated += 1
                    elif status == "updated":
                        updated += 1
                    else:
                        skipped += 1
                changed = created + reactivated + updated
                if changed:
                    messages.success(request, f"Imported or updated {changed} habit(s).")
                else:
                    messages.info(request, "No new habits were imported.")
                if skipped or invalid:
                    messages.warning(request, f"Skipped {skipped + invalid} duplicate or invalid row(s).")
                return redirect("habits")

    today_habits = create_today_habits_for_user(request.user)
    active_habits = Habit.objects.filter(user=request.user, active=True).order_by(
        models.F("start_time").asc(nulls_last=True),
        "created_at",
        "name",
    )
    return render(
        request,
        "lifeos/habits.html",
        {
            "today_habits": today_habits,
            "habit_score": habit_score_for_queryset(today_habits),
            "active_habits": active_habits,
            "settings_form": settings_form,
            "habit_form": habit_form,
            "import_form": import_form,
            "habit_start_date": habit_settings.start_date,
            "habits_tracking_started": today >= habit_settings.start_date,
        },
    )


@login_required
@require_POST
def toggle_habit(request, pk):
    habit = get_object_or_404(DailyHabit, pk=pk, user=request.user)
    habit_settings = get_habit_tracking_settings(request.user)
    if habit.date < habit_settings.start_date:
        messages.warning(request, "That habit is before your tracking start date.")
        return redirect("habits")

    habit.completed = not habit.completed
    habit.save(update_fields=["completed", "updated_at"])
    return redirect("habits")


@login_required
@require_POST
def remove_habit(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    habit.active = False
    habit.save(update_fields=["active", "updated_at"])
    DailyHabit.objects.filter(
        user=request.user,
        name=habit.name,
        date=timezone.localdate(),
    ).delete()
    messages.success(request, "Habit removed.")
    return redirect("habits")


@login_required
def todos(request):
    form = TodoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        todo = form.save(commit=False)
        todo.user = request.user
        todo.save()
        messages.success(request, "To-do item added.")
        return redirect("todos")
    return render(
        request,
        "lifeos/todos.html",
        {"form": form, "items": TodoItem.objects.filter(user=request.user)},
    )


@login_required
@require_POST
def toggle_todo(request, pk):
    item = get_object_or_404(TodoItem, pk=pk, user=request.user)
    item.completed = not item.completed
    item.save(update_fields=["completed", "updated_at"])
    return redirect("todos")


@login_required
@require_POST
def delete_todo(request, pk):
    get_object_or_404(TodoItem, pk=pk, user=request.user).delete()
    return redirect("todos")


@login_required
def expenses(request):
    form = ExpenseForm(user=request.user)
    account_form = MoneyAccountForm()

    if request.method == "POST":
        action = request.POST.get("action", "add_expense")
        if action == "save_account":
            account_form = MoneyAccountForm(request.POST)
            if account_form.is_valid():
                status = save_money_account_for_user(request.user, account_form)
                if status == "created":
                    messages.success(request, "Money account added.")
                else:
                    messages.success(request, "Money account balance updated.")
                return redirect("expenses")
        else:
            form = ExpenseForm(request.POST, user=request.user)
            if form.is_valid():
                expense = form.save(commit=False)
                expense.user = request.user
                with transaction.atomic():
                    expense.save()
                    expense.account.balance -= expense.amount
                    expense.account.save(update_fields=["balance", "updated_at"])
                messages.success(request, "Expense saved and account balance updated.")
                return redirect("expenses")

    items = Expense.objects.filter(user=request.user)
    money_accounts = MoneyAccount.objects.filter(user=request.user, active=True)
    total = items.aggregate(total=Sum("amount"))["total"] or 0
    account_totals = {
        row["account_type"]: row["total"] or 0
        for row in money_accounts.values("account_type").annotate(total=Sum("balance"))
    }
    return render(
        request,
        "lifeos/expenses.html",
        {
            "form": form,
            "account_form": account_form,
            "items": items,
            "money_accounts": money_accounts,
            "total": total,
            "total_money": money_accounts.aggregate(total=Sum("balance"))["total"] or 0,
            "cash_balance": account_totals.get(MoneyAccount.ACCOUNT_CASH, 0),
            "bank_balance": account_totals.get(MoneyAccount.ACCOUNT_BANK, 0),
        },
    )


@login_required
@require_POST
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    with transaction.atomic():
        if expense.account is not None:
            expense.account.balance += expense.amount
            expense.account.save(update_fields=["balance", "updated_at"])
        expense.delete()
    messages.success(request, "Expense deleted and balance restored.")
    return redirect("expenses")


@login_required
@require_POST
def remove_money_account(request, pk):
    account = get_object_or_404(MoneyAccount, pk=pk, user=request.user)
    account.active = False
    account.save(update_fields=["active", "updated_at"])
    messages.success(request, "Money account removed.")
    return redirect("expenses")


@login_required
def credit_cards(request):
    sync_credit_cards_for_user(request.user)
    form = CreditCardForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        card = form.save(commit=False)
        card.user = request.user
        card.save()
        messages.success(request, "Credit card reminder saved.")
        return redirect("credit_cards")
    return render(
        request,
        "lifeos/credit_cards.html",
        {"form": form, "items": CreditCard.objects.filter(user=request.user).order_by("due_date")},
    )


@login_required
@require_POST
def delete_credit_card(request, pk):
    get_object_or_404(CreditCard, pk=pk, user=request.user).delete()
    return redirect("credit_cards")


@login_required
def subscriptions(request):
    form = SubscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        subscription = form.save(commit=False)
        subscription.user = request.user
        subscription.save()
        messages.success(request, "Subscription saved.")
        return redirect("subscriptions")
    return render(
        request,
        "lifeos/subscriptions.html",
        {"form": form, "items": Subscription.objects.filter(user=request.user)},
    )


@login_required
@require_POST
def delete_subscription(request, pk):
    get_object_or_404(Subscription, pk=pk, user=request.user).delete()
    return redirect("subscriptions")


@login_required
def study_tracker(request):
    form = StudySessionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        session = form.save(commit=False)
        session.user = request.user
        session.save()
        messages.success(request, "Study session saved.")
        return redirect("study_tracker")
    items = StudySession.objects.filter(user=request.user)
    total = items.aggregate(total=Sum("minutes"))["total"] or 0
    return render(request, "lifeos/study.html", {"form": form, "items": items, "total": total})


@login_required
@require_POST
def delete_study_session(request, pk):
    get_object_or_404(StudySession, pk=pk, user=request.user).delete()
    return redirect("study_tracker")


@login_required
def reports(request):
    today = timezone.localdate()
    sync_credit_cards_for_user(request.user)
    habit_settings = get_habit_tracking_settings(request.user)
    active_habit_names = list(
        Habit.objects.filter(user=request.user, active=True).values_list("name", flat=True)
    )
    habit_rows = []
    for days_ago in range(6, -1, -1):
        day = today - timedelta(days=days_ago)
        is_tracking = day >= habit_settings.start_date
        score = 0
        if is_tracking and active_habit_names:
            habits_for_day = DailyHabit.objects.filter(user=request.user, date=day, name__in=active_habit_names)
            score = habit_score_for_queryset(habits_for_day)
        habit_rows.append({"date": day, "score": score, "is_tracking": is_tracking})

    month_start = today.replace(day=1)
    monthly_expenses = Expense.objects.filter(
        user=request.user,
        spent_on__gte=month_start,
        spent_on__lte=today,
    )
    study_rows = (
        StudySession.objects.filter(user=request.user, studied_on__gte=today - timedelta(days=30))
        .values("subject")
        .annotate(total=Sum("minutes"))
        .order_by("subject")
    )
    return render(
        request,
        "lifeos/reports.html",
        {
            "habit_rows": habit_rows,
            "habit_start_date": habit_settings.start_date,
            "monthly_expense": monthly_expenses.aggregate(total=Sum("amount"))["total"] or 0,
            "study_rows": study_rows,
            "study_total": StudySession.objects.filter(
                user=request.user,
                studied_on__gte=today - timedelta(days=30),
            ).aggregate(total=Sum("minutes"))["total"] or 0,
        },
    )
