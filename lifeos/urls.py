from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("habits/", views.habits, name="habits"),
    path("habits/<int:pk>/toggle/", views.toggle_habit, name="toggle_habit"),
    path("habits/<int:pk>/remove/", views.remove_habit, name="remove_habit"),
    path("todos/", views.todos, name="todos"),
    path("todos/<int:pk>/toggle/", views.toggle_todo, name="toggle_todo"),
    path("todos/<int:pk>/delete/", views.delete_todo, name="delete_todo"),
    path("expenses/", views.expenses, name="expenses"),
    path("expenses/export.csv", views.export_expenses_csv, name="export_expenses_csv"),
    path("transactions/export.csv", views.export_transactions_csv, name="export_transactions_csv"),
    path("expenses/<int:pk>/delete/", views.delete_expense, name="delete_expense"),
    path(
        "money-accounts/<int:account_pk>/transactions.csv",
        views.export_transactions_csv,
        name="export_account_transactions_csv",
    ),
    path("money-accounts/<int:pk>/remove/", views.remove_money_account, name="remove_money_account"),
    path("credit-cards/", views.credit_cards, name="credit_cards"),
    path("credit-cards/<int:pk>/delete/", views.delete_credit_card, name="delete_credit_card"),
    path("subscriptions/", views.subscriptions, name="subscriptions"),
    path("subscriptions/<int:pk>/delete/", views.delete_subscription, name="delete_subscription"),
    path("study/", views.study_tracker, name="study_tracker"),
    path("study/<int:pk>/delete/", views.delete_study_session, name="delete_study_session"),
    path("reports/", views.reports, name="reports"),
]
