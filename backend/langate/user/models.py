"""
Module for the definition of models tied to users
"""
from datetime import datetime

from django.contrib.auth.base_user import AbstractBaseUser as AbstractBaseUser
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

class UserManager(BaseUserManager):
    """
    Managers the User objects (kind of like a serializer but not quite that)
    """

    # pylint: disable=unused-argument
    def create_user(
        self, username, password, password_validation=None, **extra_fields
    ):
        """
        check that all required fields are present and create an user
        """
        if not username:
            raise ValueError(_("A username is required"))
        if not password:
            raise ValueError(_("A password is required"))
        user = self.model(
            username=username,
            date_joined=timezone.make_aware(datetime.now()),
            **extra_fields
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, password, **extra_fields):
        """
        Check that all required fields are present and create a superuser
        """
        if password is None:
            raise TypeError(_("Superusers must have a password."))
        user = self.create_user(username, password, **extra_fields)
        user.role = Role.ADMIN
        user.is_active = True
        user.save()

        return user

class Role(models.TextChoices):
    """
    Enum for the role of a user
    """

    PLAYER = "player", _("Player")
    MANAGER = "manager", _("Manager")
    GUEST = "guest", _("Guest")
    STAFF = "staff", _("Staff")
    ADMIN = "admin", _("Admin")

class User(AbstractBaseUser):
    """
    A user is simply our own abstraction defined above the standard Django User class.
    """

    username_validator: UnicodeUsernameValidator = UnicodeUsernameValidator()

    username = models.CharField(
        max_length=150,
        unique=True,
    )
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.PLAYER,
    )
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(
      default=timezone.now,
    )

    # The number of devices a user can have, minimum is 2
    max_device_nb = models.IntegerField(
        default=3,
        validators=[MinValueValidator(2)],
    )

    # Relevant for the player role
    tournament = models.CharField(max_length=100, null=True)
    team = models.CharField(max_length=100, null=True)
    
    # Whether the user's devices have bypass on
    bypass = models.BooleanField(default=False)
    
    USERNAME_FIELD = "username"
    objects = UserManager()

    class Meta:
        """Meta options"""

        verbose_name = _("User")
        verbose_name_plural = _("Users")
