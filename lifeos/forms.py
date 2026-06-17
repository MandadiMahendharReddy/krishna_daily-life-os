from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import CreditCard, Expense, Habit, HabitTrackingSettings, MoneyAccount, StudySession, Subscription, TodoItem


class DateInput(forms.DateInput):
    input_type = "date"


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
        fields = ["name"]
        labels = {"name": "Habit name"}

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())


class HabitImportForm(BootstrapFormMixin, forms.Form):
    file = forms.FileField(label="Import habits file")


class MoneyAccountForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MoneyAccount
        fields = ["name", "account_type", "balance"]
        labels = {"balance": "Current balance"}

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())

    def clean_balance(self):
        balance = self.cleaned_data["balance"]
        if balance < 0:
            raise forms.ValidationError("Balance cannot be negative.")
        return balance


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
        self.fields["account"].empty_label = "Choose cash/bank account"
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
        if account is not None and amount is not None and amount > account.balance:
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
