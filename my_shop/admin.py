from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin

# Настраиваем отображение пользователей
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

# Перерегистрируем модели
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Убираем группу из админки (опционально)
admin.site.unregister(Group)

# Настраиваем заголовки
admin.site.site_header = 'Панель управления магазином'
admin.site.site_title = 'Администрирование'
admin.site.index_title = 'Добро пожаловать в панель управления'