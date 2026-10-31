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
            email = form.cleaned_data.get("email", "").lower()
            password = form.cleaned_data.get("password", "")
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                return redirect("dashboard:index")

        return render(
            request,
            "user/auth.html",
            {
                "form": form,
                "error": "Неверный логин или пароль! Повторите попытку.",
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
            if user:
                login(request, user)
            return redirect("dashboard:index")
        else:
            error_message = None
            if "__all__" in form.errors:
                error_message = form.errors["__all__"][0]
            elif form.errors:
                # Берем первую ошибку из полей формы
                first_field_errors = next(iter(form.errors.values()))
                error_message = first_field_errors[0]

            return render(
                request,
                "user/registration.html",
                {"form": form, "error": error_message},
            )


class LogoutView(View):
    """Выход"""

    @staticmethod
    def get(request):
        logout(request)
        return redirect("dashboard:index")
