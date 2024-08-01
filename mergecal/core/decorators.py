from functools import wraps

from django.core.exceptions import PermissionDenied


def requires_htmx(view):
    @wraps(view)
    def _view(request, *args, **kwargs):
        if not request.htmx:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return _view
