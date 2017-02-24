from django import template
from django.contrib.auth.models import User
from django.template.loader import render_to_string

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


@register.filter(name='eventary_auth_group')
def eventary_auth_group(user):
    group = __get_user_group(user)
    return ' '.join(group.split('_'))


@register.filter(name='to_full_date')
def full_date(value):
    results = []
    if isinstance(value, Event):
        timedates = value.eventtimedate_set.all()
        for timedate in timedates:

            if (
                timedate.end_date is not None and
                timedate.end_date != timedate.start_date
            ):

                # generally, the start format is just the day, but we
                # might change it if some of the values do not coincide
                startformat = "%d."
                if timedate.start_date.month != timedate.end_date.month:
                    startformat += "%m."
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


@register.filter(name='join')
def join(value, arg):
    return str(arg).join([
        getattr(g, 'title', str(g)) for g in value
    ])


@register.filter(name='navigation')
def navigation(user):
    _group = __get_user_group(user)
    return render_to_string(
        'eventary/navigation/{group_name}.html'.format(group_name=_group),
        context={'user': user},
    )


@register.simple_tag
def url_replace(request, field, value):
    """Replaces a specific GET parameter"""
    _dict = request.GET.copy()
    _dict[field] = value
    return _dict.urlencode()
