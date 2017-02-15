from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.db.models import Case, IntegerField, Sum, When
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic import ListView, TemplateView

from ..forms import CalendarForm, GenericFilterForm
from ..models import Calendar, Event, EventTimeDate


class CalendarCreateView(CreateView):

    form_class = CalendarForm
    model = Calendar
    template_name = 'eventary/management/create_calendar.html'

    def get_success_url(self):
        """Returns the user to the details view of the created calendar."""

        # todo: create a secret and create a link with 'n' previews per day
        return reverse(
            'eventary:anonymous-calendar_details',
            args=[self.object.pk]
        )


class CalendarDeleteView(DeleteView):

    model = Calendar
    template_name = 'eventary/management/delete_calendar.html'

    def get_success_url(self):
        return reverse('eventary:management-list_calendars')


class CalendarListView(ListView):

    model = Calendar
    template_name = 'eventary/management/list_calendars.html'

    def get_queryset(self):
        qs = super(CalendarListView, self).get_queryset()
        qs = qs.annotate(
            num_events=Sum(Case(When(
                event__published=True,
                then=1
            )), output_field=IntegerField(), distinct=True),
            num_proposals=Sum(Case(When(
                event__published=False,
                then=1
            )), output_field=IntegerField(), distinct=True),
        )
        return qs


class CalendarUpdateView(UpdateView):

    form_class = CalendarForm
    model = Calendar
    template_name = 'eventary/management/update_calendar.html'

    def get_success_url(self):
        return reverse('eventary:management-list_calendars')


class LandingView(TemplateView):

    template_name = 'eventary/management/landing.html'

    def filter_qs(self, qs):

        if self.form.is_valid():

            data = self.form.clean()

            # filter the queryset with the given date range / date
            if data['from_date'] is not None and data['to_date'] is not None:
                qs = qs.exclude(
                    eventtimedate__start_date__gte=data['to_date'],
                    eventtimedate__end_date__lte=data['from_date']
                )
            elif data['to_date'] is not None:
                qs = qs.exclude(eventtimedate__start_date__gte=data['to_date'])
            elif data['from_date'] is not None:
                qs = qs.exclude(eventtimedate__end_date__gt=data['from_date'])

            # filter the queryset by the selected groups
            groups = self.form.groups()
            if len(groups) > 0:
                qs = qs.filter(group__in=groups)

        return qs

    def get_context_data(self, **kwargs):
        context = super(LandingView, self).get_context_data(**kwargs)

        # general context data
        context.update({
            'calendar_list':  self.get_queryset(),
            'event_count':    Event.objects.filter(published=True).count(),
            'proposal_count': Event.objects.filter(published=False).count(),
            'timedate_count': EventTimeDate.objects.count()
        })

        # upcoming events and proposals
        event_list = Event.objects.filter(published=True).distinct()
        proposal_list = Event.objects.filter(published=False).distinct()

        # filter the events and proposals
        form = self.get_form()
        context.update({'form': form})
        event_list = self.filter_qs(event_list)
        proposal_list = self.filter_qs(proposal_list)

        # create some paginators
        event_list, event_paginator = self.paginate_qs(
            event_list,
            prefix='event'
        )
        proposal_list, proposal_paginator = self.paginate_qs(
            proposal_list,
            prefix='proposal'
        )

        context.update({
            'event_list':    event_list,
            'proposal_list': proposal_list
        })

        context.update({
            'event_paginator': event_paginator,
            'proposal_paginator': proposal_paginator
        })

        return context

    def get_form(self):
        if len(self.request.GET):
            self.form = GenericFilterForm(self.request.GET, prefix='filter')
        else:
            self.form = GenericFilterForm(prefix='filter')
        return self.form

    def get_queryset(self):
        qs = Calendar.objects.annotate(
            num_events=Sum(Case(When(
                event__published=True,
                then=1
            )), output_field=IntegerField(), distinct=True),
            num_proposals=Sum(Case(When(
                event__published=False,
                then=1
            )), output_field=IntegerField(), distinct=True),
        ).order_by()
        return qs

    def paginate_qs(self, qs, prefix='paginator'):
        paginator = Paginator(qs, 25)

        page = self.request.GET.get('{0}_page'.format(prefix), 1)
        try:
            obj_list = paginator.page(page)
        except PageNotAnInteger:
            obj_list = paginator.page(1)
        except EmptyPage:
            obj_list = paginator.page(paginator.num_pages)

        return obj_list, paginator
