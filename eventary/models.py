import os
import uuid

from django.db import models
from django.utils.text import slugify
from django.utils.translation import ugettext as _

from autoslug import AutoSlugField
from recurrence.fields import RecurrenceField

from .validators import validate_file_extension, validate_image_extension


def _get_upload_path(event, filename):
    return os.path.join(
        'calendar_{slug}'.format(slug=event.calendar.slug),
        'event_{slug}'.format(slug=event.slug),
        filename
    )


class Calendar(models.Model):
    # To allow several calendars in the same application,
    # a calendar model is generated, to which the events
    # are related enabling event discrimination by calendar
    title = models.CharField(max_length=255, verbose_name=_('title'))
    slug = AutoSlugField(populate_from='title', verbose_name=_('slug'))
    view_limit = models.IntegerField(help_text=_(
                                        'limits the number of daily anonymous '
                                        'views for proposed events'
                                     ),
                                     verbose_name=_('view limit'))

    def __str__(self):
        return self.title


class Event(models.Model):
    # The event model contains all the information related
    # to an event. Since date and time information requires
    # some flexibility its split up into a custom model and
    # linked to the event through a one to many relation.
    calendar = models.ForeignKey(Calendar, verbose_name=_('calendar'))
    host = models.ForeignKey('EventHost',
                             blank=True,
                             null=True,
                             verbose_name=_('host'))
    image = models.ImageField(blank=True,
                              max_length=255,
                              null=True,
                              upload_to=_get_upload_path,
                              validators=[validate_image_extension],
                              verbose_name=_('image'))
    document = models.FileField(blank=True,
                                max_length=255,
                                null=True,
                                upload_to=_get_upload_path,
                                validators=[validate_file_extension],
                                verbose_name=_('document'))
    title = models.CharField(max_length=255, verbose_name=_('title'))
    location = models.CharField(blank=True,
                                max_length=255,
                                null=True,
                                verbose_name=_('location'))
    homepage = models.URLField(blank=True,
                               null=True,
                               verbose_name=_('homepage'))
    published = models.BooleanField(help_text=_('publication status'),
                                    verbose_name=_('published'))
    description = models.TextField(blank=True,
                                   help_text=_('description'),
                                   null=True,
                                   verbose_name=_('description'))
    proposed = models.DateField(auto_now_add=True)
    comment = models.CharField(blank=True,
                               help_text=_('comment'),
                               max_length=255,
                               null=True,
                               verbose_name=_('comment'))
    prize = models.DecimalField(blank=True,
                                decimal_places=2,
                                help_text=_('prize'),
                                max_digits=6,
                                null=True,
                                verbose_name=_('prize'))
    recurring = models.BooleanField(default=False,
                                    help_text=_('recurring event'),
                                    verbose_name=_('recurring event'))

    def __str__(self):
        return "{0} @ {1} by {2}".format(self.title, self.location, self.host)

    def slug():
        def fget(self):
            return slugify(self.title)
        return locals()
    slug = property(**slug())


class EventTimeDate(models.Model):
    event = models.OneToOneField(Event, verbose_name=_('event'))
    start_date = models.DateField(help_text=_('start date'),
                                  verbose_name=_('start date'))
    start_time = models.TimeField(blank=True,
                                  help_text=_('start time'),
                                  null=True,
                                  verbose_name=_('start time'))
    end_date = models.DateField(blank=True,
                                help_text=_('end date'),
                                null=True,
                                verbose_name=_('end date'))
    end_time = models.TimeField(blank=True,
                                help_text=_('end time'),
                                null=True,
                                verbose_name=_('end time'))
    comment = models.CharField(blank=True,
                               help_text=_('comment'),
                               max_length=255,
                               null=True,
                               verbose_name=_('comment'))

    def __str__(self):

        # general case, when only a start date is set
        line = self.start_date.strftime('%x')

        # if the event spans over few days
        if (
            self.end_date is not None and
            self.end_date != self.start_date
        ):
            line = "{0} - {1}".format(
                self.start_date.strftime('%x'),
                self.end_date.strftime('%x')
            )

        # if the event spans over some time on the same day
        if (
            self.start_date == self.end_date and
            self.start_time is not None and
            self.end_time is not None
        ):
            line = "{0} {1} to {2}".format(
                line,
                self.start_time.strftime('%H:%M'),
                self.end_time.strftime('%H:%M')
            )

        return line


class EventRecurrence(models.Model):
    event = models.OneToOneField(Event, verbose_name=_('event'))
    recurrences = RecurrenceField()


class GroupingType(models.Model):
    label = models.CharField(max_length=255, verbose_name=_('label'))

    def __str__(self):
        return self.label


class Grouping(models.Model):
    title = models.CharField(max_length=255, verbose_name=_('title'))
    calendars = models.ManyToManyField(Calendar,
                                       blank=True,
                                       verbose_name=_('calendar'))
    grouping_type = models.ForeignKey(GroupingType,
                                      verbose_name=_('grouping type'))

    def __str__(self):
        return self.title


class Group(models.Model):
    title = models.CharField(max_length=255, verbose_name=_('title'))
    grouping = models.ForeignKey(Grouping, verbose_name=_('grouping'))
    events = models.ManyToManyField(Event,
                                    blank=True,
                                    verbose_name=_('events'))

    def __str__(self):
        return self.title


class EventHost(models.Model):
    # The host contains all the information about the host.
    # The attributes of the DjangoUser are:
    #   username, password, email, first_name, last_name
    # For our purpose we need further fields
    name = models.CharField(max_length=50, verbose_name=_('host name'))
    info = models.CharField(blank=True,
                            max_length=50,
                            null=True,
                            verbose_name=_('info'))
    phone = models.CharField(max_length=20, verbose_name=_('phone'))
    email = models.EmailField(blank=True, null=True, verbose_name=_('email'))
    homepage = models.URLField(blank=True,
                               null=True,
                               verbose_name=_('homepage'))


class Secret(models.Model):

    event = models.OneToOneField(Event, verbose_name=_('event'))
    secret = models.UUIDField(default=uuid.uuid4,
                              editable=False,
                              verbose_name=_('secret'))
    calls = models.IntegerField(default=0, verbose_name=_('calls'))
    creation_date = models.DateField(auto_now_add=True,
                                     verbose_name=_('creation date'))
    last_call = models.DateField(null=True,
                                 verbose_name=_('last call'))
