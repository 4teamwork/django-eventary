import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


setup(
    name='django-eventary',
    version='1.1.1',
    packages=find_packages(),
    include_package_data=True,
    license='GPLv2',
    description='A calendar for events',
    long_description=README,
    url='https://github.com/4teamwork/eventary',
    author='Pablo Vergés',
    author_email='pablo.verges@4teamwork.ch',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GPLv2',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=[
        'Django',
        'django-appconf',
        'django-autoslug',
        'django-bootstrap-themes',
        'django-bootstrap3-datetimepicker',
        'django_compressor',
        'django-forms-bootstrap',
        'django-formtools',
        'django-imagekit',
        'django-jquery',
        'django-recurrence',
        'django-searchable-select',
        'Django-Select2',
        'olefile',
        'Pillow',
        'psycopg2',
        'python-slugify',
        'requests',
        'Unidecode',
    ],
)
