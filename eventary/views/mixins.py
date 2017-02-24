from django.contrib.auth.mixins import PermissionRequiredMixin


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
