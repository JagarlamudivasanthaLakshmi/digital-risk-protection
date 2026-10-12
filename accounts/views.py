from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views import View
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .forms import RegistrationForm
from .serializers import RegistrationSerializer


class RegisterView(View):
    def get(self, request):
        return render(request, "register.html", {"form": RegistrationForm()})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
        return render(request, "register.html", {"form": form}, status=400)


class RegistrationAPIView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]
