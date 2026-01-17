from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('generate/', views.generate_resume, name='generate_resume'),
    path('download/', views.download_pdf, name='download_pdf'),
]
