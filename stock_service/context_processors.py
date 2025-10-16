# stock_service/context_processors.py
from .models import SocietyUser

def society_context(request):
    """Add society information to template context"""
    context = {
        'user_society': None,
        'is_society_admin': False,
    }
    
    if request.user.is_authenticated:
        society_user = SocietyUser.objects.filter(user=request.user).first()
        if society_user:
            context['user_society'] = society_user.society
            context['is_society_admin'] = society_user.is_society_admin
    
    return context