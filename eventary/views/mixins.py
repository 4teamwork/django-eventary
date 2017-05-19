from datetime import datetime, timedelta

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.postgres.search import SearchVector
from django.db.models import Q
from django.views.generic.edit import FormMixin
from django.views.generic.list import MultipleObjectMixin


from ..forms import GenericFilterForm
from ..models import Event, EventRecurrence


class ManagementRequiredMixin(PermissionRequiredMixin):

    def has_permission(self):
        return self.request.user.groups.filter(
            name='eventary_management'
        ).exists()


class EditorialOrManagementRequiredMixin(PermissionRequiredMixin):

    def has_permission(self):
        return self.request.user.groups.filter(name__in=[
            'eventary_editorial',
            'eventary_management'
        ]).exists()


class FilterFormMixin(MultipleObjectMixin, FormMixin):

    form_class = GenericFilterForm
    paginate_by = 10

    def __init__(self, **kwargs):
        super(FilterFormMixin, self).__init__(**kwargs)

        # initial date filter
        self.initial = {
            'from_date': datetime.today(),
            'to_date': (datetime.today() + timedelta(weeks=1))
        }

        self.event_list = Event.objects.filter(published=True).distinct()
        self.proposal_list = Event.objects.filter(published=False).distinct()

    def apply_filter(self, form, object_list):
        form_data = form.clean()

        # apply fulltext search
        if 'search' in form_data and form_data.get('search'):
            object_list = object_list.annotate(
                search=SearchVector('calendar__title',
                                    'host__name',
                                    'title', 'location', 'address', 'city',
                                    'entry_fee', 'zip_code', 'description',
                                    'group__title')
            ).filter(search=form_data.get('search'))

        # apply date filters
        object_list = object_list.filter(self.get_date_filter(
            form_data
        ))

        # filter the queryset by the selected groups
        groups = form.groups()
        if len(groups) > 0:
            object_list = object_list.filter(group__in=groups)

        return object_list

    def apply_order(self, object_list):
        return object_list.order_by('eventtimedate__start_date')

    def get(self, request, *args, **kwargs):
        form = self.get_form()

        if len(self.request.GET) and form.is_valid():
            self.event_list = self.apply_filter(form, self.event_list)
            self.proposal_list = self.apply_filter(form, self.proposal_list)
        else:
            date_filter = self.get_date_filter(self.initial)
            self.event_list = self.event_list.filter(date_filter)
            self.proposal_list = self.proposal_list.filter(date_filter)

        self.event_list = self.apply_order(self.event_list)
        self.proposal_list = self.apply_order(self.proposal_list)

        context = self.get_context_data()

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(MultipleObjectMixin, self).get_context_data(**kwargs)

        self.page_kwarg = 'event_page'
        self.object_list = self.event_list
        event_context = super(FilterFormMixin, self).get_context_data(**kwargs)

        self.page_kwarg = 'proposal_page'
        self.object_list = self.proposal_list
        proposal_context = super(FilterFormMixin, self).get_context_data(**kwargs)

        context.update({
            'event_page': event_context.get('page_obj'),
            'event_paginator': event_context.get('paginator'),
            'event_list': event_context.get('object_list'),
            'event_page_kwarg': 'event_page',
            'proposal_page': proposal_context.get('page_obj'),
            'proposal_paginator': proposal_context.get('paginator'),
            'proposal_list': proposal_context.get('object_list'),
            'proposal_page_kwarg': 'proposal_page',
        })

        return context

    def get_date_filter(self, data):
        fdate = data.get('from_date', None)
        tdate = data.get('to_date', None)

        def _to_datetime(date, min_or_max='min'):
            """
            Converts a date object into a datetime object
            if min_or_max is set to "min" it will return the smallest possible time
            if it is set to "max" it will return the greatest possible time
            """
            if min_or_max not in ['min', 'max']:
                raise ValueError('min_or_max has to be either "min" or "max"')
            _border = getattr(datetime, min_or_max, datetime.min)
            return datetime.combine(date, _border.time())

        if fdate is not None and tdate is not None:
            fdatetime = _to_datetime(fdate)
            tdatetime = _to_datetime(tdate, min_or_max='max')

            # find the the recurrences of the events in between 'from' and 'to'
            recurrences = EventRecurrence.objects.filter(
                Q(event__recurring=True) & (
                    # events with start and end dates
                    Q(event__eventtimedate__start_date__lte=tdate,
                      event__eventtimedate__end_date__gte=fdate,
                      event__eventtimedate__end_date__isnull=False) |
                    # events without end dates
                    Q(event__eventtimedate__start_date__lte=tdate,
                      event__eventtimedate__end_date__isnull=True)
                )
            )

            # now find all the events that have recurrences in the given span
            event_pks = [
                recurrence.event.pk
                for recurrence in recurrences
                if len(recurrence.recurrences.between(fdatetime, tdatetime))
            ]

            return (Q(recurring=False) & (
                    Q(eventtimedate__start_date__gte=fdate,
                      eventtimedate__start_date__lte=tdate,
                      eventtimedate__end_date__isnull=True) |
                    Q(eventtimedate__start_date__gte=fdate,
                      eventtimedate__end_date__gte=fdate,
                      eventtimedate__end_date__lte=tdate,
                      eventtimedate__end_date__isnull=False)) |
                    Q(pk__in=event_pks))

        elif tdate is not None:
            tdatetime = _to_datetime(tdate, 'max')

            # find all the recurrences before the given date
            recurrences = EventRecurrence.objects.filter(
                event__recurring=True,
                event__eventtimedate__start_date__lte=tdate,
            )

            # now find all events with occurrences in the given span
            event_pk = [
                recurrence.event.pk
                for recurrence in recurrences
                if len(recurrence.recurrences.between(
                    _to_datetime(recurrence.event.eventtimedate.start_date),
                    tdatetime
                ))
            ]

            return (Q(recurring=False) & (
                    Q(eventtimedate__start_date__lte=tdate,
                      eventtimedate__end_date__isnull=True) |
                    Q(eventtimedate__end_date__isnull=False,
                      eventtimedate__end_date__lte=tdate)) |
                    Q(pk__in=event_pk))
        elif fdate is not None:
            fdatetime = _to_datetime(fdate, 'min')

            # find all the recurrences before the given date
            recurrences = EventRecurrence.objects.filter(
                Q(event__recurring=True) & (
                    Q(event__eventtimedate__end_date__isnull=True) |
                    Q(event__eventtimedate__end_date__isnull=False,
                      event__eventtimedate__end_date__gte=fdate)
                )
            )

            # now find all events with occurrences in the given span
            event_pk = [
                recurrence.event.pk
                for recurrence in recurrences
                if recurrence.recurrences.after(fdatetime) is not None
            ]

            return (Q(recurring=False,
                      eventtimedate__start_date__gte=fdate) |
                    Q(pk__in=event_pk))

        return Q()

    def get_form(self):
        form_class = self.get_form_class()

        if len(self.request.GET):
            self.form = form_class(self.request.GET, prefix='filter')
        else:
            self.form = form_class(prefix='filter',
                                   initial=self.initial)
        return self.form
