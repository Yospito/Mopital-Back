# from rest_framework import serializers

# from mopito_project.users.models import User


# class UserSerializer(serializers.ModelSerializer[User]):
#     class Meta:
#         model = User
#         fields = ["username", "name", "url"]

#         extra_kwargs = {
#             "url": {"view_name": "api:user-detail", "lookup_field": "username"},
#         }

import logging

from django.contrib.auth.models import Group, Permission
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

# from hemodialyse.core.api.serializers import BaseSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from mopito_project.core.api.serializers import BaseSerializer
from mopito_project.utils import randomize_digit_char
from mopito_project.users.models import User

# from ..models import User, VisibilityGroup
# from ...h_centers.api.serializers import HUniteSerializers
# from ...utils.randomize_digit_char import randomize_digit_char


def generate_user_code():
    """"""
    user_code = randomize_digit_char(N=4)
    exist_user = User.objects.filter(is_active=True, user_code=user_code).exists()
    if exist_user:
        return generate_user_code()
    return user_code


# class VisibilityGroupSerializer(BaseSerializer):
#     class Meta:
#         model = VisibilityGroup
#         fields = ("id", "name", "code", "slug", "description", "h_unite")


# class VisibilityDetailGroupSerializer(BaseSerializer):
#     h_unite = HUniteSerializers(many=True, read_only=True)

#     class Meta:
#         model = VisibilityGroup
#         fields = ("id", "name", "code", "slug", "description", "h_unite")


class PermissionSerializer(BaseSerializer):
    """
    Serializer for Permission.
    """

    code = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "name", "code"]

    def get_code(self, obj) -> str:
        return f"{obj.content_type.app_label}.{obj.codename}"


class GroupSerializer(BaseSerializer):
    """
    Serializer for Group.
    """

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]


class GroupDetailSerializer(BaseSerializer):
    permissions = serializers.SerializerMethodField()
    """
    Serializer for Group.
    """

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]

    def get_permissions(self, obj):
        permissions = Permission.objects.filter(group=obj)
        return PermissionSerializer(permissions, many=True).data


class UserSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = (
            "id", "is_active", "email", "password", "user_typ")
        extra_kwargs = {"password": {"write_only": True}}


class CreateUserSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "is_active",
            "email",
            "user_typ",
            "password",
            "groups",
            "user_permissions",
            # "visibility_groups",
        )
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        # Supprimer le champ "password" des données validées
        validated_data.pop('password', None)
        return super().update(instance, validated_data)


class UserDetailSerializer(BaseSerializer):
    groups = GroupDetailSerializer(many=True)
    user_permissions = PermissionSerializer(many=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "is_active",
            "email",
            "user_typ",
            "password",
            "user_permissions",
            "groups",
            "permissions",
            # "visibility_groups",

        )
        extra_kwargs = {"password": {"write_only": True}}
        depth = 1

    def get_permissions(self, obj):
        user_permissions = obj.get_user_permissions()
        groups = obj.groups.all()
        for group in groups:
            permissions = group.permissions.all()
            for permission in permissions:
                perm = f"{permission.content_type.app_label}.{permission.codename}"
                if perm not in user_permissions:
                    user_permissions.add(perm)
        return user_permissions


class SelfPasswordSerializer(BaseSerializer):
    old_password = serializers.CharField()

    class Meta:
        model = User
        fields = ("old_password", "password")
        extra_kwargs = {
            "password": {"write_only": True},
            "old_password": {"write_only": True},
        }

    def validate_old_password(self, value):
        if not self.context.get("request").user.check_password(value):
            raise ValidationError("Old password is invalid.")

        return value

    def save(self):
        user = self.context.get("request").user
        user.set_password(self.validated_data["password"])
        user.save()


class PasswordSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ("password",)
        extra_kwargs = {"password": {"write_only": True}}

    def save(self):
        user = self.instance
        user.set_password(self.validated_data["password"])
        user.save()


class TokenObtainLifetimeSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)
        username = self.user.email
        refresh = self.get_token(self.user)
        data['lifetime'] = int(refresh.access_token.lifetime.total_seconds())
        return data


class TokenRefreshLifetimeSerializer(TokenRefreshSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)
        refresh = RefreshToken(attrs['refresh'])
        data['lifetime'] = int(refresh.access_token.lifetime.total_seconds())
        return data
