"""
© Ocado Group
Created on 05/12/2023 at 17:43:14(+00:00).

Teacher model.
"""

import typing as t

from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta

from ...models import WarehouseModel
from . import klass as _class
from . import school as _school
from . import student as _student
from . import user as _user


class Teacher(WarehouseModel):
    """A user's teacher profile."""

    # pylint: disable-next=missing-class-docstring
    class Manager(WarehouseModel.Manager["Teacher"]):
        def create_user(self, teacher: t.Dict[str, t.Any], **fields):
            """Create a user with a teacher profile.

            Args:
                user: The user fields.

            Returns:
                A teacher profile.
            """

            return _user.User.objects.create_user(
                **fields,
                teacher=self.create(**teacher),
            )

    objects: Manager = Manager()

    user: "_user.User"
    classes: QuerySet["_class.Class"]

    school_id: t.Optional[int]
    school: t.Optional[
        "_school.School"
    ] = models.ForeignKey(  # type: ignore[assignment]
        "user.School",
        related_name="teachers",
        null=True,
        on_delete=models.SET_NULL,
    )

    # TODO: phase out and use django's permission system.
    is_admin = models.BooleanField(
        _("is administrator"),
        default=False,
        help_text=_("Designates if the teacher has admin privileges."),
    )

    class Meta(TypedModelMeta):
        verbose_name = _("teacher")
        verbose_name_plural = _("teachers")

    @property
    def students(self) -> QuerySet["_student.Student"]:
        """All students in this teacher's classes.

        Returns:
            A queryset
        """

        return _student.Student.objects.filter(
            klass_id__in=list(self.classes.values_list("id", flat=True)),
        )
