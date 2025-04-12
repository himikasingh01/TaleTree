from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('home/',views.home,name='home'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('generate/', views.generate_story, name='generate'),
    path('word-meaning/', views.word_meaning, name='word-meaning'),
    path('library/', views.story_library, name='story_library'),

]
