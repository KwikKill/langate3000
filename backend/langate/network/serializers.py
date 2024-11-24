"""Data Serializers for the langate Network module"""
# pylint: disable=too-few-public-methods

from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from rest_framework import serializers

from langate.network.models import Device, UserDevice, DeviceManager
from langate.user.models import User

class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for a Device"""

    class Meta:
        """Meta class, used to set parameters"""

        model = Device
        exclude = ()

    def create(self, validated_data):
        """
        Create a Device object.
        """
        return DeviceManager.create_device(**validated_data)


class UserDeviceSerializer(serializers.ModelSerializer):
    """Serializer for an UserDevice"""

    class Meta:
        """Meta class, used to set parameters"""

        model = UserDevice
        exclude = ()

    def to_representation(self, instance):
        """
        Convert the instance to a dictionary that can be used to create a Response.
        """
        representation = super().to_representation(instance)
        representation['user'] = instance.user.username
        return representation

    def create(self, validated_data):
        """
        Create a UserDevice object.
        """
        return DeviceManager.create_user_device(**validated_data)

class FullDeviceSerializer(serializers.Serializer):
    """
    Serializer that can handle both UserDevice and Device objects.
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100, required=False)
    mac = serializers.CharField(max_length=17, required=False)
    bypass = serializers.BooleanField(required=False)
    whitelisted = serializers.BooleanField(read_only=True)
    ip = serializers.IPAddressField(allow_null=True, required=False)
    user = serializers.CharField(allow_null=True, required=False)

    def to_representation(self, instance):
        """
        Convert the instance to a dictionary that can be used to create a Response.
        """
        representation = super().to_representation(instance)

        # If the instance is a Device, set ip, user to None
        if isinstance(instance, UserDevice):
            representation['ip'] = instance.ip
            representation['user'] = instance.user.username
        else:
            representation['ip'] = None
            representation['user'] = None

        return representation

    def create(self, validated_data):
        """
        Create a UserDevice or a Device object.
        """
        # If the user field is present, create a UserDevice object
        if 'user' in validated_data:
            try:
                user = User.objects.get(id=validated_data.pop('user'))
            except User.DoesNotExist as e:
                raise serializers.ValidationError(_("User not found")) from e
            if not 'ip' in validated_data:
                raise serializers.ValidationError(_("You must provide UserId and IP or MAC and Name"))

            try:
                return DeviceManager.create_user_device(user, **validated_data)
            except ValidationError as e:
                raise serializers.ValidationError(e.message) from e
            except IntegrityError as e:
                raise serializers.ValidationError(_(e.__cause__.diag.message_detail)) from e
            except Exception as e:
                raise serializers.ValidationError(_("An error occurred while creating the device")) from e

        # Otherwise, create a Device object
        if not 'mac' in validated_data:
            raise serializers.ValidationError(_("You must provide UserId and IP or MAC and Name"))
        if not 'name' in validated_data:
            raise serializers.ValidationError(_("You must provide UserId and IP or MAC and Name"))
        # A device object created from here has to be whitelisted
        validated_data['whitelisted'] = True

        try:
            return DeviceManager.create_device(**validated_data)
        except ValidationError as e:
            raise serializers.ValidationError(e.message) from e
        except IntegrityError as e:
            raise serializers.ValidationError(_(e.__cause__.diag.message_detail)) from e
        except Exception as e:
            raise serializers.ValidationError(_("An error occurred while creating the device")) from e
