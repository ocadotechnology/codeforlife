from datetime import timedelta

from django.test import RequestFactory, TestCase
from django.utils import timezone
from django.utils.crypto import get_random_string

from ....auth.backends import TokenBackend
from ....models import AuthFactor, BackupToken, Session, SessionAuthFactor, User


class TestTokenBackend(TestCase):
    def setUp(self):
        self.backend = TokenBackend()
        self.request_factory = RequestFactory()

        self.user = User.objects.get(id=2)

        self.auth_factor = AuthFactor.objects.create(
            user=self.user,
            type=AuthFactor.Type.OTP,
        )

        self.session = Session.objects.create(
            session_key="a",
            session_data="",
            expire_date=timezone.now() + timedelta(hours=24),
            user=self.user,
        )

        self.session_auth_factor = SessionAuthFactor.objects.create(
            session=self.session,
            auth_factor=self.auth_factor,
        )

        self.tokens = [
            get_random_string(8) for _ in range(BackupToken.max_count)
        ]
        self.backup_tokens = BackupToken.objects.bulk_create(
            [BackupToken(user=self.user, token=token) for token in self.tokens]
        )

    def test_authenticate(self):
        request = self.request_factory.post("/")
        request.user = self.user

        user = self.backend.authenticate(request, token=self.tokens[0])

        assert user == self.user
        assert self.backup_tokens[0].id is None
