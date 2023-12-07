"""
© Ocado Group
Created on 04/12/2023 at 17:19:37(+00:00).

User model.
"""

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta

from ...models import AbstractModel

# from . import student as _student
from . import auth_factor as _auth_factor
from . import otp_bypass_token as _otp_bypass_token
from . import session as _session
from . import teacher as _teacher


class User(AbstractUser, AbstractModel):
    """A user within the CFL system."""

    objects = UserManager.from_queryset(  # type: ignore[misc]
        AbstractModel.QuerySet
    )()  # type: ignore[assignment]

    session: "_session.Session"
    auth_factors: QuerySet["_auth_factor.AuthFactor"]
    otp_bypass_tokens: QuerySet["_otp_bypass_token.OtpBypassToken"]

    otp_secret = models.CharField(
        _("OTP secret"),
        max_length=40,
        null=True,
        editable=False,
        help_text=_("Secret used to generate a OTP."),
    )

    last_otp_for_time = models.DateTimeField(
        _("last OTP for-time"),
        null=True,
        editable=False,
        help_text=_(
            "Used to prevent replay attacks, where the same OTP is used for"
            " different times."
        ),
    )

    # pylint: disable-next=unsubscriptable-object
    teacher: models.OneToOneField["_teacher.Teacher"] = models.OneToOneField(
        "user.Teacher",
        null=True,
        editable=False,
        on_delete=models.CASCADE,
    )

    # student: "_student.Student" = models.OneToOneField(
    #     "user.Student",
    #     null=True,
    #     editable=False,
    #     on_delete=models.CASCADE,
    # )

    # class Meta(TypedModelMeta):  # pylint: disable=missing-class-docstring
    #     constraints = [
    #         models.CheckConstraint(
    #             check=(
    #                 Q(teacher__isnull=True, student__isnull=False)
    #                 | Q(teacher__isnull=False, student__isnull=True)
    #             ),
    #             name="user__teacher_is_null_or_student_is_null",
    #         ),
    #     ]

    @property
    def is_authenticated(self):
        """Check if the user has any pending auth factors."""

        try:
            return not self.session.session_auth_factors.exists()
        except _session.Session.DoesNotExist:
            return False
