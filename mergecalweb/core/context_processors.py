from mergecalweb.core.utils import get_site_url


def site_url(request):
    return {"site_url": get_site_url()}
