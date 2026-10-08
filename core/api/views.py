# core/views_landing.py
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from core.models import ContactMessage
from core.tasks import send_email_task

from .serializers_landing import (
    ApiEndpointSerializer,
    ContactMessageSerializer,
    FeatureGroupSerializer,
    ProjectInfoSerializer,
    RoadmapPhaseSerializer,
    ScreenshotSerializer,
    SocialLinkSerializer,
    StatisticSerializer,
    TechCategorySerializer,
)
from .services_landing import get_landing_data

# ============================================================
# Landing data
# ============================================================


class LandingView(APIView):
    """
    GET /api/v1/landing/

    Returns everything the landing page needs in one request:
    - project info
    - tech stack (grouped)
    - features (grouped)
    - API endpoints
    - screenshots
    - roadmap
    - stats
    - social links

    Cached for 10 minutes. Cache is invalidated when the editor
    updates settings or related models.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        data = get_landing_data()

        # If the data is a dict of model instances, serialize now.
        # If it's already a serialized dict (from cache), return it.
        if isinstance(data.get("project"), dict):
            # Already serialized (from cache)
            return Response(data)

        payload = {
            "project": ProjectInfoSerializer(
                data["project"], context={"request": request}
            ).data,
            "tech_stack": TechCategorySerializer(
                data["tech_stack"], many=True, context={"request": request}
            ).data,
            "features": FeatureGroupSerializer(
                data["features"], many=True, context={"request": request}
            ).data,
            "api_endpoints": ApiEndpointSerializer(
                data["api_endpoints"], many=True
            ).data,
            "screenshots": ScreenshotSerializer(
                data["screenshots"], many=True, context={"request": request}
            ).data,
            "roadmap": RoadmapPhaseSerializer(data["roadmap"], many=True).data,
            "stats": StatisticSerializer(data["stats"], many=True).data,
            "social_links": SocialLinkSerializer(data["social_links"], many=True).data,
        }
        return Response(payload)


# ============================================================
# Contact form
# ============================================================


class ContactThrottle(AnonRateThrottle):
    """
    5 contact submissions per hour per IP.
    """

    scope = "contact"
    rate = "5/hour"


def get_current_site_address(request):
    current_site = get_current_site(request)
    site_name = current_site.name
    protocol = "https" if request.is_secure() else "http"
    site_address = f"{protocol}://{current_site.domain}"
    return site_name, site_address


def message_feedback(request, name, user_email, message):
    site_name, site_address = get_current_site_address(request)
    kwargs = {
        "site_name": site_name,
        "site_address": site_address,
        "name": name,
        "email": user_email,
        "message": message,
    }
    if settings.HOST_ASYNC_ABILITY:
        send_email_task.delay(**kwargs)
    else:
        send_email_task(**kwargs)


class ContactView(generics.CreateAPIView):
    """
    POST /api/v1/contact/
    Body: {name, email, subject?, message, website? (honeypot)}

    Saves the message and returns a generic success response.
    Rate-limited to 5 requests per hour per IP.
    """

    permission_classes = [AllowAny]
    serializer_class = ContactMessageSerializer
    throttle_classes = [ContactThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Pop honeypot before saving
        data = dict(serializer.validated_data)
        data.pop("website", None)

        instance = ContactMessage.objects.create(
            **data,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
        )
        message_feedback(self.request, instance.name, instance.email, instance.message)
        return Response(
            {"detail": ("Thanks for your message. We'll get back to you soon.")},
            status=status.HTTP_201_CREATED,
        )

    def _get_client_ip(self, request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
