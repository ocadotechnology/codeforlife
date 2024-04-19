"""
© Ocado Group
Created on 19/01/2024 at 17:15:56(+00:00).
"""

import typing as t

from django.db.models.query import QuerySet

from ...tests import ModelViewSetTestCase
from ..models import (
    AdminSchoolTeacherUser,
    Class,
    IndependentUser,
    NonAdminSchoolTeacherUser,
    NonSchoolTeacherUser,
    SchoolTeacherUser,
    Student,
    StudentUser,
    User,
)
from ..views import UserViewSet

RequestUser = User


# pylint: disable-next=too-many-ancestors,too-many-public-methods,missing-class-docstring
class TestUserViewSet(ModelViewSetTestCase[RequestUser, User]):
    basename = "user"
    model_view_set_class = UserViewSet
    fixtures = ["non_school_teacher", "school_1"]

    def setUp(self):
        self.admin_school_teacher_user = AdminSchoolTeacherUser.objects.get(
            email="admin.teacher@school1.com"
        )

    # test: get queryset

    def test_get_queryset__indy(self):
        """Independent-users can only target themselves."""
        user = IndependentUser.objects.first()
        assert user

        self.assert_get_queryset(
            values=[user],
            request=self.client.request_factory.get(user=user),
        )

    def test_get_queryset__student(self):
        """
        Student-users can only target themselves, their classmates and their
        teacher.
        """
        user = StudentUser.objects.first()
        assert user

        users = [
            user,
            user.student.class_field.teacher.new_user,
            *list(
                User.objects.exclude(pk=user.pk).filter(
                    new_student__in=user.student.class_field.students.all()
                )
            ),
        ]
        users.sort(key=lambda user: user.pk)

        self.assert_get_queryset(
            values=users,
            request=self.client.request_factory.get(user=user),
        )

    def test_get_queryset__teacher__non_school(self):
        """Non-school-teacher-users can only target themselves."""
        user = NonSchoolTeacherUser.objects.first()
        assert user

        self.assert_get_queryset(
            values=[user],
            request=self.client.request_factory.get(user=user),
        )

    def test_get_queryset__teacher__admin(self):
        """
        Admin-teacher-users can only target themselves, all teachers in their
        school and all student in their school.
        """
        user = AdminSchoolTeacherUser.objects.first()
        assert user

        users = [
            *list(user.teacher.school_teacher_users),
            *list(user.teacher.student_users),
        ]
        users.sort(key=lambda user: user.pk)

        self.assert_get_queryset(
            values=users,
            request=self.client.request_factory.get(user=user),
        )

    def test_get_queryset__teacher__non_admin(self):
        """
        Non-admin-teacher-users can only target themselves, all teachers in
        their school and their class-students.
        """
        user = NonAdminSchoolTeacherUser.objects.first()
        assert user

        users = [
            *list(
                SchoolTeacherUser.objects.filter(
                    new_teacher__school=user.teacher.school
                )
            ),
            *list(user.teacher.student_users),
        ]
        users.sort(key=lambda user: user.pk)

        self.assert_get_queryset(
            values=users,
            request=self.client.request_factory.get(user=user),
        )

    # test: actions

    def test_list(self):
        """Can successfully list users."""
        user = AdminSchoolTeacherUser.objects.first()
        assert user

        users = [
            *list(user.teacher.school_teacher_users),
            *list(user.teacher.student_users),
        ]
        users.sort(key=lambda user: user.pk)

        self.client.login_as(user, password="abc123")
        self.client.list(models=users)

    def test_list__students_in_class(self):
        """Can successfully list student-users in a class."""
        user = self.admin_school_teacher_user
        assert user.teacher.classes.count() >= 2

        klass = t.cast(Class, user.teacher.classes.first())
        students: QuerySet[Student] = klass.students.all()
        assert (
            Student.objects.filter(
                class_field__teacher__school=user.teacher.school
            )
            .exclude(pk__in=students.values_list("pk", flat=True))
            .exists()
        ), "There are no other students in other classes, in the same school."

        self.client.login_as(user)
        self.client.list(
            models=StudentUser.objects.filter(new_student__in=students),
            filters={"students_in_class": klass.access_code},
        )

    def test_retrieve(self):
        """Can successfully retrieve users."""
        user = AdminSchoolTeacherUser.objects.first()
        assert user

        self.client.login_as(user, password="abc123")
        self.client.retrieve(model=user)
