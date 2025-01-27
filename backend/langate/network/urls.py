"""url for network"""
from django.urls import path

from . import views

urlpatterns = [
    path("devices/", views.DeviceList.as_view(), name="device-list"),
    path("userdevices/", views.UserDeviceList.as_view(), name="user-devices"),
    path("devices/<int:pk>/", views.DeviceDetail.as_view(), name="device-detail"),
    path("devices/whitelist/", views.DeviceWhitelist.as_view(), name="device-whitelist"),
    path("marks/", views.MarkList.as_view(), name="mark-list"),
    path("mark/<int:old>/move/<int:new>/", views.MarkMove.as_view(), name="mark-move"),
    path("mark/<int:old>/spread/", views.MarkSpread.as_view(), name="mark-spread"),
    path("games/", views.GameList.as_view(), name="game-list"),
    path("userdevices/<int:pk>/", views.UserDeviceDetail.as_view(), name="user-device-detail"),
    path("metrics/", views.Metrics.as_view(), name="metrics"),
]
