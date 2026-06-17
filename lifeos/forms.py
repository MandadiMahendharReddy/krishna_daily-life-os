from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import CreditCard, Expense, Habit, HabitTrackingSettings, MoneyAccount, StudySession, Subscription, TodoItem


class DateInput(forms.DateInput):
    input_type = "date"


class TimeInput(forms.TimeInput):
    input_type = "time"


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget_class = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"
            field.widget.attrs.setdefault("class", widget_class)


class HabitTrackingSettingsForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = HabitTrackingSettings
        fields = ["start_date"]
        widgets = {"start_date": DateInput()}
        labels = {"start_date": "Habit tracking start date"}


class HabitForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Habit
        fields = ["name", "start_time", "end_time"]
        widgets = {"start_time": TimeInput(), "end_time": TimeInput()}
        labels = {
            "name": "Habit name",
            "start_time": "Start time",
            "end_time": "End time",
        }

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if not start_time:
            self.add_error("start_time", "Start time is required.")
        if not end_time:
            self.add_error("end_time", "End time is required.")
        return cleaned_data


class HabitImportForm(BootstrapFormMixin, forms.Form):
    file = forms.FileField(
        label="Import habits CSV",
        help_text="Use columns: Habit Name, Start Time, End Time. Example: Wake,3:55 AM,3:56 AM",
    )


class MoneyAccountForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MoneyAccount
        fields = ["name", "account_type", "balance"]
        labels = {"balance": "Current balance"}

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())

    def clean(self):
        cleaned_data = super().clean()
        account_type = cleaned_data.get("account_type")
        balance = cleaned_data.get("balance")
        if (
            account_type != MoneyAccount.ACCOUNT_CREDIT_CARD
            and balance is not None
            and balance < 0
        ):
            self.add_error("balance", "Cash and bank balances cannot be negative.")
        return cleaned_data


class AccountCreditForm(BootstrapFormMixin, forms.Form):
    CREDIT_TYPE_CHOICES = [
        ("Salary", "Salary"),
        ("Interest from Bank", "Interest from Bank"),
        ("Refund from Income Tax", "Refund from Income Tax"),
        ("Business Income", "Business Income"),
        ("Freelance Income", "Freelance Income"),
        ("Bonus", "Bonus"),
        ("Reimbursement", "Reimbursement"),
        ("Cash Deposit", "Cash Deposit"),
        ("Gift", "Gift"),
        ("Dividend", "Dividend"),
        ("Rent Received", "Rent Received"),
        ("Loan Received", "Loan Received"),
        ("Other Credit", "Other Credit"),
    ]

    title = forms.ChoiceField(choices=CREDIT_TYPE_CHOICES, label="Credit type", initial="Salary")
    to_account = forms.ModelChoiceField(queryset=MoneyAccount.objects.none(), label="Credit to")
    amount = forms.DecimalField(max_digits=12, decimal_places=2)
    occurred_on = forms.DateField(widget=DateInput(), initial=timezone.localdate, label="Date")
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["to_account"].queryset = MoneyAccount.objects.filter(
                user=user,
                active=True,
            ).exclude(account_type=MoneyAccount.ACCOUNT_CREDIT_CARD)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount


class AccountTransferForm(BootstrapFormMixin, forms.Form):
    title = forms.CharField(max_length=180, initial="Transfer")
    from_account = forms.ModelChoiceField(queryset=MoneyAccount.objects.none(), label="From account")
    to_account = forms.ModelChoiceField(queryset=MoneyAccount.objects.none(), label="To account")
    amount = forms.DecimalField(max_digits=12, decimal_places=2)
    occurred_on = forms.DateField(widget=DateInput(), initial=timezone.localdate, label="Date")
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            accounts = MoneyAccount.objects.filter(user=user, active=True).exclude(
                account_type=MoneyAccount.ACCOUNT_CREDIT_CARD
            )
            self.fields["from_account"].queryset = accounts
            self.fields["to_account"].queryset = accounts

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get("from_account")
        to_account = cleaned_data.get("to_account")
        amount = cleaned_data.get("amount")
        if from_account is not None and to_account is not None and from_account == to_account:
            self.add_error("to_account", "Choose a different account.")
        if from_account is not None and amount is not None and amount > from_account.balance:
            self.add_error("amount", "Amount is more than the selected account balance.")
        return cleaned_data


class CreditCardPaymentForm(BootstrapFormMixin, forms.Form):
    credit_card = forms.ModelChoiceField(
        queryset=MoneyAccount.objects.none(),
        label="Credit card",
    )
    pay_from_account = forms.ModelChoiceField(
        queryset=MoneyAccount.objects.none(),
        label="Pay from account",
    )
    amount = forms.DecimalField(max_digits=12, decimal_places=2)
    occurred_on = forms.DateField(widget=DateInput(), initial=timezone.localdate, label="Date")
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            active_accounts = MoneyAccount.objects.filter(user=user, active=True)
            self.fields["credit_card"].queryset = active_accounts.filter(
                account_type=MoneyAccount.ACCOUNT_CREDIT_CARD
            )
            self.fields["pay_from_account"].queryset = active_accounts.exclude(
                account_type=MoneyAccount.ACCOUNT_CREDIT_CARD
            )

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        credit_card = cleaned_data.get("credit_card")
        pay_from_account = cleaned_data.get("pay_from_account")
        amount = cleaned_data.get("amount")

        if credit_card is not None and credit_card.account_type != MoneyAccount.ACCOUNT_CREDIT_CARD:
            self.add_error("credit_card", "Choose a credit card account.")
        if (
            pay_from_account is not None
            and pay_from_account.account_type == MoneyAccount.ACCOUNT_CREDIT_CARD
        ):
            self.add_error("pay_from_account", "Payment must come from cash or a bank account.")
        if pay_from_account is not None and amount is not None and amount > pay_from_account.balance:
            self.add_error("amount", "Amount is more than the selected account balance.")
        return cleaned_data


class TodoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TodoItem
        fields = ["title", "description", "due_date", "priority", "completed"]
        widgets = {"due_date": DateInput()}


class ExpenseForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = MoneyAccount.objects.none()
        if user is not None:
            queryset = MoneyAccount.objects.filter(user=user, active=True)
        self.fields["account"].queryset = queryset
        self.fields["account"].empty_label = "Choose an account"
        self.fields["account"].required = True

    class Meta:
        model = Expense
        fields = ["title", "category", "amount", "account", "spent_on", "notes"]
        widgets = {"spent_on": DateInput()}
        labels = {"account": "Paid from"}

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        account = cleaned_data.get("account")
        amount = cleaned_data.get("amount")
        if (
            account is not None
            and account.account_type != MoneyAccount.ACCOUNT_CREDIT_CARD
            and amount is not None
            and amount > account.balance
        ):
            self.add_error("amount", "Amount is more than the selected account balance.")
        return cleaned_data


class CreditCardForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CreditCard
        fields = ["name", "bank_name", "due_date"]
        widgets = {"due_date": DateInput()}
        labels = {"name": "Card type", "bank_name": "Bank", "due_date": "Monthly due date"}


class SubscriptionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ["name", "amount", "renewal_date", "billing_cycle", "active", "notes"]
        widgets = {"renewal_date": DateInput()}


class StudySessionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = StudySession
        fields = ["subject", "title", "minutes", "studied_on", "notes"]
        widgets = {"studied_on": DateInput()}
