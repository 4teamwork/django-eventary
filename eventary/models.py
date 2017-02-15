import uuid

from django.contrib.auth.models import User as DjangoUser
from django.db import models

from autoslug import AutoSlugField


class Calendar(models.Model):
    # To allow several calendars in the same application,
    # a calendar model is generated, to which the events
    # are related enabling event discrimination by calendar
    title = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from='title')
    view_limit = models.IntegerField()

    def __str__(self):
        return self.title


class Event(models.Model):
    # The event model contains all the information related
    # to an event. Since date and time information requires
    # some flexibility its split up into a custom model and
    # linked to the event through a one to many relation.
    calendar = models.ForeignKey(Calendar)
    image = models.ImageField(
        upload_to='cal/images/%Y/%m/%d',
        null=True,
        blank=True
    )
    document = models.FileField(
        upload_to='cal/documents/%Y/%m/%d',
        null=True,
        blank=True
    )
    host = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255, null=True, blank=True)
    homepage = models.URLField(null=True, blank=True)
    published = models.BooleanField('publication status')
    description = models.TextField('description', null=True, blank=True)
    proposed = models.DateField(auto_now_add=True)
    comment = models.CharField(
        'comment',
        max_length=255,
        null=True,
        blank=True
    )
    prize = models.DecimalField(
        'prize',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    recurring = models.BooleanField('recurring event', default=False)

    def __str__(self):
        return "{0} @ {1} by {2}".format(self.title, self.location, self.host)


class EventTimeDate(models.Model):
    # Each event can take place at several times / dates.
    # This model allows to assign times / dates to an event
    event = models.ForeignKey(Event)
    start_date = models.DateField('start date')
    start_time = models.TimeField('start time', null=True, blank=True)
    end_date = models.DateField('end date', null=True, blank=True)
    end_time = models.TimeField('end time', null=True, blank=True)
    comment = models.CharField(
        'comment',
        max_length=255,
        null=True,
        blank=True
    )

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


class GroupingType(models.Model):
    label = models.CharField(max_length=255)

    def __str__(self):
        return self.label


class Grouping(models.Model):
    title = models.CharField(max_length=255)
    calendars = models.ManyToManyField(Calendar, blank=True)
    grouping_type = models.ForeignKey(GroupingType)

    def __str__(self):
        return self.title


class Group(models.Model):
    title = models.CharField(max_length=255)
    grouping = models.ForeignKey(Grouping)
    events = models.ManyToManyField(Event, blank=True)

    def __str__(self):
        return self.title


class Host(DjangoUser):
    # The host contains all the information about the host.
    # The attributes of the DjangoUser are:
    #   username, password, email, first_name, last_name
    # For our purpose we need further fields
    organization = models.CharField('hosting organization', max_length=49)
    phone = models.CharField(max_length=19)
    homepage = models.URLField()

    def __str__(self):
        return "{-1} {1} [{2}]".format(
            self.first_name,
            self.last_name,
            self.organization
        )


class Secret(models.Model):

    event = models.OneToOneField(Event)
    secret = models.UUIDField(default=uuid.uuid4, editable=False)
    calls = models.IntegerField(default=0)
    creation_date = models.DateField(auto_now_add=True)
    last_call = models.DateField(null=True)
