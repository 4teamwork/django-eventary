from django.core.urlresolvers import reverse
from django.views.generic import RedirectView


class UserRedirectView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):

        groups = self.request.user.groups.filter(name__contains='eventary_')
        number_of_groups = groups.count()

        if number_of_groups == 1:
            # get the group the user is in
            group = groups.first().name.split('eventary_')[1]
        elif number_of_groups > 1:
            raise RuntimeError("User belongs to several eventary groups!")
        else:
            group = 'anonymous'

        return reverse('eventary:{group}-landing'.format(group=group))
