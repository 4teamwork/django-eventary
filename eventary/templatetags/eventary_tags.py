import html

from django import template
from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Page
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from ..models import Calendar, Event

register = template.Library()


def __get_user_group(user):

    if not isinstance(user, User):
        TypeError('value needs to be of type django.contrib.auth.models.User')

    groups = user.groups.filter(name__contains='eventary_')
    number_of_groups = groups.count()

    if number_of_groups == 1:
        # get the group the user is in
        group = groups.first().name.split('eventary_')[1]
    elif number_of_groups > 1:
        raise RuntimeError("User belongs to several eventary groups!")
    else:
        group = 'anonymous'

    return group


#  Filters

@register.filter(name='actions')
def actions(value, user=None):

    _group = __get_user_group(user)

    if isinstance(value, Calendar):
        return render_to_string(
            'eventary/actions/calendars_{group_name}.html'.format(
                group_name=_group
            ),
            context={'calendar': value}
        )

    if isinstance(value, Event):
        if value.published:
            return render_to_string(
                'eventary/actions/events_{group_name}.html'.format(
                    group_name=_group
                ),
                context={'event': value}
            )
        else:
            return render_to_string(
                'eventary/actions/proposals_{group_name}.html'.format(
                    group_name=_group
                ),
                context={'event': value}
            )

    if isinstance(value, Page) and value.object_list.model is Event:
        if value.object_list.first().published:
            return render_to_string(
                'eventary/actions/event_list_{group_name}.html'.format(
                    group_name=_group
                ),
            )
        else:
            return render_to_string(
                'eventary/actions/proposal_list_{group_name}.html'.format(
                    group_name=_group
                ),
            )


@register.filter(name='eventary_auth_group')
def eventary_auth_group(user):
    group = __get_user_group(user)
    return ' '.join(group.split('_'))


@register.filter(name='to_full_date')
def full_date(event):
    results = []
    if isinstance(event, Event):

        timedate = event.eventtimedate

        if event.recurring and getattr(event, 'eventrecurrence', False):

            if (timedate.end_date is not None and
                timedate.end_date != timedate.start_date):

                # generally, the start format is just the day, but we
                # might change it if some of the values do not coincide
                startformat = "%d.%m."
                if timedate.start_date.year != timedate.end_date.year:
                    startformat += "%Y"

                results.append("{0} - {2}, {1} - {3}".format(
                    timedate.start_date.strftime(startformat),
                    (timedate.start_time and
                     timedate.start_time.strftime(" %H:%M") or ''),
                    timedate.end_date.strftime("%d.%m.%Y"),
                    (timedate.end_time and
                     timedate.end_time.strftime(" %H:%M") or '')
                ))
            else:
                results.append("{0}{1}{2}".format(
                    timedate.start_date.strftime("%d.%m.%Y"),
                    (timedate.start_time and
                     timedate.start_time.strftime(" %H:%M") or ''),
                    (timedate.end_time and
                     timedate.end_time.strftime(" - %H:%M") or '')
                ))

            # now append the recursion information to the last entry
            results.append("{0} {1} {2}".format(
                event.eventtimedate.end_date is None and _('from') or '',
                results.pop(),
                ', '.join([
                    rule.to_text()
                    for rule in event.eventrecurrence.recurrences.rrules
                ])
            ))

        else:

            if (timedate.end_date is not None and
                timedate.end_date != timedate.start_date):

                # generally, the start format is just the day, but we
                # might change it if some of the values do not coincide
                startformat = "%d.%m."
                if timedate.start_date.year != timedate.end_date.year:
                    startformat += "%Y"

                results.append("{0}{1} - {2}{3}".format(
                    timedate.start_date.strftime(startformat),
                    (timedate.start_time and
                        timedate.start_time.strftime(" %H:%M") or ''),
                    timedate.end_date.strftime("%d.%m.%Y"),
                    (timedate.end_time and
                        timedate.end_time.strftime(" %H:%M") or '')
                ))
            else:
                results.append("{0}{1}{2}".format(
                    timedate.start_date.strftime("%d.%m.%Y"),
                    (timedate.start_time and
                        timedate.start_time.strftime(" %H:%M") or ''),
                    (timedate.end_time and
                        timedate.end_time.strftime(" - %H:%M") or '')
                ))

    return len(results) and ", ".join(results) or ""


@register.filter(name='dates')
def dates(event):
    results = []
    if isinstance(event, Event):

        timedate = event.eventtimedate

        if (timedate.end_date is not None and
            timedate.end_date != timedate.start_date):

            # generally, the start format is just the day, but we
            # might change it if some of the values do not coincide
            startformat = "%d.%m."
            if timedate.start_date.year != timedate.end_date.year:
                startformat += "%Y"

            results.append("{0} - {1}".format(
                timedate.start_date.strftime(startformat),
                timedate.end_date.strftime("%d.%m.%Y"),
            ))
        else:
            results.append(timedate.start_date.strftime("%d.%m.%Y"))

    return len(results) and ", ".join(results) or ""


@register.filter(name='times')
def times(event):
    results = []
    if isinstance(event, Event):

        timedate = event.eventtimedate

        if (timedate.end_time is not None and
            timedate.end_time != timedate.start_time):

            results.append("{0} - {1}".format(
                timedate.start_time.strftime("%H:%M"),
                timedate.end_time.strftime("%H:%M"),
            ))
        elif timedate.start_time is not None:
            results.append(timedate.start_time.strftime("%H:%M"))

    return len(results) and ", ".join(results) or ""


@register.filter(name='recursion')
def recursion(event):
    results = []
    if isinstance(event, Event):
        if event.recurring:
            results.append(', '.join([
                rule.to_text()
                for rule in event.eventrecurrence.recurrences.rrules
            ]))

    return len(results) and ", ".join(results) or ""


@register.filter(name='join')
def join(value, arg):
    return str(arg).join([
        getattr(g, 'title', str(g)) for g in value
    ])


@register.filter(name='media')
def media(form, media_type):
    if form is None:
        return []
    if media_type=='js':
        return form.media.render_js()
    if media_type=='css':
        return form.media.render_css()


@register.filter(name='navigation')
def navigation(user):
    _group = __get_user_group(user)
    return render_to_string(
        'eventary/navigation/{group_name}.html'.format(group_name=_group),
        context={'user': user},
    )


@register.filter(name='pick')
def pick(page, nr_picks=10):
    num_pages = page.paginator.num_pages
    nr_picks = min(num_pages, nr_picks)
    page_number = page.number
    coefficient = num_pages < nr_picks and 1 or num_pages // nr_picks
    return sorted(set([
        (i + 1) * coefficient
        for i in range(nr_picks)
    ] + [page_number]))


@register.filter(name='to_rrule')
def to_rrule(recurrence):
    return ';'.join([str(rrule.to_dateutil_rrule()).split('\n')[-1]
                     for rrule in recurrence.recurrences.rrules])


@register.filter(name='unescape')
def unescape(text):
    return html.unescape(text)


#  Tags

@register.simple_tag
def google_maps_api_key():
    """Returns the api key for google maps"""
    return getattr(settings, 'GOOGLE_MAPS_API_KEY', '')


@register.simple_tag
def page_navigation(page, request, key='page'):
    """Renders a paginator (page navigation)"""
    return render_to_string(
        'eventary/pagination.html',
        context={'key': key,
                 'page': page,
                 'paginator': page.paginator,
                 'request': request}
    )


@register.simple_tag
def url_replace(request, field, value):
    """Replaces a specific GET parameter"""
    _dict = request.GET.copy()
    _dict[field] = value
    return _dict.urlencode()


@register.simple_tag
def wizard_status(wizard, named_steps, valid_steps=[], form_id="wizardform"):
    """Renders a paginator (page navigation)"""
    return render_to_string('eventary/wizard_status.html',
                            context={'wizard': wizard,
                                     'named_steps': named_steps,
                                     'valid_steps': valid_steps,
                                     'form_id': form_id})


@register.simple_tag
def wizard_buttons(wizard):
    """Renders a paginator (page navigation)"""
    return render_to_string('eventary/wizard_buttons.html',
                            context={'wizard': wizard})
