from django.contrib.auth.models import AbstractUser
from uuid import uuid4
from django.db import models
from datetime import timedelta
from django.utils import timezone
from django_countries.fields import CountryField



class CFL_User(AbstractUser): # I did not know how to call this class, so I called it CFL_User
    developer = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    # This is a string showing which badges in which worksheets have been earned. The format is "X:Y" where X is the
    # worksheet ID and Y is the badge ID. This repeats for all badges and each pair is comma-separated.
    # aimmo_badges = models.CharField(max_length=200, null=True, blank=True) this should be moved to aimmo model PlayerProfile

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def joined_recently(self):
        now = timezone.now()
        return now - timedelta(days=7) <= self.date_joined

class SchoolModelManager(models.Manager):
    # Filter out inactive schools by default
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class School(models.Model):
    name = models.CharField(max_length=200)
    postcode = models.CharField(max_length=10, null=True)
    country = CountryField(blank_label="(select country)")
    creation_time = models.DateTimeField(default=timezone.now, null=True)
    is_active = models.BooleanField(default=True)

    objects = SchoolModelManager()

    def __str__(self):
        return self.name

    def classes(self):
        teachers = self.school_teacher.all()
        if teachers:
            classes = []
            for teacher in teachers:
                if teacher.class_teacher.all():
                    classes.extend(list(teacher.class_teacher.all()))
            return classes
        return None

    def admins(self):
        teachers = self.school_teacher.all()
        return [teacher for teacher in teachers if teacher.is_admin] if teachers else None

    def anonymise(self):
        self.name = uuid4().hex
        self.postcode = ""
        self.is_active = False
        self.save()


class TeacherModelManager(models.Manager):
    def factory(self, first_name, last_name, email, password):
        cfl_user = CFL_User.objects.create_user(
            username=email, email=email, password=password, first_name=first_name, last_name=last_name
        )


        return Teacher.objects.create(cfl_user=cfl_user)

    # Filter out non active teachers by default
    def get_queryset(self):
        return super().get_queryset().filter(cfl_user__is_active=True)


class Teacher(models.Model):
    cfl_user = models.OneToOneField(CFL_User, related_name="teacher", null=True, blank=True, on_delete=models.CASCADE)
    school = models.ForeignKey(School, related_name="school_teacher", null=True, blank=True, on_delete=models.SET_NULL)
    is_admin = models.BooleanField(default=False)
    blocked_time = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        "self", related_name="invited_teachers", null=True, blank=True, on_delete=models.SET_NULL
    )

    objects = TeacherModelManager()

    def teaches(self, userprofile):
        if hasattr(userprofile, "student"):
            student = userprofile.student
            return not student.is_independent() and student.class_field.teacher == self

    def has_school(self):
        return self.school is not (None or "")

    def has_class(self):
        return self.class_teacher.exists()

    def __str__(self):
        return f"{self.cfl_user.first_name} {self.cfl_user.last_name}"


class SchoolTeacherInvitationModelManager(models.Manager):
    # Filter out inactive invitations by default
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class SchoolTeacherInvitation(models.Model):
    token = models.CharField(max_length=32)
    school = models.ForeignKey(School, related_name="teacher_invitations", null=True, on_delete=models.SET_NULL)
    from_teacher = models.ForeignKey(Teacher, related_name="school_invitations", null=True, on_delete=models.SET_NULL)
    creation_time = models.DateTimeField(default=timezone.now, null=True)
    is_active = models.BooleanField(default=True)

    objects = SchoolTeacherInvitationModelManager()

    @property
    def is_expired(self):
        return self.expiry < timezone.now()

    def __str__(self):
        return f"School teacher invitation for {self.invited_teacher_email} to {self.school.name}"

    def anonymise(self):
        self.invited_teacher_first_name = uuid4().hex
        self.invited_teacher_last_name = uuid4().hex
        self.invited_teacher_email = uuid4().hex
        self.is_active = False
        self.save()


class ClassModelManager(models.Manager):
    def all_members(self, user):
        members = []
        if hasattr(user, "teacher"):
            members.append(user.teacher)
            if user.teacher.has_school():
                classes = user.teacher.class_teacher.all()
                for c in classes:
                    members.extend(c.students.all())
        else:
            c = user.student.class_field
            members.append(c.teacher)
            members.extend(c.students.all())
        return members

    # Filter out non active classes by default
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Class(models.Model):
    name = models.CharField(max_length=200)
    teacher = models.ForeignKey(Teacher, related_name="class_teacher", on_delete=models.CASCADE)
    access_code = models.CharField(max_length=5, null=True)
    classmates_data_viewable = models.BooleanField(default=False)
    always_accept_requests = models.BooleanField(default=False)
    accept_requests_until = models.DateTimeField(null=True)
    creation_time = models.DateTimeField(default=timezone.now, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        Teacher, null=True, blank=True, related_name="created_classes", on_delete=models.SET_NULL
    )

    objects = ClassModelManager()

    def __str__(self):
        return self.name

    @property
    def active_game(self):
        games = self.game_set.filter(game_class=self, is_archived=False)
        if len(games) >= 1:
            assert len(games) == 1  # there should NOT be more than one active game
            return games[0]
        return None

    def has_students(self):
        students = self.students.all()
        return students.count() != 0

    def get_requests_message(self):
        if self.always_accept_requests:
            external_requests_message = "This class is currently set to always accept requests."
        elif self.accept_requests_until is not None and (self.accept_requests_until - timezone.now()) >= timedelta():
            external_requests_message = (
                "This class is accepting external requests until "
                + self.accept_requests_until.strftime("%d-%m-%Y %H:%M")
                + " "
                + timezone.get_current_timezone_name()
            )
        else:
            external_requests_message = "This class is not currently accepting external requests."

        return external_requests_message

    def anonymise(self):
        self.name = uuid4().hex
        self.access_code = ""
        self.is_active = False
        self.save()

        # Remove independent students' requests to join this class
        self.class_request.clear()

    class Meta(object):
        verbose_name_plural = "classes"


class UserSession(models.Model):
    cfl_user = models.ForeignKey(CFL_User, on_delete=models.CASCADE)
    login_time = models.DateTimeField(default=timezone.now)
    school = models.ForeignKey(School, null=True, on_delete=models.SET_NULL)
    class_field = models.ForeignKey(Class, null=True, on_delete=models.SET_NULL)
    login_type = models.CharField(max_length=100, null=True)  # for student login

    def __str__(self):
        return f"{self.cfl_user} login: {self.login_time} type: {self.login_type}"


class StudentModelManager(models.Manager):
    def get_random_username(self):
        while True:
            random_username = uuid4().hex[:30]  # generate a random username
            if not CFL_User.objects.filter(username=random_username).exists():
                return random_username

    def schoolFactory(self, klass, name, password, login_id=None):
        cfl_user = CFL_User.objects.create_user(username=self.get_random_username(), password=password, first_name=name)

        return Student.objects.create(class_field=klass, cfl_user=cfl_user, login_id=login_id)

    def independentStudentFactory(self, name, email, password):
        cfl_user = CFL_User.objects.create_user(username=email, email=email, password=password, first_name=name)


        return Student.objects.create(cfl_user=cfl_user)


class Student(models.Model):
    class_field = models.ForeignKey(Class, related_name="students", null=True, blank=True, on_delete=models.CASCADE)
    # hashed uuid used for the unique direct login url
    login_id = models.CharField(max_length=64, null=True)
    cfl_user = models.OneToOneField(CFL_User, related_name="student", null=True, blank=True, on_delete=models.CASCADE)
    pending_class_request = models.ForeignKey(
        Class, related_name="class_request", null=True, blank=True, on_delete=models.SET_NULL
    )
    blocked_time = models.DateTimeField(null=True, blank=True)

    objects = StudentModelManager()

    def is_independent(self):
        return not self.class_field

    def __str__(self):
        return f"{self.cfl_user.first_name} {self.cfl_user.last_name}"


def stripStudentName(name):
    return re.sub("[ \t]+", " ", name.strip())


class AimmoCharacterManager(models.Manager):
    def sorted(self):
        return self.get_queryset().order_by("sort_order")


class AimmoCharacter(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    image_path = models.CharField(max_length=255)
    sort_order = models.IntegerField()
    alt = models.CharField(max_length=255, null=True)
    objects = AimmoCharacterManager()

    def __str__(self) -> str:
        return self.name


# -----------------------------------------------------------------------
# Below are models used for data tracking and maintenance
# -----------------------------------------------------------------------
class JoinReleaseStudent(models.Model):
    """
    To keep track when a student is released to be independent student or
    joins a class to be a school student.
    """

    JOIN = "join"
    RELEASE = "release"

    student = models.ForeignKey(Student, related_name="student", on_delete=models.CASCADE)
    # either "release" or "join"
    action_type = models.CharField(max_length=64)
    action_time = models.DateTimeField(default=timezone.now)


class DailyActivity(models.Model):
    """
    A model to record sets of daily activity. Currently used to record the amount of
    student details download clicks, through the CSV and login cards methods, per day.
    """

    date = models.DateField(default=timezone.now)
    csv_click_count = models.PositiveIntegerField(default=0)
    login_cards_click_count = models.PositiveIntegerField(default=0)
    primary_coding_club_downloads = models.PositiveIntegerField(default=0)
    python_coding_club_downloads = models.PositiveIntegerField(default=0)
    level_control_submits = models.PositiveBigIntegerField(default=0)
    teacher_lockout_resets = models.PositiveIntegerField(default=0)
    indy_lockout_resets = models.PositiveIntegerField(default=0)
    school_student_lockout_resets = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Daily activities"

    def __str__(self):
        return f"Activity on {self.date}: CSV clicks: {self.csv_click_count}, login cards clicks: {self.login_cards_click_count}, primary pack downloads: {self.primary_coding_club_downloads}, python pack downloads: {self.python_coding_club_downloads}, level control submits: {self.level_control_submits}, teacher lockout resets: {self.teacher_lockout_resets}, indy lockout resets: {self.indy_lockout_resets}, school student lockout resets: {self.school_student_lockout_resets}"


class DynamicElement(models.Model):
    """
    This model is meant to allow us to quickly update some elements dynamically on the website without having to
    redeploy everytime. For example, if a maintenance banner needs to be added, we check the box in the Django admin
    panel, edit the text and it'll show immediately on the website.
    """

    name = models.CharField(max_length=64, unique=True, editable=False)
    active = models.BooleanField(default=False)
    text = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name
