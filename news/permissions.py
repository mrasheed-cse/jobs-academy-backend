from rest_framework import permissions

class IsAdminRoleOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow users with role 'ADMIN' to edit.
    Others can read-only.
    """

    def has_permission(self, request, view):
        # SAFE_METHODS = GET, HEAD, OPTIONS (read-only)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if user is authenticated and has ADMIN role
        user = request.user
        return user.is_authenticated and getattr(user, "role", None) == "ADMIN"
