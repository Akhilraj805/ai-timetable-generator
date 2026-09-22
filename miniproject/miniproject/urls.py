from django.contrib import admin
from django.urls import path
from miniproject.scheduler import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('generate/', views.generate, name='generate'),
    path('teacher-availability/', views.teacher_availability_view, name='teacher_availability'),
    path('api/teacher-availability/', views.teacher_availability_api, name='teacher_availability_api'),
]
