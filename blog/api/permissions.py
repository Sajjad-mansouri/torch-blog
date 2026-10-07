# blog/permissions.py
from rest_framework import permissions


class IsAuthor(permissions.BasePermission):
    """
    Allows access only to users with role 'author' or 'editor'.
    """

    message = "Only authors and editors can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.can_write_posts
        )


class IsEditor(permissions.BasePermission):
    """
    Allows access only to users with role 'editor'.
    """

    message = "Only editors can perform this action."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_editor


class IsOwnerOrEditor(permissions.BasePermission):
    """
    Object-level permission: the requesting user must be the
    owner of the object (author) or an editor.
    """

    message = "You do not have permission to modify this object."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_editor:
            return True

        # Determine "owner" based on the object type
        owner = getattr(obj, "author", None)
        if owner is None:
            owner = getattr(obj, "user", None)
        return owner == request.user


class IsAuthorOrEditorOrReadOnly(permissions.BasePermission):
    """
    - Safe methods (GET, HEAD, OPTIONS) are public.
    - Unsafe methods require an author or editor.
    - Object-level writes require ownership or editor role.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            request.user
            and request.user.is_authenticated
            and request.user.can_write_posts
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_editor:
            return True
        return obj.author == request.user


class CanSubmitPost(permissions.BasePermission):
    """
    Only the author of a post can submit it for review,
    and only if the post is in a submittable status.
    """

    message = "You cannot submit this post for review."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return obj.can_be_submitted_by(request.user)
