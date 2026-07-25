from rest_framework import serializers
from .models import Account, Agent
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.contrib.auth import get_user_model
from django.core.validators import validate_email as django_validate_email
import os
from main_api.sanitization import sanitize_agent_input


from drf_spectacular.utils import extend_schema_serializer


@extend_schema_serializer(component_name="AccountAgent")
class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ["id", "name", "orange_stars", "is_active", "created_at"]


class AccountSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[UniqueValidator(queryset=Account.objects.all(), lookup="iexact")])
    username = serializers.CharField(validators=[UniqueValidator(queryset=Account.objects.all(), lookup="iexact")])
    password = serializers.CharField(write_only=True)
    agents = AgentSerializer(many=True, read_only=True)
    follows = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    def validate_email(self, value):
        return value.lower()

    def validate_username(self, value):
        return value.lower()

    class Meta:
        model = Account
        fields = [
            "id",
            "email",
            "username",
            "password",
            "avatar",
            "agents",
            "follows",
            "biography",
            "date_joined",
            "last_login",
            "is_active",
            "balance_blue_stars",
            "balance_orange_stars",
            "saved_nodes",
            "saved_papers",
        ]
        extra_kwargs = {"password": {"write_only": True}}
        read_only_fields = ["balance_blue_stars", "balance_orange_stars", "is_active", "date_joined", "last_login"]

    def create(self, validated_data):
        return Account.objects.create_user(**validated_data)


class PasswordSerializer(serializers.Serializer):
    password1 = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs["password1"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Password fields didn't match."})
        try:
            validate_password(attrs["password1"])
        except ValidationError as e:
            raise serializers.ValidationError({"password1": list(e.messages)})
        return attrs


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password1 = serializers.CharField(write_only=True, required=True)
    new_password2 = serializers.CharField(write_only=True, required=True)
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs["new_password1"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "Password fields didn't match."})
        user = self.context.get("user")
        try:
            validate_password(attrs["new_password1"], user=user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password1": list(e.messages)})
        return attrs


User = get_user_model()


class PersonalInformationSerializer(serializers.ModelSerializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = ["username", "email", "current_password", "new_password"]
        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
            "new_password": {"required": False},
        }

    def validate_username(self, value):
        if value:
            # Apply strict normalization (NFKC) to username
            value = sanitize_agent_input(value, apply_nfkc=True)
            if len(value) > 30:
                raise serializers.ValidationError("Username must be under 30 characters.")
            # Basic validation to ensure it doesn't become empty or problematic after sanitization
            if not value.strip():
                raise serializers.ValidationError("Username cannot be empty.")
        return value

    def validate_email(self, value):
        if value:
            try:
                django_validate_email(value)
            except ValidationError:
                raise serializers.ValidationError("Invalid email address.")
            if User.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
                raise serializers.ValidationError("This email is already in use.")
        return value

    def validate_new_password(self, value):
        if value:
            try:
                validate_password(value, user=self.instance)
            except ValidationError as e:
                raise serializers.ValidationError(list(e.messages))
        return value

    def update(self, instance, validated_data):
        instance.username = validated_data.get("username", instance.username)

        new_password = validated_data.get("new_password")
        if new_password:
            instance.set_password(new_password)
            instance.jwt_token_version += 1

        # We'll handle email update in the view
        instance.save()
        return instance


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["avatar", "biography"]

    def validate_avatar(self, value):
        if value:
            # Check file size
            if value.size > 60 * 1024:
                raise ValidationError("Image file too large ( > 60KB )")

            # Check if it's a valid image
            width, height = get_image_dimensions(value)
            if not width or not height:
                raise ValidationError("Submitted file is not a valid image")

            ext = value.name.rsplit(".", 1)[-1].lower()
            if ext not in ["jpg", "jpeg", "png"]:
                raise ValidationError("Unsupported file extension")

            import uuid

            # Set filename to include unique hash to prevent caching issues
            value.name = f"user_{self.instance.id}_{uuid.uuid4().hex[:8]}.{ext}"

            return value

    def validate_biography(self, value):
        if value:
            # Apply loose sanitization to biography
            value = sanitize_agent_input(value, apply_nfkc=False)
            if len(value) > 2000:
                raise ValidationError("Biography must be under 2000 characters")
        return value

    def update(self, instance, validated_data):
        if "avatar" in validated_data:
            # Delete the old avatar file if it exists
            if instance.avatar:
                old_path = instance.avatar.path
                if os.path.isfile(old_path):
                    os.remove(old_path)

            # Save the new avatar
            instance.avatar = validated_data["avatar"]

        if "biography" in validated_data:
            instance.biography = validated_data["biography"]

        instance.save()
        return instance
