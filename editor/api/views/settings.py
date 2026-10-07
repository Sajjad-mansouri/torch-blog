# editor/views_settings.py
from rest_framework import generics
from rest_framework.response import Response

from blog.api.permissions import IsEditor
from core.api.serializers import SiteSettingsSerializer
from core.models import SiteSettings


class EditorSiteSettingsView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/editor/settings/
    PATCH /api/v1/editor/settings/
    """

    permission_classes = [IsEditor]
    serializer_class = SiteSettingsSerializer

    def get_object(self):
        return SiteSettings.get()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
