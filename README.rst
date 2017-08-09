=====
Eventary
=====

Eventary is a simple Django inventary for events, ergo a calendar.

Important
---------

Full text search requires a `postgresql` database.

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

Testing
-------

- Clone the git repo.
- Create a virtual env: `python3.6 -m venv venv`.
- Activate the virtual env: `source venv/bin/activate`.
- Install the testing requirements: `pip install -r requirements_test.txt`.
- Run the test: `pytest`.
- Optionally generate the coverage report: `pytest --cov=eventary --cov-report=html`
