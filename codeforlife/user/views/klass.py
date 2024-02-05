"""
© Ocado Group
Created on 24/01/2024 at 13:47:53(+00:00).
"""

from ...views import ModelViewSet
from ..models import Class
from ..permissions import InSchool, IsTeacher
from ..serializers import ClassSerializer


# pylint: disable-next=missing-class-docstring,too-many-ancestors
class ClassViewSet(ModelViewSet[Class]):
    http_method_names = ["get"]
    lookup_field = "access_code"
    serializer_class = ClassSerializer

    def get_permissions(self):
        # Only school-teachers can list classes.
        if self.action == "list":
            return [IsTeacher(), InSchool()]

        return [InSchool()]

    # pylint: disable-next=missing-function-docstring
    def get_queryset(self):
        user = self.request_user
        if user.student:
            return Class.objects.filter(students=user.student)

        user = self.request_school_teacher_user
        if user.teacher.is_admin:
            return Class.objects.filter(teacher__school=user.teacher.school)

        return Class.objects.filter(teacher=user.teacher)
