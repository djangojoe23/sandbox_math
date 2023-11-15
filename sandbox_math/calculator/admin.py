from django.contrib import admin

from sandbox_math.calculator.models import Content, Response, UserMessage


# Register your models here.
@admin.register(UserMessage)
class UserMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "sandbox", "problem_id", "timestamp"]
    search_fields = ["id"]


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ["id", "user_message_id", "context", "timestamp"]
    search_fields = ["user_message_id"]


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ["id", "content_type", "content"]
    search_fields = ["id"]
