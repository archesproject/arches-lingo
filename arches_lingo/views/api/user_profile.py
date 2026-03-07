import json

import django.contrib.auth.password_validation as validation
from django.contrib.auth import authenticate, login
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.debug import (
    sensitive_post_parameters,
    sensitive_variables,
)
from django.views.generic import View

from arches.app.models import models
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.const import LINGO_EDITOR_GROUP_NAME
from arches_lingo.permissions import (
    is_lingo_editor,
    anonymous_access_allowed,
)


class LingoUserView(View):
    """Returns the current user's basic info and editor status."""

    def get(self, request):
        user = request.user
        is_anonymous = not user.is_authenticated or user.username == "anonymous"

        return JSONResponse(
            {
                "username": user.username,
                "first_name": getattr(user, "first_name", ""),
                "last_name": getattr(user, "last_name", ""),
                "is_editor": is_lingo_editor(user),
                "is_anonymous": is_anonymous,
                "allow_anonymous_access": anonymous_access_allowed(),
            }
        )


class UserProfileAPIView(View):
    """JSON API for reading and updating the authenticated user's profile."""

    def get(self, request):
        user = request.user
        if not user.is_authenticated or user.username == "anonymous":
            return JSONErrorResponse(
                title=_("Not authenticated"),
                message=_("You must be logged in to view your profile."),
                status=401,
            )

        phone = ""
        try:
            phone = user.userprofile.phone or ""
        except models.UserProfile.DoesNotExist:
            pass

        return JSONResponse(
            {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone": phone,
            }
        )

    @method_decorator((sensitive_variables(), sensitive_post_parameters()))
    def put(self, request):
        user = request.user
        if not user.is_authenticated or user.username == "anonymous":
            return JSONErrorResponse(
                title=_("Not authenticated"),
                message=_("You must be logged in to update your profile."),
                status=401,
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JSONErrorResponse(
                title=_("Invalid request"),
                message=_("Request body must be valid JSON."),
                status=400,
            )

        first_name = data.get("first_name", user.first_name)
        last_name = data.get("last_name", user.last_name)
        email = data.get("email", user.email)
        phone = data.get("phone", "")

        errors = {}
        if not first_name:
            errors["first_name"] = _("First name is required.")
        if not last_name:
            errors["last_name"] = _("Last name is required.")
        if not email:
            errors["email"] = _("Email is required.")

        if errors:
            return JSONErrorResponse(
                title=_("Validation error"),
                message=json.dumps(errors),
                status=400,
            )

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        if not models.UserProfile.objects.filter(user=user).exists():
            models.UserProfile.objects.create(user=user)

        user.userprofile.phone = phone
        user.userprofile.save()

        return JSONResponse(
            {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone": phone,
            }
        )


class ChangePasswordAPIView(View):
    """JSON API for changing the authenticated user's password."""

    @method_decorator((sensitive_variables(), sensitive_post_parameters()))
    def post(self, request):
        user = request.user
        if not user.is_authenticated or user.username == "anonymous":
            return JSONErrorResponse(
                title=_("Not authenticated"),
                message=_("You must be logged in to change your password."),
                status=401,
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JSONErrorResponse(
                title=_("Invalid request"),
                message=_("Request body must be valid JSON."),
                status=400,
            )

        old_password = data.get("old_password", "")
        new_password = data.get("new_password", "")
        new_password2 = data.get("new_password2", "")

        if not user.check_password(old_password):
            return JSONErrorResponse(
                title=_("Invalid password"),
                message=_("Your current password is incorrect."),
                status=400,
            )

        if new_password != new_password2:
            return JSONErrorResponse(
                title=_("Password mismatch"),
                message=_("New password and confirmation must match."),
                status=400,
            )

        try:
            validation.validate_password(new_password, user)
        except ValidationError as val_err:
            return JSONErrorResponse(
                title=_("Password validation failed"),
                message=" ".join(val_err.messages),
                status=400,
            )

        user.set_password(new_password)
        user.save()
        authenticated_user = authenticate(username=user.username, password=new_password)
        login(request, authenticated_user)

        return JSONResponse({"success": _("Password successfully updated.")})
