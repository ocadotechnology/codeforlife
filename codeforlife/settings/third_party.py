"""
This file contains custom settings defined by third party extensions.
"""

from .django import DEBUG

# CORS
# https://pypi.org/project/django-cors-headers/

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = ["https://www.codeforlife.education"]

# REST framework
# https://www.django-rest-framework.org/api-guide/settings/#settings

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend"
    ],
    "DEFAULT_PAGINATION_CLASS": "codeforlife.pagination.LimitOffsetPagination",
    "DEFAULT_THROTTLE_CLASSES": [
        "codeforlife.user.throttles.AnonBurstRateThrottle",
        "codeforlife.user.throttles.BurstRateThrottle",
        "codeforlife.user.throttles.AnonSustainedRateThrottle",
        "codeforlife.user.throttles.SustainedRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon_burst": "60/min",
        "user_burst": "120/min",
        "anon_sustained": "10000/day",
        "user_sustained": "50000/day",
    },
}

# Django Extensions - Graph Models
# https://django-extensions.readthedocs.io/en/latest/graph_models.html?highlight=graph_models#default-settings

GRAPH_MODELS = {
    "all_applications": True,
    "group_models": True,
    "pygraphviz": True,
    "output": "docs/entity_relationship_diagram.png",
    "arrow_shape": "normal",
    "color_code_deletions": True,
    "rankdir": "BT",
}
