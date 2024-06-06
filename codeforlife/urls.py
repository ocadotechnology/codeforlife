"""
© Ocado Group
Created on 12/04/2024 at 14:42:20(+01:00).
"""

import typing as t

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.http import HttpResponse
from django.urls import URLPattern, URLResolver, include, path, re_path
from rest_framework import status

from .settings import SERVICE_IS_ROOT, SERVICE_NAME
from .views import csrf

UrlPatterns = t.List[t.Union[URLResolver, URLPattern]]


def get_urlpatterns(
    api_urls_path: str = "src.api.urls",
    include_user_urls: bool = True,
) -> UrlPatterns:
    """Generate standard url patterns for each service.

    Args:
        api_urls_path: The path to the api's urls.
        include_user_urls: Whether or not to include the CFL's user urls.

    Returns:
        The standard url patterns for each service.
    """

    urlpatterns: UrlPatterns = [
        path(
            "admin/",
            admin.site.urls,
            name="admin",
        ),
        path(
            "api/csrf/cookie/",
            csrf.CookieView.as_view(),
            name="get-csrf-cookie",
        ),
        path(
            "api/session/logout/",
            LogoutView.as_view(),
            name="logout",
        ),
        # Django's default behavior with the @login_required decorator is to
        # redirect users to the login template found in setting LOGIN_URL.
        # Because we're using a React frontend, we want to return a
        # 401-Unauthorized whenever a user's session-cookie expires so we can
        # redirect them to the login page. Therefore, all login redirects will
        # direct to this view which will return the desired 401.
        path(
            "api/session/expired/",
            lambda request: HttpResponse(
                status=status.HTTP_401_UNAUTHORIZED,
            ),
            name="session-expired",
        ),
        path(
            "api/",
            include(api_urls_path),
            name="api",
        ),
    ]

    if include_user_urls:
        urlpatterns.append(
            path(
                "api/",
                include("codeforlife.user.urls"),
                name="user",
            )
        )

    if SERVICE_IS_ROOT:
        return urlpatterns

    return [
        path(
            f"{SERVICE_NAME}/",
            include(urlpatterns),
            name="service",
        ),
        re_path(
            rf"^(?!{SERVICE_NAME}/).*",
            lambda request: HttpResponse(
                f'The base route is "{SERVICE_NAME}/".',
                status=status.HTTP_404_NOT_FOUND,
            ),
            name="service-not-found",
        ),
    ]
