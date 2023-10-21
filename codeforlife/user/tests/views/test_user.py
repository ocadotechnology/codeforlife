import typing as t

from django.db.models.query import QuerySet
from rest_framework import status

from ....tests import APITestCase, APIClient
from ...serializers import UserSerializer
from ...models import User, School, Teacher, Student, Class, UserProfile


class TestUserViewSet(APITestCase):
    """
    Base naming convention:
        test_{action}

    action: This view set action.
        https://www.django-rest-framework.org/api-guide/viewsets/#viewset-actions
    """

    # TODO: replace this setup with data fixtures.
    def setUp(self):
        school = School.objects.create(
            name="ExampleSchool",
            country="UK",
        )

        user = User.objects.create(
            first_name="Example",
            last_name="Teacher",
            email="example.teacher@codeforlife.com",
            username="example.teacher@codeforlife.com",
        )

        user_profile = UserProfile.objects.create(user=user)

        teacher = Teacher.objects.create(
            user=user_profile,
            new_user=user,
            school=school,
        )

        klass = Class.objects.create(
            name="ExampleClass",
            teacher=teacher,
            created_by=teacher,
        )

        user = User.objects.create(
            first_name="Example",
            last_name="Student",
            email="example.student@codeforlife.com",
            username="example.student@codeforlife.com",
        )

        user_profile = UserProfile.objects.create(user=user)

        Student.objects.create(
            class_field=klass,
            user=user_profile,
            new_user=user,
        )

    def _login_teacher(self):
        user = self.client.login(
            email="alberteinstein@codeforlife.com",
            password="Password1",
        )
        assert user.teacher
        assert user.teacher.school
        return user

    def _login_student(self):
        user = self.client.login(
            email="leonardodavinci@codeforlife.com",
            password="Password1",
        )
        assert user.student
        assert user.student.class_field.teacher.school
        return user

    def _get_other_user(
        self,
        user: User,
        other_users: QuerySet[User],
        is_teacher: bool,
        same_school: bool,
    ):
        school = (
            user.teacher.school
            if user.teacher
            else user.student.class_field.teacher.school
        )

        other_user = other_users.first()
        assert other_user
        assert user != other_user

        if is_teacher:
            assert other_user.teacher
            other_school = other_user.teacher.school
        else:
            assert other_user.student
            other_school = other_user.student.class_field.teacher.school

        assert other_school
        if same_school:
            assert school == other_school
        else:
            assert school != other_school

        return other_user

    """
    Retrieve naming convention:
        test_retrieve__{user_type}__{other_user_type}__{same_school}

    user_type: The type of user that is making the request. Options:
        - teacher: A teacher.
        - student: A student.

    other_user_type: The type of user whose data is being requested. Options:
        - self: User's own data.
        - teacher: Another teacher's data.
        - student: Another student's data.

    same_school: A flag for if the other user is from the same school. Options:
        - same_school: The other user is from the same school.
        - not_same_school: The other user is not from the same school.
    """

    def _retrieve_user(
        self,
        user: User,
        status_code_assertion: APIClient.StatusCodeAssertion = None,
    ):
        return self.client.retrieve(
            "user",
            user,
            UserSerializer,
            status_code_assertion,
        )

    def test_retrieve__teacher__self(self):
        """
        Teacher can retrieve their own user data.
        """

        user = self._login_teacher()
        self._retrieve_user(user)

    def test_retrieve__student__self(self):
        """
        Student can retrieve their own user data.
        """

        user = self._login_student()
        self._retrieve_user(user)

    def test_retrieve__teacher__teacher__same_school(self):
        """
        Teacher can retrieve another teacher from the same school.
        """

        user = self._login_teacher()

        other_user = self._get_other_user(
            user,
            other_users=User.objects.exclude(id=user.id).filter(
                new_teacher__school=user.teacher.school
            ),
            is_teacher=True,
            same_school=True,
        )

        self._retrieve_user(other_user)

    def test_retrieve__teacher__student__same_school(self):
        """
        Teacher can retrieve a student from the same school.
        """

        user = self._login_teacher()

        other_user = self._get_other_user(
            user,
            other_users=User.objects.filter(
                new_student__class_field__teacher__school=user.teacher.school
            ),
            is_teacher=False,
            same_school=True,
        )

        self._retrieve_user(other_user)

    def test_retrieve__student__teacher__same_school(self):
        """
        Student can not retrieve a teacher from the same school.
        """

        user = self._login_student()

        other_user = self._get_other_user(
            user,
            other_users=User.objects.filter(
                new_teacher__school=user.student.class_field.teacher.school
            ),
            is_teacher=True,
            same_school=True,
        )

        self._retrieve_user(
            other_user,
            status_code_assertion=status.HTTP_404_NOT_FOUND,
        )

    def test_retrieve__student__student__same_school(self):
        """
        Student can not retrieve another student from the same school.
        """

        user = self._login_student()

        other_user = self._get_other_user(
            user,
            other_users=User.objects.exclude(id=user.id).filter(
                new_student__class_field__teacher__school=user.student.class_field.teacher.school
            ),
            is_teacher=False,
            same_school=True,
        )

        self._retrieve_user(
            other_user,
            status_code_assertion=status.HTTP_404_NOT_FOUND,
        )

    def test_retrieve__teacher__teacher__not_same_school(self):
        """
        Teacher can not retrieve another teacher from another school.
        """

        user = self._login_teacher()

        other_user = self._get_other_user(
            user,
            other_users=User.objects.exclude(
                new_teacher__school=user.teacher.school
            ).filter(new_teacher__school__isnull=False),
            is_teacher=True,
            same_school=False,
        )

        self._retrieve_user(
            other_user,
            status_code_assertion=status.HTTP_404_NOT_FOUND,
        )

    def test_retrieve__teacher__student__not_same_school(self):
        """
        Teacher can not retrieve a student from another school.
        """

        user = self._login_teacher()

        other_user = self._get_other_user(
            user,
            other_users=User.objects.exclude(
                new_student__class_field__teacher__school=user.teacher.school
            ).filter(new_student__class_field__teacher__school__isnull=False),
            is_teacher=False,
            same_school=False,
        )

        self._retrieve_user(
            other_user,
            status_code_assertion=status.HTTP_404_NOT_FOUND,
        )

    def test_retrieve__student__teacher__not_same_school(self):
        """
        Student can not retrieve a teacher from another school.
        """

        user = self._login_student()

        other_user = self._get_other_user(
            user,
            other_users=User.objects.exclude(
                new_teacher__school=user.student.class_field.teacher.school
            ).filter(new_teacher__school__isnull=False),
            is_teacher=True,
            same_school=False,
        )

        self._retrieve_user(
            other_user,
            status_code_assertion=status.HTTP_404_NOT_FOUND,
        )

    def test_retrieve__student__student__not_same_school(self):
        """
        Student can not retrieve another student from another school.
        """

        user = self._login_student()

        other_user = self._get_other_user(
            user,
            other_users=User.objects.exclude(
                new_student__class_field__teacher__school=user.student.class_field.teacher.school
            ).filter(new_student__class_field__teacher__school__isnull=False),
            is_teacher=False,
            same_school=False,
        )

        self._retrieve_user(
            other_user,
            status_code_assertion=status.HTTP_404_NOT_FOUND,
        )

    """
    List naming convention:
        test_list__{user_type}

    user_type: The type of user that is making the request. Options:
        - teacher: A teacher.
        - student: A student.
    """

    def _list_users(
        self,
        users: t.Iterable[User],
        status_code_assertion: APIClient.StatusCodeAssertion = None,
    ):
        return self.client.list(
            "user",
            users,
            UserSerializer,
            status_code_assertion,
        )

    def test_list__teacher(self):
        """
        Teacher can list all the users in the same school.
        """

        user = self._login_teacher()

        self._list_users(
            User.objects.filter(new_teacher__school=user.teacher.school)
            | User.objects.filter(
                new_student__class_field__teacher__school=user.teacher.school
            )
        )

    def test_list__student(self):
        """
        Student can list only themselves.
        """

        user = self._login_student()

        self._list_users([user])
