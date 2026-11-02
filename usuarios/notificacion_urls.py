from django.urls import path

from .notificacion_views import NotificacionDetailView, NotificacionListCreateView


urlpatterns = [
    path('notificaciones/', NotificacionListCreateView.as_view(), name='notificaciones-list-create'),
    path(
        'notificaciones/<str:notificacion_id>/',
        NotificacionDetailView.as_view(),
        name='notificaciones-detail',
    ),
]
