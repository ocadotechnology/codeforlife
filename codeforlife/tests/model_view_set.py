"""
© Ocado Group
Created on 19/01/2024 at 17:06:45(+00:00).

Base test case for all model view sets.
"""

import typing as t
from datetime import datetime
from unittest.mock import patch

from django.db.models import Model
from django.db.models.query import QuerySet
from django.urls import reverse as _reverse
from django.utils import timezone
from django.utils.http import urlencode
from pyotp import TOTP
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from rest_framework.test import APIClient, APIRequestFactory, APITestCase
from rest_framework.viewsets import ModelViewSet

from ..user.models import AuthFactor, User

AnyModelViewSet = t.TypeVar("AnyModelViewSet", bound=ModelViewSet)
AnyModelSerializer = t.TypeVar("AnyModelSerializer", bound=ModelSerializer)
AnyModel = t.TypeVar("AnyModel", bound=Model)


class ModelViewSetClient(
    APIClient,
    t.Generic[AnyModelViewSet, AnyModelSerializer, AnyModel],
):
    """
    An API client that helps make requests to a model view set and assert their
    responses.
    """

    def __init__(self, enforce_csrf_checks: bool = False, **defaults):
        super().__init__(enforce_csrf_checks, **defaults)
        self.request_factory = APIRequestFactory(
            enforce_csrf_checks,
            **defaults,
        )

    _test_case: "ModelViewSetTestCase[AnyModelViewSet, AnyModelSerializer, AnyModel]"

    @property
    def _model_class(self):
        """Shortcut to get model class."""

        # pylint: disable-next=no-member
        return self._test_case.get_model_class()

    @property
    def _model_serializer_class(self):
        """Shortcut to get model serializer class."""

        # pylint: disable-next=no-member
        return self._test_case.get_model_serializer_class()

    @property
    def _model_view_set_class(self):
        """Shortcut to get model view set class."""

        # pylint: disable-next=no-member
        return self._test_case.get_model_view_set_class()

    Data = t.Dict[str, t.Any]
    StatusCodeAssertion = t.Optional[t.Union[int, t.Callable[[int], bool]]]
    ListFilters = t.Optional[t.Dict[str, str]]

    @staticmethod
    def status_code_is_ok(status_code: int):
        """Check if the status code is greater than or equal to 200 and less
        than 300.

        Args:
            status_code: The status code to check.

        Returns:
            A flag designating if the status code is OK.
        """

        return 200 <= status_code < 300

    def assert_data_equals_model(
        self,
        data: Data,
        model: AnyModel,
        contains_subset: bool = False,
    ):
        # pylint: disable=line-too-long
        """Check if the data equals the current state of the model instance.

        Args:
            data: The data to check.
            model: The model instance.
            model_serializer_class: The serializer used to serialize the model's data.
            contains_subset: A flag designating whether the data is a subset of the serialized model.

        Returns:
            A flag designating if the data equals the current state of the model
            instance.
        """
        # pylint: enable=line-too-long

        def parse_data(data):
            if isinstance(data, list):
                return [parse_data(value) for value in data]
            if isinstance(data, dict):
                return {key: parse_data(value) for key, value in data.items()}
            if isinstance(data, datetime):
                return data.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            return data

        actual_data = parse_data(self._model_serializer_class(model).data)

        if contains_subset:
            # pylint: disable-next=no-member
            self._test_case.assertDictContainsSubset(
                data,
                actual_data,
                "Data is not a subset of serialized model.",
            )
        else:
            # pylint: disable-next=no-member
            self._test_case.assertDictEqual(
                data,
                actual_data,
                "Data does not equal serialized model.",
            )

    def reverse(
        self,
        action: str,
        model: t.Optional[AnyModel] = None,
        **kwargs,
    ):
        """Get the reverse URL for the model view set's action.

        Args:
            action: The name of the action.
            model: The model to look up.

        Returns:
            The reversed URL.
        """

        reverse_kwargs = kwargs.pop("kwargs", {})
        if model is not None:
            reverse_kwargs[self._model_view_set_class.lookup_field] = getattr(
                model,
                self._model_view_set_class.lookup_field,
            )

        return _reverse(
            viewname=kwargs.pop(
                "viewname",
                # pylint: disable-next=no-member
                f"{self._test_case.basename}-{action}",
            ),
            kwargs=reverse_kwargs,
            **kwargs,
        )

    # pylint: disable-next=too-many-arguments
    def generic(
        self,
        method,
        path,
        data="",
        content_type="application/octet-stream",
        secure=False,
        status_code_assertion: StatusCodeAssertion = None,
        **extra,
    ):
        response = t.cast(
            Response,
            super().generic(
                method,
                path,
                data,
                content_type,
                secure,
                **extra,
            ),
        )

        # Use a custom kwarg to handle the common case of checking the
        # response's status code.
        if status_code_assertion is None:
            status_code_assertion = self.status_code_is_ok
        elif isinstance(status_code_assertion, int):
            expected_status_code = status_code_assertion
            status_code_assertion = (
                # pylint: disable-next=unnecessary-lambda-assignment
                lambda status_code: status_code
                == expected_status_code
            )

        # pylint: disable-next=no-member
        status_code = response.status_code
        assert status_code_assertion(
            status_code
        ), f"Unexpected status code: {status_code}."

        return response

    def create(
        self,
        data: Data,
        status_code_assertion: StatusCodeAssertion = status.HTTP_201_CREATED,
        **kwargs,
    ):
        """Create a model.

        Args:
            data: The values for each field.
            status_code_assertion: The expected status code.

        Returns:
            The HTTP response.
        """

        response: Response = self.post(
            self.reverse("list"),
            data=data,
            status_code_assertion=status_code_assertion,
            **kwargs,
        )

        if self.status_code_is_ok(response.status_code):
            # pylint: disable-next=no-member
            self._test_case.assertDictContainsSubset(
                data,
                response.json(),  # type: ignore[attr-defined]
            )

        return response

    def retrieve(
        self,
        model: AnyModel,
        status_code_assertion: StatusCodeAssertion = status.HTTP_200_OK,
        **kwargs,
    ):
        """Retrieve a model.

        Args:
            model: The model to retrieve.
            status_code_assertion: The expected status code.

        Returns:
            The HTTP response.
        """

        response: Response = self.get(
            self.reverse("detail", model),
            status_code_assertion=status_code_assertion,
            **kwargs,
        )

        if self.status_code_is_ok(response.status_code):
            self.assert_data_equals_model(
                response.json(),  # type: ignore[attr-defined]
                model,
            )

        return response

    def list(
        self,
        models: t.Iterable[AnyModel],
        status_code_assertion: StatusCodeAssertion = status.HTTP_200_OK,
        filters: ListFilters = None,
        **kwargs,
    ):
        """Retrieve a list of models.

        Args:
            models: The model list to retrieve.
            status_code_assertion: The expected status code.
            filters: The filters to apply to the list.

        Returns:
            The HTTP response.
        """

        assert self._model_class.objects.difference(
            self._model_class.objects.filter(
                pk__in=[model.pk for model in models]
            )
        ).exists(), "List must exclude some models for a valid test."

        response: Response = self.get(
            f"{self.reverse('list')}?{urlencode(filters or {})}",
            status_code_assertion=status_code_assertion,
            **kwargs,
        )

        if self.status_code_is_ok(response.status_code):
            for data, model in zip(response.json()["data"], models):  # type: ignore[attr-defined]
                self.assert_data_equals_model(data, model)

        return response

    def partial_update(
        self,
        model: AnyModel,
        data: Data,
        status_code_assertion: StatusCodeAssertion = status.HTTP_200_OK,
        **kwargs,
    ):
        """Partially update a model.

        Args:
            model: The model to partially update.
            data: The values for each field.
            status_code_assertion: The expected status code.

        Returns:
            The HTTP response.
        """

        response: Response = self.patch(
            self.reverse("detail", model),
            data=data,
            status_code_assertion=status_code_assertion,
            **kwargs,
        )

        if self.status_code_is_ok(response.status_code):
            model.refresh_from_db()
            self.assert_data_equals_model(
                response.json(),  # type: ignore[attr-defined]
                model,
                contains_subset=True,
            )

        return response

    def destroy(
        self,
        model: AnyModel,
        status_code_assertion: StatusCodeAssertion = status.HTTP_204_NO_CONTENT,
        anonymized: bool = False,
        **kwargs,
    ):
        """Destroy a model.

        Args:
            model: The model to destroy.
            status_code_assertion: The expected status code.
            anonymized: Whether or not the data is anonymized.

        Returns:
            The HTTP response.
        """

        response: Response = self.delete(
            self.reverse("detail", model),
            status_code_assertion=status_code_assertion,
            **kwargs,
        )

        if not anonymized and self.status_code_is_ok(response.status_code):
            # pylint: disable-next=no-member
            with self._test_case.assertRaises(model.DoesNotExist):
                model.refresh_from_db()

        return response

    def login(self, **credentials):
        assert super().login(
            **credentials
        ), f"Failed to login with credentials: {credentials}."

        user = User.objects.get(session=self.session.session_key)

        if user.session.session_auth_factors.filter(
            auth_factor__type=AuthFactor.Type.OTP
        ).exists():
            request = self.request_factory.request()
            request.user = user

            now = timezone.now()
            otp = TOTP(user.otp_secret).at(now)
            with patch.object(timezone, "now", return_value=now):
                assert super().login(
                    request=request,
                    otp=otp,
                ), f'Failed to login with OTP "{otp}" at {now}.'

        assert user.is_authenticated, "Failed to authenticate user."

        return user

    def login_teacher(self, is_admin: bool, **credentials):
        """Log in a user and assert they are a teacher.

        Args:
            is_admin: Whether or not the teacher is an admin.

        Returns:
            The teacher-user.
        """

        user = self.login(**credentials)
        assert user.teacher
        assert user.teacher.school
        assert is_admin == user.teacher.is_admin
        return user

    def login_student(self, **credentials):
        """Log in a user and assert they are a student.

        Returns:
            The student-user.
        """

        user = self.login(**credentials)
        assert user.student
        assert user.student.class_field.teacher.school
        return user

    def login_indy(self, **credentials):
        """Log in an independent and assert they are a student.

        Returns:
            The independent-user.
        """

        user = self.login(**credentials)
        assert user.student
        assert not user.student.class_field
        return user


class ModelViewSetTestCase(
    APITestCase,
    t.Generic[AnyModelViewSet, AnyModelSerializer, AnyModel],
):
    """Base for all model view set test cases."""

    basename: str
    client: ModelViewSetClient[  # type: ignore[assignment]
        AnyModelViewSet,
        AnyModelSerializer,
        AnyModel,
    ]
    client_class = ModelViewSetClient  # type: ignore[assignment]

    def _pre_setup(self):
        super()._pre_setup()
        # pylint: disable-next=protected-access
        self.client._test_case = self

    @classmethod
    def _get_generic_args(
        cls,
    ) -> t.Tuple[
        t.Type[AnyModelViewSet],
        t.Type[AnyModelSerializer],
        t.Type[AnyModel],
    ]:
        # pylint: disable-next=no-member
        return t.get_args(cls.__orig_bases__[0])  # type: ignore[attr-defined,return-value]

    @classmethod
    def get_model_view_set_class(cls):
        """Get the model view set's class.

        Returns:
            The model view set's class.
        """

        return cls._get_generic_args()[0]

    @classmethod
    def get_model_serializer_class(cls):
        """Get the model serializer's class.

        Returns:
            The model serializer's class.
        """

        return cls._get_generic_args()[1]

    @classmethod
    def get_model_class(cls):
        """Get the model view set's class.

        Returns:
            The model view set's class.
        """

        return cls._get_generic_args()[2]

    def get_other_user(
        self,
        user: User,
        other_users: QuerySet[User],
        is_teacher: bool,
    ):
        """
        Get a different user.
        """

        other_user = other_users.first()
        assert other_user
        assert user != other_user
        assert other_user.is_teacher if is_teacher else other_user.is_student
        return other_user

    def get_other_school_user(
        self,
        user: User,
        other_users: QuerySet[User],
        is_teacher: bool,
    ):
        """
        Get a different user that is in a school.
        - the provided user does not have to be in a school.
        - the other user has to be in a school.
        """

        other_user = self.get_other_user(user, other_users, is_teacher)
        assert (
            other_user.teacher.school
            if is_teacher
            else other_user.student.class_field.teacher.school
        )
        return other_user

    def get_another_school_user(
        self,
        user: User,
        other_users: QuerySet[User],
        is_teacher: bool,
        same_school: bool,
        same_class: t.Optional[bool] = None,
    ):
        """
        Get a different user that is also in a school.
         - the provided user has to be in a school.
         - the other user has to be in a school.
        """

        other_user = self.get_other_school_user(user, other_users, is_teacher)

        school = (
            user.teacher.school
            if user.teacher
            else user.student.class_field.teacher.school  # type: ignore[union-attr]
        )
        assert school

        other_school = (
            other_user.teacher.school
            if is_teacher
            else other_user.student.class_field.teacher.school
        )
        assert other_school

        if same_school:
            assert school == other_school

            # Cannot assert that 2 teachers are in the same class since a class
            # can only have 1 teacher.
            if not (user.is_teacher and other_user.is_teacher):
                # At this point, same_class needs to be set.
                assert same_class is not None, "same_class must be set."

                # If one of the users is a teacher.
                if user.is_teacher or is_teacher:
                    # Get the teacher.
                    teacher = other_user if is_teacher else user

                    # Get the student's class' teacher.
                    class_teacher = (
                        user if is_teacher else other_user
                    ).student.class_field.teacher.new_user

                    # Assert the teacher is the class' teacher.
                    assert (
                        teacher == class_teacher
                        if same_class
                        else teacher != class_teacher
                    )
                # Else, both users are students.
                else:
                    assert (
                        user.student.class_field  # type: ignore[union-attr]
                        == other_user.student.class_field
                        if same_class
                        else user.student.class_field  # type: ignore[union-attr]
                        != other_user.student.class_field
                    )
        else:
            assert school != other_school

        return other_user
