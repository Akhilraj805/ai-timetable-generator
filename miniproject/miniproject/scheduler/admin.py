from django.contrib import admin

from .models import Class, Teacher, Subject, Lab, TeacherAvailability


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("teacher_id", "teacher_name", "designation")
    search_fields = ("teacher_name", "designation")


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("class_id", "class_name", "semester")
    search_fields = ("class_name",)
    list_filter = ("semester",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("subject_id", "subject_name", "subject_type", "semester", "class_ref")
    search_fields = ("subject_name",)
    list_filter = ("subject_type", "semester", "class_ref")


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ("lab_id", "lab_name", "room")
    search_fields = ("lab_name", "room")


@admin.register(TeacherAvailability)
class TeacherAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("teacher", "day", "period", "is_available")
    list_filter = ("teacher", "day", "is_available")
    search_fields = ("teacher__teacher_name",)

