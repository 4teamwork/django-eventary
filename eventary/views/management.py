from django.core.urlresolvers import reverse
from django.db.models import Case, IntegerField, Sum, Q, When
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic import ListView, TemplateView

from ..forms import CalendarForm
from ..models import Calendar, Event, EventTimeDate

from .mixins import ManagementRequiredMixin, FilterFormMixin


class CalendarCreateView(ManagementRequiredMixin, CreateView):

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


class CalendarDeleteView(ManagementRequiredMixin, DeleteView):

    model = Calendar
    template_name = 'eventary/management/delete_calendar.html'

    def get_success_url(self):
        return reverse('eventary:management-list_calendars')


class CalendarListView(ManagementRequiredMixin, ListView):

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


class CalendarUpdateView(ManagementRequiredMixin, UpdateView):

    form_class = CalendarForm
    model = Calendar
    template_name = 'eventary/management/update_calendar.html'

    def get_success_url(self):
        return reverse('eventary:management-list_calendars')


class LandingView(ManagementRequiredMixin, FilterFormMixin, TemplateView):

    template_name = 'eventary/management/landing.html'

    def get_context_data(self, **kwargs):
        context = super(LandingView, self).get_context_data(**kwargs)

        # general context data
        context.update({
            'calendar_list':  self.get_queryset(),
            'event_count':    Event.objects.filter(published=True).count(),
            'proposal_count': Event.objects.filter(published=False).count(),
            'timedate_count': EventTimeDate.objects.count()
        })

        # create some paginators
        event_page, event_paginator = self.paginate_qs(
            self.event_list,
            prefix='event'
        )
        proposal_page, proposal_paginator = self.paginate_qs(
            self.proposal_list,
            prefix='proposal'
        )

        context.update({'event_page': event_page,
                        'event_list': self.event_list,
                        'proposal_page': proposal_page,
                        'proposal_list': self.proposal_list,
                        'event_paginator': event_paginator,
                        'proposal_paginator': proposal_paginator})

        return context

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
