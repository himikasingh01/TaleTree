from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),       # 👈 Default route is now landing page
    path('login/', views.user_login, name='login'),      # 👈 Moved login to /login
    path('home/', views.home, name='home'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('generate/', views.generate_story, name='generate'),
    path('word-meaning/', views.word_meaning, name='word-meaning'),
    path('library/', views.story_library, name='story_library'),
    path('storybook/', views.storybook_view, name='show_storybook'),

]
