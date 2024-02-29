"""
© Ocado Group
Created on 30/01/2024 at 18:06:31(+00:00).

Base test case for all model serializers.
"""

import typing as t
from unittest.case import _AssertRaisesContext

from django.db.models import Model
from django.forms.models import model_to_dict
from django.test import TestCase
from rest_framework.serializers import BaseSerializer, ValidationError

from ..serializers import ModelSerializer
from ..types import DataDict
from .api_request_factory import APIRequestFactory

AnyModel = t.TypeVar("AnyModel", bound=Model)


class ModelSerializerTestCase(TestCase, t.Generic[AnyModel]):
    """Base for all model serializer test cases."""

    model_serializer_class: t.Type[ModelSerializer[AnyModel]]

    request_factory = APIRequestFactory()

    @classmethod
    def setUpClass(cls):
        attr_name = "model_serializer_class"
        assert hasattr(cls, attr_name), f'Attribute "{attr_name}" must be set.'

        return super().setUpClass()

    @classmethod
    def get_model_class(cls) -> t.Type[AnyModel]:
        """Get the model view set's class.

        Returns:
            The model view set's class.
        """
        # pylint: disable-next=no-member
        return t.get_args(cls.__orig_bases__[0])[  # type: ignore[attr-defined]
            0
        ]

    def assert_raises_validation_error(self, code: str, *args, **kwargs):
        """Assert code block raises a validation error.

        Args:
            code: The validation code to assert.

        Returns:
            The assert-raises context which will auto-assert the code.
        """

        class Wrapper:
            """Wrap context to assert code on exit."""

            def __init__(self, ctx: "_AssertRaisesContext[ValidationError]"):
                self.ctx = ctx

            def __enter__(self, *args, **kwargs):
                return self.ctx.__enter__(*args, **kwargs)

            def __exit__(self, *args, **kwargs):
                value = self.ctx.__exit__(*args, **kwargs)
                assert (
                    code
                    == self.ctx.exception.detail[  # type: ignore[union-attr]
                        0  # type: ignore[index]
                    ].code
                )
                return value

        return Wrapper(self.assertRaises(ValidationError, *args, **kwargs))

    def _init_model_serializer(
        self, *args, parent: t.Optional[BaseSerializer] = None, **kwargs
    ):
        serializer = self.model_serializer_class(*args, **kwargs)
        if parent:
            serializer.parent = parent

        return serializer

    def assert_validate(
        self,
        attrs: t.Union[DataDict, t.List[DataDict]],
        error_code: str,
        *args,
        **kwargs,
    ):
        """Asserts that calling validate() raises the expected error code.

        Args:
            attrs: The attributes to pass to validate().
            error_code: The expected error code to be raised.
        """
        serializer = self._init_model_serializer(*args, **kwargs)
        with self.assert_raises_validation_error(error_code):
            serializer.validate(attrs)  # type: ignore[arg-type]

    # pylint: disable-next=too-many-arguments
    def assert_validate_field(
        self, name: str, value, error_code: str, *args, **kwargs
    ):
        """Asserts that calling validate_field() raises the expected error code.

        Args:
            name: The name of the field.
            value: The value to pass to validate_field().
            error_code: The expected error code to be raised.
        """
        serializer = self._init_model_serializer(*args, **kwargs)
        validate_field = getattr(serializer, f"validate_{name}")
        assert callable(validate_field)
        with self.assert_raises_validation_error(error_code):
            validate_field(value)

    def _assert_data_is_subset_of_model(self, data: DataDict, model):
        assert isinstance(model, Model)

        for field, value in data.copy().items():
            # NOTE: A data value of type dict == a foreign object on the model.
            if isinstance(value, dict):
                self._assert_data_is_subset_of_model(
                    value,
                    getattr(model, field),
                )
                data.pop(field)
            elif isinstance(value, Model):
                data[field] = value.pk

        self.assertDictContainsSubset(data, model_to_dict(model))

    def assert_create(
        self,
        validated_data: DataDict,
        *args,
        new_data: t.Optional[DataDict] = None,
        non_model_fields: t.Optional[t.Iterable[str]] = None,
        **kwargs,
    ):
        """Assert that the data used to create the model is a subset of the
        model's data.

        Args:
            validated_data: The data used to create the model.
            new_data: Any new data that the model may have after creating.
            non_model_fields: Validated data fields that are not in the model.
        """
        serializer = self._init_model_serializer(*args, **kwargs)
        model = serializer.create(validated_data.copy())
        data = {**validated_data, **(new_data or {})}
        for field in non_model_fields or []:
            data.pop(field)
        self._assert_data_is_subset_of_model(data, model)

    def assert_update(
        self,
        instance: AnyModel,
        validated_data: DataDict,
        *args,
        new_data: t.Optional[DataDict] = None,
        non_model_fields: t.Optional[t.Iterable[str]] = None,
        **kwargs,
    ):
        """Assert that the data used to update the model is a subset of the
        model's data.

        Args:
            instance: The model instance to update.
            validated_data: The data used to update the model.
            new_data: Any new data that the model may have after updating.
            non_model_fields: Validated data fields that are not in the model.
        """
        serializer = self._init_model_serializer(*args, **kwargs)
        model = serializer.update(instance, validated_data.copy())
        data = {**validated_data, **(new_data or {})}
        for field in non_model_fields or []:
            data.pop(field)
        self._assert_data_is_subset_of_model(data, model)

    def assert_update_many(
        self,
        instance: t.List[AnyModel],
        validated_data: t.List[DataDict],
        *args,
        new_data: t.Optional[t.List[DataDict]] = None,
        non_model_fields: t.Optional[t.Iterable[str]] = None,
        **kwargs,
    ):
        """Assert that the data used to update the models is a subset of the
        models' data.

        Use this assert helper instead of "assert_update" if the update() on a
        list serializer is being called.

        Args:
            instance: The model instances to update.
            validated_data: The data used to update the models.
            new_data: Any new data that the models may have after updating.
            non_model_fields: Validated data fields that are not in the model.
        """
        kwargs.pop("many", None)  # many must be True
        serializer = self._init_model_serializer(*args, **kwargs, many=True)
        models = serializer.update(
            instance, [data.copy() for data in validated_data]
        )
        new_data = new_data or [{} for _ in range(len(instance))]
        for data, _new_data, model in zip(validated_data, new_data, models):
            data = {**data, **_new_data}
            for field in non_model_fields or []:
                data.pop(field)
            self._assert_data_is_subset_of_model(data, model)

    def assert_to_representation(
        self, instance: AnyModel, new_data: DataDict, *args, **kwargs
    ):
        """Assert:
        1. the new data fields not contained in the model are equal.
        2. the original data fields contained in the model are equal.

        Args:
            instance: The model instance to represent.
            new_data: The field values not contained in the model.
        """
        serializer = self._init_model_serializer(*args, **kwargs)
        data = serializer.to_representation(instance)

        for field, value in new_data.items():
            assert value == data.pop(field)

        self._assert_data_is_subset_of_model(data, instance)
