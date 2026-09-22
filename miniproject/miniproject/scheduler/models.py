from django.db import models



# 1. CLASS MODEL

class Class(models.Model):
    class_id = models.AutoField(primary_key=True)
    class_name = models.CharField(max_length=50)
    semester = models.IntegerField()

    class Meta:
        db_table = 'classes'
        verbose_name_plural = 'Classes'

    def __str__(self):
        return f"{self.class_name} (Sem {self.semester})"


# 2. TEACHER MODEL

class Teacher(models.Model):
    teacher_id = models.AutoField(primary_key=True)
    teacher_name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'teachers'

    def __str__(self):
        return self.teacher_name



# 3. SUBJECT MODEL

class Subject(models.Model):
    SUBJECT_TYPE_CHOICES = [
        ('Theory', 'Theory'),
        ('Lab', 'Lab'),
    ]

    subject_id = models.AutoField(primary_key=True)
    subject_name = models.CharField(max_length=100)
    class_ref = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='subjects'
    )
    subject_type = models.CharField(
        max_length=10,
        choices=SUBJECT_TYPE_CHOICES,
        default='Theory'
    )
    semester = models.IntegerField(default=1)
    semester_type = models.CharField(max_length=4, default='Odd')

    class Meta:
        db_table = 'subjects'

    def __str__(self):
        return f"{self.subject_name} ({self.class_ref.class_name}) [{self.subject_type}]"


# 4. SUBJECT REQUIREMENT MODEL


class SubjectRequirement(models.Model):
    subject = models.OneToOneField(
        Subject,
        on_delete=models.CASCADE,
        related_name='requirement'
    )
    weekly_hours = models.IntegerField()

    class Meta:
        db_table = 'subject_requirements'

    def __str__(self):
        return f"{self.subject.subject_name} → {self.weekly_hours} hrs/week"


# 5. SUBJECT TEACHER MODEL

class SubjectTeacher(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='teachers'
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='subjects_taught'
    )

    class Meta:
        db_table = 'subject_teachers'
        unique_together = ('subject', 'teacher')

    def __str__(self):
        return f"{self.subject.subject_name} ← {self.teacher.teacher_name}"


# 6. LAB MODEL


class Lab(models.Model):
    lab_id = models.AutoField(primary_key=True)
    lab_name = models.CharField(max_length=100)
    room = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'labs'

    def __str__(self):
        return f"{self.lab_name}" + (f" ({self.room})" if self.room else "")


# 7. RESERVED SLOT MODEL


class ReservedSlot(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
    ]

    day = models.IntegerField(choices=DAY_CHOICES)
    hour = models.IntegerField()
    reason = models.CharField(max_length=200, blank=True, null=True)
    class_ref = models.ForeignKey(
        'Class',
        on_delete=models.CASCADE,
        related_name='reserved_slots',
        null=True,
    )

    class Meta:
        db_table = 'reserved_slots'
        unique_together = ('class_ref', 'day', 'hour')

    def __str__(self):
        return f"{self.get_day_display()} Hour {self.hour}" + (f" ({self.reason})" if self.reason else "")


# 8. TIMETABLE MODEL

class Timetable(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
    ]

    BLOCK_TYPE_CHOICES = [
        ('Subject', 'Subject'),
        ('Lab', 'Lab'),
        ('Reserved', 'Reserved'),
        ('Free', 'Free'),
    ]

    timetable_id = models.AutoField(primary_key=True)
    class_ref = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='timetable_entries'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timetable_entries'
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timetable_entries'
    )
    lab = models.ForeignKey(
        Lab,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timetable_entries'
    )
    day = models.IntegerField(choices=DAY_CHOICES)
    period = models.IntegerField()
    block_type = models.CharField(
        max_length=10,
        choices=BLOCK_TYPE_CHOICES,
        default='Free'
    )

    class Meta:
        db_table = 'timetable'
        unique_together = ('class_ref', 'day', 'period')
        ordering = ['class_ref', 'day', 'period']

    def __str__(self):
        day_name = self.get_day_display()
        if self.block_type == 'Subject' and self.subject:
            return f"{self.class_ref.class_name} | {day_name} P{self.period} → {self.subject.subject_name}"
        elif self.block_type == 'Lab' and self.lab:
            return f"{self.class_ref.class_name} | {day_name} P{self.period} → {self.lab.lab_name}"
        elif self.block_type == 'Reserved':
            return f"{self.class_ref.class_name} | {day_name} P{self.period} → Reserved"
        else:
            return f"{self.class_ref.class_name} | {day_name} P{self.period} → Free"


# 9. TEACHER AVAILABILITY MODEL

class TeacherAvailability(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
    ]

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='availability_slots'
    )
    day = models.IntegerField(choices=DAY_CHOICES)
    period = models.IntegerField()  # 0-based: 0..5
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = 'teacher_availability'
        unique_together = ('teacher', 'day', 'period')

    def __str__(self):
        status = "Available" if self.is_available else "Unavailable"
        return f"{self.teacher.teacher_name} | {self.get_day_display()} P{self.period + 1} → {status}"
