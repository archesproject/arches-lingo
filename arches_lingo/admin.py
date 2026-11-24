from django.contrib import admin

from arches_lingo.models import MatchLinkImport


@admin.register(MatchLinkImport)
class MatchLinkImportAdmin(admin.ModelAdmin):
    """A read-only audit view: an import records what happened, so it is
    never created or edited here."""

    list_display = (
        "pk",
        "filename",
        "user",
        "status",
        "link_count",
        "created",
        "finished",
        "edit_transaction_id",
    )
    list_filter = ("status", "error_code")
    search_fields = ("filename", "user__username", "edit_transaction_id")
    date_hierarchy = "created"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
