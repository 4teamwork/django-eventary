from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.i18n import JavaScriptCatalog

from eventary.views import anonymous

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    # the javascript catalogue
    url(r'^jsi18n/$',
        JavaScriptCatalog.as_view(packages=['recurrence']),
        name='javascript-catalog'),

    # The eventary app urls
    url(r'^', include('eventary.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
