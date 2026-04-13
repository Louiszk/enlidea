from django.urls import path
from . import views

urlpatterns = [
    # social-api/
    path('follow/<int:user_id>/', views.follow_user, name='follow_user'),
    path('unfollow/<int:user_id>/', views.unfollow_user, name='unfollow_user'),
    path('home-feed/<int:user_id>', views.home_feed, name='home_feed'),
    path('follows/', views.get_follows, name='get_follows'),
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/mark-read/', views.mark_notifications_as_read, name='mark_notifications_as_read'),
    path('nodes/<int:node_id>/save/', views.save_node, name='save_node'),
    path('papers/<int:paper_id>/save/', views.save_paper, name='save_paper'),
    path('papers/<int:paper_id>/appreciate/', views.appreciate_paper, name='appreciate_paper'),
    path('leaderboard', views.leaderboard, name='leaderboard'),
    path('report/', views.report_content, name='report_content'),
    path('complaint/', views.submit_complaint, name='submit_complaint'),
]
