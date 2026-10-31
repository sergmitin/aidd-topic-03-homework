from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="investor@example.com",
            email="investor@example.com",
            password="StrongPassword123!",
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("user:auth"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "user/auth.html")

    def test_login_success(self):
        response = self.client.post(
            reverse("user:auth"),
            {"email": "investor@example.com", "password": "StrongPassword123!"},
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_invalid_password(self):
        response = self.client.post(
            reverse("user:auth"),
            {"email": "investor@example.com", "password": "WrongPassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверный логин или пароль")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_empty_form(self):
        response = self.client.post(reverse("user:auth"), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Пожалуйста, заполните форму корректно")

    def test_logout(self):
        self.client.login(username="investor@example.com", password="StrongPassword123!")
        response = self.client.get(reverse("user:logout"))
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class UserRegistrationTests(TestCase):
    def test_registration_page_renders(self):
        response = self.client.get(reverse("user:registration"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "user/registration.html")

    def test_registration_success(self):
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "newuser@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertTrue(User.objects.filter(username="newuser@example.com").exists())
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_registration_password_mismatch(self):
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "mismatch@example.com",
                "password1": "SecurePass123!",
                "password2": "DifferentPass456!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введенные пароли не совпадают")
        self.assertFalse(User.objects.filter(username="mismatch@example.com").exists())

    def test_registration_duplicate_email(self):
        User.objects.create_user(
            username="existing@example.com",
            email="existing@example.com",
            password="Pass1",
        )
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "existing@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "уже зарегистрирован")

    def test_registration_invalid_email(self):
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "not-an-email",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="not-an-email").exists())
