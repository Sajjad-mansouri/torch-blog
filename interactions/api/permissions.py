# interactions/permissions.py
from rest_framework import permissions


class IsCommentOwnerOrEditor(permissions.BasePermission):
    """
    Object-level permission for comment editing/deletion.
    Owner or editor only.
    """

    message = "You do not have permission to modify this comment."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_editor:
            return True
        return obj.author == request.user


class IsCommentOwner(permissions.BasePermission):
    """
    Only the owner can edit their comment (editors cannot edit
    other users' comments, only delete them for moderation).
    """

    message = "You can only edit your own comments."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return obj.author == request.user
