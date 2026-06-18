from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def ai_dashboard(request):
    return render(request, "ai_insights/dashboard.html")
