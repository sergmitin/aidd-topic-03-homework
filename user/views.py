from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.generic import View

from .forms import AuthForm, RegistrationForm


class AuthView(View):
    """Авторизация"""

    @staticmethod
    def get(request):
        return render(request, "user/auth.html", {"form": AuthForm()})

    @staticmethod
    def post(request):
        form = AuthForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                return redirect("dashboard:index")
            error = "Неверный логин или пароль! Повторите попытку."
        else:
            error = "Пожалуйста, заполните форму корректно."

        return render(
            request,
            "user/auth.html",
            {
                "form": form,
                "error": error,
            },
        )


class RegistrationView(View):
    """Регистрация"""

    @staticmethod
    def get(request):
        return render(request, "user/registration.html", {"form": RegistrationForm()})

    @staticmethod
    def post(request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard:index")

        error = None
        if form.non_field_errors():
            error = form.non_field_errors()[0]
        elif form.errors:
            first_field = next(iter(form.errors))
            error = form.errors[first_field][0]

        return render(
            request,
            "user/registration.html",
            {"form": form, "error": error or "Проверьте введенные данные."},
        )


class LogoutView(View):
    """Выход"""

    @staticmethod
    def get(request):
        logout(request)
        return redirect("dashboard:index")

    @staticmethod
    def post(request):
        logout(request)
        return redirect("dashboard:index")
