from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AccountForm, HoldingForm, MonthlyContributionForm
from .models import Account, Holding, MonthlyContribution


def _portfolio_summary(accounts):
    total_value = None
    total_basis = 0
    total_monthly = 0
    for acct in accounts:
        v = acct.total_value
        if v is not None:
            total_value = (total_value or 0) + v
        total_basis += acct.total_cost_basis
        total_monthly += acct.monthly_contribution_total
    gain_loss = (total_value - total_basis) if total_value is not None else None
    return {
        "total_value": total_value,
        "total_basis": total_basis,
        "total_monthly": total_monthly,
        "gain_loss": gain_loss,
    }


@login_required
def assets_dashboard(request):
    accounts = Account.objects.prefetch_related("holdings__contributions").all()
    summary = _portfolio_summary(accounts)
    return render(
        request,
        "assets/dashboard.html",
        {
            "accounts": accounts,
            **summary,
        },
    )


# ── Account ───────────────────────────────────────────────────────────────────


@login_required
def account_add(request):
    form = AccountForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Account added.")
        return redirect("assets_dashboard")
    return render(request, "assets/account_form.html", {"form": form, "title": "Add Account"})


@login_required
def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk)
    form = AccountForm(request.POST or None, instance=account)
    if form.is_valid():
        form.save()
        messages.success(request, "Account updated.")
        return redirect("assets_dashboard")
    return render(request, "assets/account_form.html", {"form": form, "title": "Edit Account"})


@login_required
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == "POST":
        account.delete()
        messages.success(request, "Account removed.")
        return redirect("assets_dashboard")
    return render(
        request,
        "assets/confirm_delete.html",
        {
            "obj": account,
            "cancel_url": reverse("assets_dashboard"),
        },
    )


# ── Holding ───────────────────────────────────────────────────────────────────


@login_required
def holding_add(request, account_pk):
    account = get_object_or_404(Account, pk=account_pk)
    form = HoldingForm(request.POST or None, account=account)
    if form.is_valid():
        form.save()
        messages.success(request, f"{form.cleaned_data['ticker']} added.")
        return redirect("assets_dashboard")
    return render(
        request,
        "assets/holding_form.html",
        {
            "form": form,
            "account": account,
            "title": f"Add Holding — {account.name}",
        },
    )


@login_required
def holding_edit(request, pk):
    holding = get_object_or_404(Holding, pk=pk)
    form = HoldingForm(request.POST or None, instance=holding)
    if form.is_valid():
        form.save()
        messages.success(request, "Holding updated.")
        return redirect("assets_dashboard")
    return render(
        request,
        "assets/holding_form.html",
        {
            "form": form,
            "account": holding.account,
            "title": f"Edit {holding.ticker}",
        },
    )


@login_required
def holding_delete(request, pk):
    holding = get_object_or_404(Holding, pk=pk)
    if request.method == "POST":
        holding.delete()
        messages.success(request, "Holding removed.")
        return redirect("assets_dashboard")
    return render(
        request,
        "assets/confirm_delete.html",
        {
            "obj": holding,
            "cancel_url": reverse("assets_dashboard"),
        },
    )


# ── Monthly Contribution ──────────────────────────────────────────────────────


@login_required
def contribution_add(request, holding_pk):
    holding = get_object_or_404(Holding, pk=holding_pk)
    form = MonthlyContributionForm(request.POST or None, holding=holding)
    if form.is_valid():
        form.save()
        messages.success(request, "Monthly contribution added.")
        return redirect("assets_dashboard")
    return render(
        request,
        "assets/contribution_form.html",
        {
            "form": form,
            "holding": holding,
            "title": f"Add Contribution — {holding.ticker} ({holding.account.name})",
        },
    )


@login_required
def contribution_edit(request, pk):
    contribution = get_object_or_404(MonthlyContribution, pk=pk)
    form = MonthlyContributionForm(request.POST or None, instance=contribution)
    if form.is_valid():
        form.save()
        messages.success(request, "Contribution updated.")
        return redirect("assets_dashboard")
    return render(
        request,
        "assets/contribution_form.html",
        {
            "form": form,
            "holding": contribution.holding,
            "title": f"Edit Contribution — {contribution.holding.ticker}",
        },
    )


@login_required
def contribution_delete(request, pk):
    contribution = get_object_or_404(MonthlyContribution, pk=pk)
    if request.method == "POST":
        contribution.delete()
        messages.success(request, "Contribution removed.")
        return redirect("assets_dashboard")
    return render(
        request,
        "assets/confirm_delete.html",
        {
            "obj": contribution,
            "cancel_url": reverse("assets_dashboard"),
        },
    )


# ── Price Refresh ─────────────────────────────────────────────────────────────


@login_required
@require_POST
def refresh_prices(request):
    try:
        import yfinance as yf
    except ImportError:
        messages.error(request, "yfinance is not installed. Run: pip install yfinance")
        return redirect("assets_dashboard")

    tickers = list(Holding.objects.values_list("ticker", flat=True).distinct())
    if not tickers:
        messages.warning(request, "No holdings to refresh.")
        return redirect("assets_dashboard")

    # Skip placeholder tickers for non-market assets (pensions, private funds, etc.)
    SKIP_TICKERS = {"N/A", "NA", "NONE", "CASH", "-", "N.A."}
    market_tickers = [t for t in tickers if t.upper() not in SKIP_TICKERS]
    skipped_count = len(tickers) - len(market_tickers)

    if not market_tickers:
        messages.info(request, "No market tickers to refresh (all holdings are non-market assets).")
        return redirect("assets_dashboard")

    updated = 0
    errors = []
    for ticker in market_tickers:
        # For crypto accounts, bare symbols like ETH/BTC need the -USD suffix for yfinance
        yf_ticker = ticker
        holding_qs = Holding.objects.filter(ticker=ticker)
        if holding_qs.filter(account__account_type="crypto").exists() and "-" not in ticker:
            yf_ticker = f"{ticker}-USD"
        try:
            data = yf.Ticker(yf_ticker).fast_info
            price = data.last_price
            if price:
                holding_qs.update(
                    last_price=price,
                    last_price_updated=timezone.now(),
                )
                updated += 1
            else:
                errors.append(ticker)
        except Exception:
            errors.append(ticker)

    if updated:
        msg = f"Prices updated for {updated} ticker(s)."
        if skipped_count:
            msg += f" ({skipped_count} non-market holding(s) skipped.)"
        messages.success(request, msg)
    if errors:
        messages.warning(request, f"Could not fetch: {', '.join(errors)}")

    return redirect("assets_dashboard")
