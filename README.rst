=====
Eventary
=====

Eventary is a simple Django inventary for events, ergo a calendar.

Quick start
-----------

1. Add "eventary" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'django-eventary',
    ]

2. Include the eventary URLconf in your project urls.py like this::

    url(r'^calendar/', include('eventary.urls')),

3. Run `python manage.py migrate` to create the polls models.

4. ???

5. Profit
