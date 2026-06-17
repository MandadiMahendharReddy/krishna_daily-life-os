from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from .models import AccountTransaction, Habit, MoneyAccount, create_today_habits_for_user
from .views import habit_rows_from_uploaded_file, parse_habit_time


def uploaded_csv(text):
    return SimpleUploadedFile("habits.csv", text.encode("utf-8"), content_type="text/csv")


class BootstrapSuperuserTests(TestCase):
    @patch.dict(
        "os.environ",
        {
            "DJANGO_SUPERUSER_USERNAME": "site-admin",
            "DJANGO_SUPERUSER_PASSWORD": "secure-admin-pass",
            "DJANGO_SUPERUSER_EMAIL": "admin@example.com",
        },
    )
    def test_creates_superuser_from_environment(self):
        call_command("bootstrap_superuser")

        user = get_user_model().objects.get(username="site-admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("secure-admin-pass"))

    @patch.dict("os.environ", {}, clear=True)
    def test_skips_when_credentials_are_not_configured(self):
        call_command("bootstrap_superuser")

        self.assertEqual(get_user_model().objects.count(), 0)


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

    def test_today_habits_follow_start_time_before_created_order(self):
        user = get_user_model().objects.create_user(username="radha", password="secret-pass")
        wake = Habit.objects.create(
            user=user,
            name="Wake",
            start_time=time(3, 55),
            end_time=time(3, 56),
        )
        bath = Habit.objects.create(
            user=user,
            name="Bath",
            start_time=time(3, 56),
            end_time=time(4, 0),
        )

        base_time = timezone.now()
        Habit.objects.filter(pk=wake.pk).update(created_at=base_time + timedelta(minutes=5))
        Habit.objects.filter(pk=bath.pk).update(created_at=base_time)

        today_habits = create_today_habits_for_user(user)

        self.assertEqual(
            list(today_habits.values_list("name", "habit_start_time", "habit_end_time")),
            [
                ("Wake", time(3, 55), time(3, 56)),
                ("Bath", time(3, 56), time(4, 0)),
            ],
        )


class HabitCsvImportTests(TestCase):
    def test_csv_import_reads_name_start_time_and_end_time(self):
        rows = habit_rows_from_uploaded_file(
            uploaded_csv(
                "Habit Name,Start Time,End Time\n"
                "Wake,3:55 AM,3:56 AM\n"
                "Bath,03:56,04:00\n"
            )
        )

        self.assertEqual(
            rows,
            [
                {
                    "name": "Wake",
                    "start_time": time(3, 55),
                    "end_time": time(3, 56),
                    "has_schedule": True,
                },
                {
                    "name": "Bath",
                    "start_time": time(3, 56),
                    "end_time": time(4, 0),
                    "has_schedule": True,
                },
            ],
        )

    def test_csv_import_keeps_support_for_one_column_habit_files(self):
        rows = habit_rows_from_uploaded_file(uploaded_csv("Wake\nBath\n"))

        self.assertEqual(
            rows,
            [
                {"name": "Wake", "start_time": None, "end_time": None, "has_schedule": False},
                {"name": "Bath", "start_time": None, "end_time": None, "has_schedule": False},
            ],
        )

    def test_parse_habit_time_accepts_common_formats(self):
        self.assertEqual(parse_habit_time("3:55 AM"), time(3, 55))
        self.assertEqual(parse_habit_time("3.55 am"), time(3, 55))
        self.assertEqual(parse_habit_time("15:30"), time(15, 30))
        self.assertIsNone(parse_habit_time("bad time"))


class MoneyLedgerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ledger", password="secret-pass")
        self.client.force_login(self.user)
        self.cash = MoneyAccount.objects.create(
            user=self.user,
            name="Cash",
            account_type=MoneyAccount.ACCOUNT_CASH,
            balance=Decimal("100.00"),
        )
        self.bank = MoneyAccount.objects.create(
            user=self.user,
            name="Bank1",
            account_type=MoneyAccount.ACCOUNT_BANK,
            balance=Decimal("1000.00"),
        )

    def test_expense_debits_selected_account_and_creates_transaction(self):
        response = self.client.post(
            "/expenses/",
            {
                "action": "add_expense",
                "title": "Food",
                "category": "food",
                "amount": "50.00",
                "account": self.bank.pk,
                "spent_on": timezone.localdate(),
                "notes": "",
            },
        )

        self.assertRedirects(response, "/expenses/")
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal("950.00"))
        self.assertEqual(AccountTransaction.objects.count(), 1)
        transaction = AccountTransaction.objects.get()
        self.assertEqual(transaction.transaction_type, AccountTransaction.TYPE_EXPENSE)
        self.assertEqual(transaction.from_account, self.bank)
        self.assertEqual(transaction.amount, Decimal("50.00"))

    def test_credit_adds_to_selected_account_and_creates_transaction(self):
        response = self.client.post(
            "/expenses/",
            {
                "action": "credit_account",
                "title": "Salary",
                "to_account": self.bank.pk,
                "amount": "500.00",
                "occurred_on": timezone.localdate(),
                "notes": "",
            },
        )

        self.assertRedirects(response, "/expenses/")
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal("1500.00"))
        transaction = AccountTransaction.objects.get(transaction_type=AccountTransaction.TYPE_CREDIT)
        self.assertEqual(transaction.to_account, self.bank)
        self.assertEqual(transaction.title, "Salary")
        self.assertEqual(transaction.amount, Decimal("500.00"))

    def test_transfer_moves_money_between_accounts_and_creates_transaction(self):
        response = self.client.post(
            "/expenses/",
            {
                "action": "transfer_account",
                "title": "ATM withdrawal",
                "from_account": self.bank.pk,
                "to_account": self.cash.pk,
                "amount": "200.00",
                "occurred_on": timezone.localdate(),
                "notes": "",
            },
        )

        self.assertRedirects(response, "/expenses/")
        self.bank.refresh_from_db()
        self.cash.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal("800.00"))
        self.assertEqual(self.cash.balance, Decimal("300.00"))
        transaction = AccountTransaction.objects.get(transaction_type=AccountTransaction.TYPE_TRANSFER)
        self.assertEqual(transaction.from_account, self.bank)
        self.assertEqual(transaction.to_account, self.cash)

    def test_transaction_csv_can_be_downloaded_for_single_account(self):
        AccountTransaction.objects.create(
            user=self.user,
            transaction_type=AccountTransaction.TYPE_CREDIT,
            title="Opening",
            amount=Decimal("100.00"),
            to_account=self.cash,
        )

        response = self.client.get(f"/money-accounts/{self.cash.pk}/transactions.csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("Opening", response.content.decode())
        self.assertIn("Credit", response.content.decode())

    def test_expenses_page_renders_account_ledger_controls(self):
        response = self.client.get("/expenses/")

        self.assertContains(response, "Credit Account")
        self.assertContains(response, "Interest from Bank")
        self.assertContains(response, "Refund from Income Tax")
        self.assertContains(response, "Transfer / Withdraw")
        self.assertContains(response, "Download Transactions")

    def test_expenses_page_bank_total_sums_all_bank_accounts(self):
        MoneyAccount.objects.create(
            user=self.user,
            name="Bank2",
            account_type=MoneyAccount.ACCOUNT_BANK,
            balance=Decimal("2000.00"),
        )
        MoneyAccount.objects.create(
            user=self.user,
            name="Bank3",
            account_type=MoneyAccount.ACCOUNT_BANK,
            balance=Decimal("3000.00"),
        )

        response = self.client.get("/expenses/")

        self.assertContains(response, "Bank Total")
        self.assertContains(response, "₹6000.00")
        self.assertContains(response, "₹6100.00")
