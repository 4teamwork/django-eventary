from django.conf.urls import url

from .views import index, management, editorial, anonymous

app_name = 'eventary'

urlpatterns = [

    # redirects users to their landing page
    url(
        r'^$',
        index.UserRedirectView.as_view(),
        name='redirector'
    ),

    # admin views
    url(  # overview of all calendars
        r'^management/$',
        management.LandingView.as_view(),
        name='management-landing'
    ),
    url(  # lists all calendars
        r'^management/calendars/$',
        management.CalendarListView.as_view(),
        name='management-list_calendars'
    ),
    url(  # creates a new calendar
        r'^management/calendar/new/$',
        management.CalendarCreateView.as_view(),
        name='management-create_calendar'
    ),
    url(
        r'^management/cal_(?P<pk>[0-9]+)/delete/$',
        management.CalendarDeleteView.as_view(),
        name='management-delete_calendar'
    ),
    url(  # updates a calendar
        r'^management/cal_(?P<pk>[0-9]+)/update/$',
        management.CalendarUpdateView.as_view(),
        name='management-update_calendar'
    ),

    # editorial views
    url(  #
        r'^editorial/$',
        editorial.LandingView.as_view(),
        name='editorial-landing'
    ),
    url(  # list all calendars
        r'^editorial/calendars/$',
        editorial.CalendarListView.as_view(),
        name='editorial-list_calendars'
    ),
    url(  # lists all proposals
        r'^cal_(?P<pk>[0-9]+)/proposals/$',
        editorial.ProposalListView.as_view(),
        name='editorial-list_proposals'
    ),
    url(  # delete an event
        r'^cal_(?P<calendar_pk>[0-9]+)/evt_(?P<pk>[0-9]+)/delete/$',
        editorial.EventDeleteView.as_view(),
        name='editorial-delete_event'
    ),
    url(  # edits an event
        r'^cal_(?P<calendar_pk>[0-9]+)/evt_(?P<pk>[0-9]+)/update/$',
        editorial.EventEditWizardView.as_view(),
        name='editorial-update_event'
    ),
    url(  # hides an event
        r'^cal_(?P<calendar_pk>[0-9]+)/evt_(?P<pk>[0-9]+)/hide/$',
        editorial.EventHideView.as_view(),
        name='editorial-hide_event'
    ),
    url(  # approves an event
        r'^cal_(?P<calendar_pk>[0-9]+)/evt_(?P<pk>[0-9]+)/publish/$',
        editorial.EventPublishView.as_view(),
        name='editorial-publish_event'
    ),
    url(  # approves several events
        r'cal_(?P<pk>[0-9]+)/editorial/$',
        editorial.EventListUpdateView.as_view(),
        name='editorial-update_event_list'
    ),

    # anonymous views
    url(  # landing page
        r'^anonymous/$',
        anonymous.LandingView.as_view(),
        name='anonymous-landing'
    ),
    url(  # shows a calendar's details
        r'^cal_(?P<pk>[0-9]+)/$',
        anonymous.CalendarDetailView.as_view(),
        name='anonymous-calendar_details'
    ),
    url(  # creates a new proposal
        r'cal_(?P<pk>[0-9]+)/new/$',
        anonymous.EventCreateWizardView.as_view(),
        name='anonymous-create_event'
    ),
    url(  # detailed event view
        r'cal_(?P<calendar_pk>[0-9]+)/evt_(?P<pk>[0-9]+)/$',
        anonymous.EventDetailView.as_view(),
        name='anonymous-event_details'
    ),
    url(  # detailed view of a proposal
        r'cal_(?P<calendar_pk>[0-9]+)/prop_(?P<pk>[0-9]+)/(?P<secret>[0-9a-f\-]{36})/$',
        anonymous.ProposalDetailView.as_view(),
        name='anonymous-proposal_details'
    ),
    url(  # exports an event to ics
        r'^cal_(?P<calendar_pk>[0-9]+)/evt_(?P<pk>[0-9]+).ics$',
        anonymous.EventICSExportView.as_view(),
        name='anonymous-export_event_to_ics'
    ),
    url(  # when viewing a secret url too many times
        r'^too_many_views/$',
        anonymous.TooManyViewsView.as_view(),
        name='anonymous-too_many_views'
    )
]
