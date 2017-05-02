from datetime import datetime, timedelta

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.postgres.search import SearchVector
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.views.generic.edit import FormMixin

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


class EventFilterFormMixin(FormMixin):

    form_class = GenericFilterForm

    def __init__(self, **kwargs):
        super(EventFilterFormMixin, self).__init__(**kwargs)

        # initial filter
        self.initial = {
            'from_date': datetime.today(),
            'to_date': (datetime.today() + timedelta(weeks=1))
        }

        # events
        self.event_list = Event.objects.filter(published=True).distinct()

    def apply_filter(self, form):

        form_data = form.clean()

        if 'search' in form_data and form_data.get('search'):
            self.event_list = self.event_list.annotate(
                search=SearchVector('calendar__title',
                                    'host__name', 'host__info',
                                    'title', 'location', 'address', 'city',
                                    'zip_code', 'description')
            ).filter(search=form_data.get('search'))

        self.event_list = self.event_list.filter(self.get_date_filter(
            form_data
        ))

        # filter the queryset by the selected groups
        groups = form.groups()
        if len(groups) > 0:
            self.event_list = self.event_list.filter(group__in=groups)

    def get(self, request, *args, **kwargs):

        form = self.get_form()

        if len(self.request.GET) and form.is_valid():
            self.apply_filter(form)
        else:
            self.event_list = self.event_list.filter(
                self.get_date_filter(self.initial)
            )

        self.event_list = self.event_list.order_by('recurring')
        context = self.get_context_data()

        return self.render_to_response(context)

    def get_date_filter(self, data):
        fdate = data.get('from_date', None)
        tdate = data.get('to_date', None)

        # this is needed a few times here
        def _to_datetime(date, min_or_max='min'):
            if min_or_max not in ['min', 'max']:
                raise ValueError('min_or_max has to be either "min" or "max"')
            _border = getattr(datetime, min_or_max, datetime.min)
            return datetime.combine(date, _border.time())

        # find the right filter
        if fdate is not None and tdate is not None:

            # recurrences requires a datetime object
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
            event_pk = [recurrence.event.pk
                        for recurrence in recurrences
                        if len(recurrence.recurrences.between(fdatetime,
                                                              tdatetime))]

            return (Q(recurring=False) & (
                    Q(eventtimedate__start_date__gte=fdate,
                      eventtimedate__start_date__lte=tdate,
                      eventtimedate__end_date__isnull=True) |
                    Q(eventtimedate__start_date__gte=fdate,
                      eventtimedate__end_date__gte=fdate,
                      eventtimedate__end_date__lte=tdate,
                      eventtimedate__end_date__isnull=False)) |
                    Q(pk__in=event_pk))

        elif tdate is not None:

            # convert the to date to a datetime object
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

            # convert the to date to a datetime object
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

    def paginate_qs(self, qs, prefix='paginator'):
        paginator = Paginator(qs, 10)

        page = self.request.GET.get('{0}_page'.format(prefix), 1)
        try:
            obj_list = paginator.page(page)
        except PageNotAnInteger:
            obj_list = paginator.page(1)
        except EmptyPage:
            obj_list = paginator.page(paginator.num_pages)

        return obj_list, paginator


class FilterFormMixin(EventFilterFormMixin):

    def __init__(self, **kwargs):
        super(FilterFormMixin, self).__init__(**kwargs)

        # proposals
        self.proposal_list = Event.objects.filter(published=False).distinct()

    def apply_filter(self, form):
        super(FilterFormMixin, self).apply_filter(form)

        self.proposal_list = self.proposal_list.filter(self.get_date_filter(
            form.clean()
        ))

        # filter the queryset by the selected groups
        groups = form.groups()
        if len(groups) > 0:
            self.proposal_list = self.proposal_list.filter(group__in=groups)

    def get(self, request, *args, **kwargs):
        super(FilterFormMixin, self).get(request, *args, **kwargs)

        if not len(request.GET):
            self.proposal_list = self.proposal_list.filter(
                self.get_date_filter(self.initial)
            )

        self.proposal_list = self.proposal_list.order_by('recurring')
        context = self.get_context_data()

        return self.render_to_response(context)
