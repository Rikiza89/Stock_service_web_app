# stock_service/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def filter_is_society_admin(users_queryset, is_admin_status):
    """
    Filters a queryset of users based on their is_society_admin status.
    Usage: {{ users|filter_is_society_admin:True }}
    """
    # This filter expects a QuerySet and will return a filtered QuerySet,
    # then you can apply .count() or .length (for list) in the template.
    if isinstance(users_queryset, models.query.QuerySet):
        return users_queryset.filter(is_society_admin=is_admin_status)
    return [user for user in users_queryset if user.is_society_admin == is_admin_status]