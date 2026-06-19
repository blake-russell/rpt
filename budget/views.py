from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import CSVImportForm, ExclusionRuleForm, ExpenseCategoryForm, TransactionEditForm
from .importers import _match_exclusion_rule, import_bank_csv
from .models import ExclusionRule, ExpenseCategory, ImportLog, MerchantMapping, Transaction
from .utils import monthly_cashflow_summary


def _normalize_month_options():
    values = (
        Transaction.objects.values_list("date__year", "date__month")
        .distinct()
        .order_by("-date__year", "-date__month")
    )
    return [f"{year:04d}-{month:02d}" for year, month in values]


def _build_chart_data(transactions):
    grouped = (
        transactions.filter(amount__lt=0)
        .values("category__name", "category__color_hex")
        .annotate(total=Sum("amount"))
        .order_by("category__name")
    )
    labels, values, colors = [], [], []
    for row in grouped:
        labels.append(row["category__name"] or "Uncategorized")
        values.append(float(abs(row["total"] or Decimal("0"))))
        colors.append(row["category__color_hex"] or "#6c757d")
    return labels, values, colors


def _six_months_ago():
    from datetime import date

    today = date.today()
    m = today.month - 6
    y = today.year
    if m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


@login_required
def budget_dashboard(request):
    month = request.GET.get("month", "")
    category_id = request.GET.get("category", "")
    include_excluded = request.GET.get("include_excluded") == "1"
    page_number = request.GET.get("page", 1)

    base_qs = Transaction.objects.select_related("category")
    if not include_excluded:
        base_qs = base_qs.filter(is_excluded=False)

    # Headline stats always reflect all available months in the current include/excluded mode.
    headline = monthly_cashflow_summary(base_qs)
    non_debt_headline = monthly_cashflow_summary(base_qs, exclude_debt_service=True)

    # Table/chart can be filtered by month/category.
    transactions = base_qs
    if month:
        try:
            year, month_num = month.split("-")
            transactions = transactions.filter(date__year=int(year), date__month=int(month_num))
        except ValueError:
            messages.warning(request, "Invalid month filter ignored.")
    if category_id:
        transactions = transactions.filter(category_id=category_id)

    filtered_income = transactions.filter(amount__gt=0).aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0")
    filtered_expense_total_raw = transactions.filter(amount__lt=0).aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0")
    filtered_expenses = abs(filtered_expense_total_raw)
    filtered_net = filtered_income - filtered_expenses

    categories = ExpenseCategory.objects.all()
    month_options = _normalize_month_options()
    chart_labels, chart_values, chart_colors = _build_chart_data(transactions)

    total_transactions = base_qs.count()
    uncategorized_count = base_qs.filter(category__isnull=True).count()
    checking_count = base_qs.filter(source="checking").count()
    credit_count = base_qs.filter(source="credit").count()
    pending_duplicates = (
        Transaction.objects.filter(is_pending_duplicate=True)
        .select_related("category")
        .order_by("-date")
    )
    pending_duplicates_count = pending_duplicates.count()
    recent_import_logs = ImportLog.objects.all()[:5]

    mapped_descriptions = MerchantMapping.objects.values_list("raw_description", flat=True)
    unmatched_base = base_qs.filter(category__isnull=True)
    unmatched_descriptions = (
        unmatched_base.exclude(raw_description__in=mapped_descriptions)
        .values_list("raw_description", flat=True)
        .distinct()
        .order_by("raw_description")
    )

    # Prune table display to last 6 months; headline stats use full history.
    cutoff = _six_months_ago()
    table_qs = transactions.filter(date__gte=cutoff)
    page_obj = Paginator(table_qs, 100).get_page(page_number)

    # Build base querystring for pagination links (preserves active filters).
    qp = request.GET.copy()
    qp.pop("page", None)
    pagination_base = (qp.urlencode() + "&") if qp.urlencode() else ""

    return render(
        request,
        "budget/dashboard.html",
        {
            "import_form": CSVImportForm(),
            "page_obj": page_obj,
            "pagination_base": pagination_base,
            "table_cutoff": cutoff,
            "categories": categories,
            "month_options": month_options,
            "selected_month": month,
            "selected_category": category_id,
            "include_excluded": include_excluded,
            "filtered_income": filtered_income,
            "filtered_expenses": filtered_expenses,
            "filtered_net": filtered_net,
            "chart_labels": chart_labels,
            "chart_values": chart_values,
            "chart_colors": chart_colors,
            "total_transactions": total_transactions,
            "uncategorized_count": uncategorized_count,
            "checking_count": checking_count,
            "credit_count": credit_count,
            "pending_duplicates": pending_duplicates,
            "pending_duplicates_count": pending_duplicates_count,
            "recent_import_logs": recent_import_logs,
            "unmatched_descriptions": unmatched_descriptions,
            **headline,
            "rolling_avg_non_debt_expenses": non_debt_headline["rolling_avg_expenses"],
        },
    )


@login_required
@require_POST
def transaction_exclude(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    note = (request.POST.get("note") or "").strip()
    tx.is_excluded = True
    tx.exclusion_note = note or "Excluded from budget math"
    tx.save(update_fields=["is_excluded", "exclusion_note"])
    messages.success(request, "Transaction excluded from budget calculations.")
    return redirect("budget_dashboard")


@login_required
@require_POST
def transaction_include(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    tx.is_excluded = False
    tx.exclusion_note = ""
    tx.save(update_fields=["is_excluded", "exclusion_note"])
    messages.success(request, "Transaction included in budget calculations.")
    return redirect("budget_dashboard")


@login_required
@require_POST
def transactions_bulk_action(request):
    action = (request.POST.get("action") or "").strip()
    note = (request.POST.get("note") or "").strip()
    category_id = (request.POST.get("category_id") or "").strip()
    transaction_ids = request.POST.getlist("transaction_ids")

    if not transaction_ids:
        messages.warning(request, "No transactions selected for bulk action.")
        return redirect("budget_dashboard")

    queryset = Transaction.objects.filter(pk__in=transaction_ids)

    if action == "exclude":
        updated = queryset.update(
            is_excluded=True,
            exclusion_note=note or "Excluded from budget math",
        )
        messages.success(request, f"Excluded {updated} transaction(s).")
    elif action == "include":
        updated = queryset.update(is_excluded=False, exclusion_note="")
        messages.success(request, f"Included {updated} transaction(s).")
    elif action == "set_category":
        if not category_id:
            messages.error(request, "Choose a category for bulk category assignment.")
            return redirect("budget_dashboard")
        category = ExpenseCategory.objects.filter(pk=category_id).first()
        if not category:
            messages.error(request, "Selected category was not found.")
            return redirect("budget_dashboard")
        updated = queryset.update(category=category)
        messages.success(
            request, f'Assigned category "{category.name}" to {updated} transaction(s).'
        )
    elif action == "clear_category":
        updated = queryset.update(category=None)
        messages.success(request, f"Cleared category on {updated} transaction(s).")
    else:
        messages.error(request, "Invalid bulk action requested.")

    return redirect("budget_dashboard")


@login_required
def import_csv(request):
    if request.method != "POST":
        return redirect("budget_dashboard")

    form = CSVImportForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Please choose source and CSV file.")
        return redirect("budget_dashboard")

    csv_file = form.cleaned_data["csv_file"]
    source = form.cleaned_data["source"]
    bank = form.cleaned_data["bank"]
    try:
        imported, skipped, staged, unmatched, skip_details = import_bank_csv(csv_file, source, bank)
    except Exception as exc:
        messages.error(request, f"Import failed: {exc}")
        return redirect("budget_dashboard")

    import json

    ImportLog.objects.create(
        bank=bank,
        source=source,
        imported_count=imported,
        skipped_count=skipped,
        staged_count=staged,
        skip_details_json=json.dumps(skip_details),
    )

    msg = f"CSV imported. Added {imported}, skipped {skipped}."
    if staged:
        msg += f" {staged} potential duplicate(s) staged for review."
    messages.success(request, msg)
    if unmatched:
        messages.info(request, f"{len(unmatched)} unmatched descriptions need mapping below.")
    return redirect("budget_dashboard")


@login_required
def save_mapping(request):
    if request.method != "POST":
        return redirect("budget_dashboard")

    raw_description = (request.POST.get("raw_description") or "").strip()
    friendly_name = (request.POST.get("friendly_name") or "").strip()
    category_id = request.POST.get("category")

    if not raw_description or not friendly_name:
        messages.error(request, "Raw description and friendly name are required.")
        return redirect("budget_dashboard")

    category = ExpenseCategory.objects.filter(pk=category_id).first() if category_id else None
    mapping, _ = MerchantMapping.objects.update_or_create(
        raw_description=raw_description,
        defaults={"friendly_name": friendly_name, "category": category},
    )
    Transaction.objects.filter(raw_description=raw_description).update(
        friendly_name=mapping.friendly_name,
        category=mapping.category,
    )
    messages.success(request, f'Mapping saved for "{raw_description}".')
    return redirect("budget_dashboard")


@login_required
def bulk_save_mappings(request):
    if request.method != "POST":
        return redirect("budget_dashboard")

    raw_descriptions = request.POST.getlist("raw_descriptions")
    category_id = request.POST.get("category")

    if not raw_descriptions:
        messages.warning(request, "No descriptions selected.")
        return redirect("budget_dashboard")

    category = ExpenseCategory.objects.filter(pk=category_id).first() if category_id else None
    saved = 0
    for raw in raw_descriptions:
        raw = raw.strip()
        if not raw:
            continue
        mapping, _ = MerchantMapping.objects.update_or_create(
            raw_description=raw,
            defaults={"friendly_name": raw[:200], "category": category},
        )
        Transaction.objects.filter(raw_description=raw).update(
            friendly_name=mapping.friendly_name,
            category=mapping.category,
        )
        saved += 1

    messages.success(request, f"Saved {saved} merchant mapping(s).")
    return redirect("budget_dashboard")


@login_required
def categories_manage(request):
    form = ExpenseCategoryForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Category created.")
        return redirect("budget_categories")
    categories = ExpenseCategory.objects.all()
    return render(request, "budget/categories.html", {"form": form, "categories": categories})


@login_required
def category_edit(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk)
    form = ExpenseCategoryForm(request.POST or None, instance=category)
    if form.is_valid():
        form.save()
        messages.success(request, "Category updated.")
        return redirect("budget_categories")
    return render(request, "budget/category_form.html", {"form": form, "title": "Edit Category"})


@login_required
def category_delete(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk)
    if request.method == "POST":
        category.delete()
        messages.success(request, "Category removed.")
        return redirect("budget_categories")
    return render(
        request,
        "budget/confirm_delete.html",
        {
            "obj": category,
            "cancel_url": reverse("budget_categories"),
        },
    )


@login_required
def exclusion_rules_manage(request):
    form = ExclusionRuleForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Exclusion rule saved.")
        return redirect("budget_exclusion_rules")
    rules = ExclusionRule.objects.all()
    return render(request, "budget/exclusion_rules.html", {"form": form, "rules": rules})


@login_required
def exclusion_rule_edit(request, pk):
    rule = get_object_or_404(ExclusionRule, pk=pk)
    form = ExclusionRuleForm(request.POST or None, instance=rule)
    if form.is_valid():
        form.save()
        messages.success(request, "Exclusion rule updated.")
        return redirect("budget_exclusion_rules")
    rules = ExclusionRule.objects.all()
    return render(
        request, "budget/exclusion_rules.html", {"form": form, "rules": rules, "editing": rule}
    )


@login_required
@require_POST
def exclusion_rule_delete(request, pk):
    rule = get_object_or_404(ExclusionRule, pk=pk)
    rule.delete()
    messages.success(request, "Exclusion rule removed.")
    return redirect("budget_exclusion_rules")


@login_required
@require_POST
def apply_exclusion_rules(request):
    updated = 0
    for tx in Transaction.objects.filter(is_excluded=False):
        rule = _match_exclusion_rule(tx.raw_description, tx.source, amount=tx.amount)
        if rule:
            tx.is_excluded = True
            tx.exclusion_note = rule.note
            tx.save(update_fields=["is_excluded", "exclusion_note"])
            updated += 1
    messages.success(request, f"Applied exclusion rules to {updated} existing transaction(s).")
    return redirect("budget_exclusion_rules")


@login_required
def transaction_edit(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    form = TransactionEditForm(request.POST or None, instance=tx)
    if form.is_valid():
        form.save()
        messages.success(request, "Transaction updated.")
        return redirect("budget_dashboard")
    return render(request, "budget/transaction_form.html", {"form": form, "tx": tx})


@login_required
@require_POST
def transaction_delete(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    tx.delete()
    messages.success(request, "Transaction deleted.")
    return redirect("budget_dashboard")


@login_required
@require_POST
def duplicates_bulk_action(request):
    action = (request.POST.get("action") or "").strip()
    pks = request.POST.getlist("duplicate_ids")

    if not pks:
        messages.warning(request, "No duplicates selected.")
        return redirect("budget_dashboard")

    qs = Transaction.objects.filter(pk__in=pks, is_pending_duplicate=True)

    if action == "approve":
        updated = qs.update(is_pending_duplicate=False, is_excluded=False, exclusion_note="")
        messages.success(request, f"Approved {updated} duplicate(s) and added to budget.")
    elif action == "deny":
        updated = qs.update(
            is_pending_duplicate=False,
            is_excluded=True,
            exclusion_note="Duplicate denied — excluded from budget",
        )
        messages.success(request, f"Denied {updated} duplicate(s).")
    else:
        messages.error(request, "Invalid bulk duplicate action.")

    return redirect("budget_dashboard")


@login_required
@require_POST
def duplicate_approve(request, pk):
    """Accept a staged potential duplicate — include it in budget calculations."""
    tx = get_object_or_404(Transaction, pk=pk, is_pending_duplicate=True)
    tx.is_pending_duplicate = False
    tx.is_excluded = False
    tx.exclusion_note = ""
    tx.save(update_fields=["is_pending_duplicate", "is_excluded", "exclusion_note"])
    messages.success(request, "Duplicate approved and added to budget.")
    return redirect("budget_dashboard")


@login_required
@require_POST
def duplicate_deny(request, pk):
    """Reject a staged potential duplicate — keep it excluded from budget calculations."""
    tx = get_object_or_404(Transaction, pk=pk, is_pending_duplicate=True)
    tx.is_pending_duplicate = False
    tx.is_excluded = True
    tx.exclusion_note = "Duplicate denied — excluded from budget"
    tx.save(update_fields=["is_pending_duplicate", "is_excluded", "exclusion_note"])
    messages.success(request, "Duplicate denied and excluded from budget.")
    return redirect("budget_dashboard")
