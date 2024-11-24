"""User Tests Module"""
import json
import re
from datetime import datetime

from typing import Dict
from unittest.mock import patch
from django.test import TestCase
from django.core import mail
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Permission

from rest_framework.test import APIClient
from rest_framework import serializers

from langate.user.models import User, Role
from langate.user.serializers import UserSerializer


class UserTestCase(TestCase):
    """
    Tests of the User model
    """

    def setUp(self):
        """
        Create some base users to do operations on
        """
        u: User = User.objects.create_user(
            username="staffplayer",
            password="^ThisIsAnAdminPassword42$",
        )
        u.role = Role.STAFF

        User.objects.create_user(
            username="randomplayer",
            password="IUseAVerySecurePassword",
        )
        User.objects.create_user(
            username="anotherplayer",
            password="ThisIsPassword",
        )

    def test_get_existing_full_user(self):
        """
        Test getting all the fields of an already created user
        """
        u: User = User.objects.get(username="randomplayer")
        self.assertEqual(u.get_username(), "randomplayer")
        self.assertTrue(u.has_usable_password())
        self.assertTrue(u.check_password("IUseAVerySecurePassword"))
        self.assertTrue(u.is_active)
        self.assertEqual(u.role, Role.PLAYER)


    def test_get_existing_minimal_user(self):
        """
        Test getting all the fields of an user created with only the required fields
        """
        u: User = User.objects.get(username="anotherplayer")
        self.assertEqual(u.get_username(), "anotherplayer")
        self.assertTrue(u.has_usable_password())
        self.assertTrue(u.check_password("ThisIsPassword"))
        self.assertTrue(u.is_active)
        self.assertEqual(u.role, Role.PLAYER)

    def test_get_non_existing_user(self):
        """
        Test that getting an user which does not exist throws an `User.DoesNotExist` error
        """
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(username="idontexist")

class UserEndToEndTestCase(TestCase):
    """
    Test cases of the API endpoints and workflows related to user model
    """

    client: APIClient

    def setUp(self):
        """
        Create a player to test getters
        """
        self.client = APIClient()
        user = User.objects.create_user(
            username="randomplayer",
            password="IUseAVerySecurePassword",
            is_active=True,
        )

    def test_login_invalid_account(self):
        """
        Try to login with invalid requests
        """

        def send_valid_data(data):
            request = self.client.post("/user/login/", data, format="json")

            self.assertEqual(request.status_code, 404)
            self.assertEqual(
                request.data["error"][0],
                _("Bad Username or password"),
            )

        send_valid_data(
            {
                "username": "newplayer",
                "password": "1111qwer!",
            }
        )

    @patch('langate.settings.netcontrol.get_mac', return_value="00:11:22:33:44:55")
    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    def test_login_account(self, mock_connect_user, mock_get_mac):
        """
        Test that when everything is ok, an user is able to login
        """
        user = User.objects.create_user(
            username="newplayer",
            password="1111qwer!",
            is_active=True,
        )
        user.save()

        def send_valid_data(data):
            # Add HTTP_X_FORWARDED_FOR to simulate a request from a client
            request = self.client.post(
              "/user/login/",
              data,
              format="json",
              HTTP_X_FORWARDED_FOR="127.0.0.1"
            )

            self.assertEqual(request.status_code, 200)
            self.assertTrue("sessionid" in self.client.cookies)

        send_valid_data(
            {
                "username": "newplayer",
                "password": "1111qwer!",
            }
        )

class UserAPITestCase(TestCase):
    """
    Test cases of the API endpoints and workflows related to user model
    """

    client: APIClient
    user: User
    admin: User

    def setUp(self):
        """
        Create a player to test getters
        """
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="randomplayer",
            password="IUseAVerySecurePassword",
            is_active=True,
        )
        self.admin = User.objects.create_user(
            username="adminplayer",
            password="^ThisIsAnAdminPassword42$",
        )
        self.admin.role = Role.ADMIN
        self.admin.save()

    @patch('langate.settings.netcontrol.get_mac', return_value="00:11:22:33:44:55")
    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    def test_get_user(self, mock_connect_user, mock_get_mac):
        """
        Test that the user can get his own information
        """
        self.client.force_authenticate(user=User.objects.get(username="randomplayer"))
        request = self.client.get("/user/me/", HTTP_X_FORWARDED_FOR="127.0.0.1")

        self.assertEqual(request.status_code, 200)
        self.assertEqual(request.data["username"], "randomplayer")

    @patch('langate.settings.netcontrol.get_mac', return_value="00:11:22:33:44:55")
    def test_get_user_not_logged_in(self, mock_get_mac):
        """
        Test that the user can't get his own information if he's not logged in
        """
        request = self.client.get("/user/me/")

        self.assertEqual(request.status_code, 403)

    def test_get_user_not_found(self):
        """
        Test that the user can't get his own information if he's not logged in
        """
        with patch('langate.settings.netcontrol.get_mac') as mock_get_mac:
            mock_get_mac.return_value = "00:11:22:33:44:55"
            self.client.force_authenticate(user=User.objects.get(username="randomplayer"))
            request = self.client.get("/user/unknown/")

            self.assertEqual(request.status_code, 404)

    def test_get_user_list(self):
        """
        Test that the user can get the list of all users
        """
        self.client.force_authenticate(user=self.admin)
        request = self.client.get("/user/users/")

        self.assertEqual(request.status_code, 200)

        # test that this is paginated
        self.assertTrue("results" in request.data)
        self.assertTrue("count" in request.data)
        self.assertTrue("next" in request.data)
        self.assertTrue("previous" in request.data)

        # test the result
        self.assertEqual(request.data["count"], 2)
        self.assertEqual(request.data["results"][0]["id"], self.admin.id)
        self.assertEqual(request.data["results"][0]["username"], self.admin.username)
        self.assertTrue("last_login" in request.data["results"][0])
        if request.data["results"][0]["last_login"] is not None:
            self.assertEqual(
              datetime.fromisoformat(request.data["results"][0]["last_login"]),
              self.admin.last_login
            )
        else:
            self.assertEqual(self.admin.last_login, None)
        self.assertEqual(request.data["results"][0]["role"], self.admin.role)
        self.assertEqual(request.data["results"][0]["is_active"], self.admin.is_active)
        self.assertTrue("date_joined" in request.data["results"][0])
        if request.data["results"][0]["date_joined"] is not None:
            self.assertEqual(
              datetime.fromisoformat(request.data["results"][0]["date_joined"]),
              self.admin.date_joined
            )
        else:
            self.assertEqual(self.admin.date_joined, None)
        self.assertEqual(request.data["results"][0]["max_device_nb"], self.admin.max_device_nb)
        self.assertEqual(request.data["results"][0]["tournament"], self.admin.tournament)
        self.assertEqual(request.data["results"][0]["team"], self.admin.team)

        self.assertEqual(request.data["results"][0]["devices"], [])

        # Verify the number of fields for the user
        self.assertEqual(len(request.data["results"][0]), 11)

    def test_get_user_list_not_logged_in(self):
        """
        Test that the user can't get the list of all users if he's not logged in
        """
        request = self.client.get("/user/users/")

        self.assertEqual(request.status_code, 403)

    def test_get_user_list_not_staff(self):
        """
        Test that the user can't get the list of all users if he's not staff
        """
        self.client.force_authenticate(user=self.user)
        request = self.client.get("/user/users/")

        self.assertEqual(request.status_code, 403)

    def test_get_user_list_staff(self):
        """
        Test that the user can get the list of all users if he's
        staff
        """
        self.client.force_authenticate(user=self.admin)
        self.user.role = Role.STAFF
        self.user.save()
        request = self.client.get("/user/users/")

        self.assertEqual(request.status_code, 200)
        self.assertEqual(request.data["results"][0]["username"], self.admin.username)

    def test_get_user_list_pagination(self):
        """
        Test that the user can get the list of all users with pagination.
        Also test query params for pagination (page, page_size, order, filter)
        """
        self.client.force_authenticate(user=self.admin)
        request = self.client.get("/user/users/?page=1")

        self.assertEqual(request.status_code, 200)
        self.assertTrue("results" in request.data)
        self.assertTrue("count" in request.data)
        self.assertTrue("next" in request.data)
        self.assertTrue("previous" in request.data)
        self.assertEqual(request.data["count"], 2)
        self.assertEqual(len(request.data["results"]), 2)

        # test the page query param
        request = self.client.get("/user/users/?page=1&page_size=1")

        self.assertEqual(request.status_code, 200)
        self.assertTrue("results" in request.data)
        self.assertTrue("count" in request.data)
        self.assertTrue("next" in request.data)
        self.assertTrue("previous" in request.data)
        self.assertEqual(request.data["count"], 2)
        self.assertEqual(len(request.data["results"]), 1)
        self.assertNotEqual(request.data["next"], None)

        # test the order query param
        request = self.client.get("/user/users/?order=-username")

        self.assertEqual(request.status_code, 200)
        self.assertTrue("results" in request.data)
        self.assertTrue("count" in request.data)
        self.assertTrue("next" in request.data)
        self.assertTrue("previous" in request.data)
        self.assertEqual(request.data["count"], 2)
        self.assertEqual(len(request.data["results"]), 2)
        self.assertEqual(request.data["results"][0]["username"], self.user.username)
        self.assertEqual(request.data["results"][1]["username"], self.admin.username)

        # test the filter query param
        request = self.client.get("/user/users/?filter=dom")

        self.assertEqual(request.status_code, 200)
        self.assertTrue("results" in request.data)
        self.assertTrue("count" in request.data)
        self.assertTrue("next" in request.data)
        self.assertTrue("previous" in request.data)
        self.assertEqual(request.data["count"], 1)
        self.assertEqual(len(request.data["results"]), 1)
        self.assertEqual(request.data["results"][0]["username"], self.user.username)

    def test_create_user(self):
        """
        Test that an admin can create a new user
        """
        self.client.force_authenticate(user=self.admin)
        request = self.client.post(
          "/user/users/",
          {
            "username": "newplayer",
            "password": "1111qwer!",
            "role": Role.PLAYER,
            "is_active": True,
          },
          format="json"
        )

        self.assertEqual(request.status_code, 201)
        self.assertTrue(User.objects.get(username="newplayer").check_password("1111qwer!"))

    def test_create_user_not_logged_in(self):
        """
        Test that you can't create a new user if you're not logged in
        """
        request = self.client.post(
          "/user/users/",
          {
            "username": "newplayer",
            "password": "1111qwer!",
            "role": Role.PLAYER,
            "is_active": True,
          },
          format="json"
        )

        self.assertEqual(request.status_code, 403)

    def test_create_user_not_staff(self):
        """
        Test that the user can't create a new user if he's not staff
        """
        self.client.force_authenticate(user=self.user)
        request = self.client.post(
          "/user/users/",
          {
            "username": "newplayer",
            "password": "1111qwer!",
            "role": Role.PLAYER,
            "is_active": True,
          },
          format="json"
        )

        self.assertEqual(request.status_code, 403)

    def test_create_user_invalid_data(self):
        """
        Test that you can't create a new user with invalid data
        """
        # Missing username
        self.client.force_authenticate(user=self.admin)
        request = self.client.post(
          "/user/users/",
          {
            "password": "1111qwer!",
          },
          format="json"
        )

        self.assertEqual(request.status_code, 400)
        self.assertEqual(request.data["error"]["username"][0], _("This field is required."))

        # Missing password
        request = self.client.post(
          "/user/users/",
          {
            "username": "newplayer",
          },
          format="json"
        )

        self.assertEqual(request.status_code, 400)
        self.assertEqual(request.data["error"]["password"][0], _("This field is required."))

        # Bad password
        request = self.client.post(
          "/user/users/",
          {
            "username": "newplayer",
            "password": "1111",
          },
          format="json"
        )

        self.assertEqual(request.status_code, 400)
        self.assertEqual(
          request.data["error"],
          [
            'This password is too short. It must contain at least 8 characters.',
            'This password is too common.',
            'This password is entirely numeric.'
          ]
        )

        # Bad role
        request = self.client.post(
          "/user/users/",
          {
            "username": "newplayer",
            "password": "1111qwer!",
            "role": "badrole",
          },
          format="json"
        )

        self.assertEqual(request.status_code, 400)
        self.assertEqual(request.data["error"]["role"][0], _('"badrole" is not a valid choice.'))

    def test_patch_user(self):
        """
        Test that an admin can patch an user
        """
        self.client.force_authenticate(user=self.admin)

        current_is_active = self.user.is_active

        request = self.client.patch(
          "/user/users/" + str(self.user.id) + "/",
          {
            "username": "newplayer",
            "role": Role.PLAYER,
            "is_active": not current_is_active,
          },
          format="json"
        )

        self.assertEqual(request.status_code, 200)
        self.assertEqual(User.objects.get(username="newplayer").id, self.user.id)
        self.assertEqual(User.objects.get(username="newplayer").role, Role.PLAYER)
        self.assertEqual(User.objects.get(username="newplayer").is_active, not current_is_active)

    def test_patch_user_not_logged_in(self):
        """
        Test that you can't patch an user if you're not logged in
        """
        request = self.client.patch(
          "/user/users/" + str(self.user.id) + "/",
          {"username": "newplayer"},
          format="json"
        )

        self.assertEqual(request.status_code, 403)

    def test_patch_user_not_staff(self):
        """
        Test that the user can't patch an user if he's not staff
        """
        self.client.force_authenticate(user=self.user)
        request = self.client.patch(
          "/user/users/" + str(self.user.id) + "/",
          {"username": "newplayer"},
          format="json"
        )

        self.assertEqual(request.status_code, 403)

    def test_patch_user_not_found(self):
        """
        Test that you can't patch an user that does not exist
        """
        self.client.force_authenticate(user=self.admin)
        request = self.client.patch(
          "/user/users/35z7/",
          {"username": "newplayer"},
          format="json"
        )

        self.assertEqual(request.status_code, 404)

    def test_patch_user_invalid_data(self):
        """
        Test that you can't patch an user with invalid data
        """
        self.client.force_authenticate(user=self.admin)
        request = self.client.patch(
          "/user/users/" + str(self.user.id) + "/",
          {"username": ""},
          format="json"
        )

        self.assertEqual(request.status_code, 400)
        self.assertEqual(request.data["username"][0], _("This field may not be blank."))

        # Bad role
        request = self.client.patch(
          "/user/users/" + str(self.user.id) + "/",
          {"role": "badrole"},
          format="json"
        )

        self.assertEqual(request.status_code, 400)
        self.assertEqual(request.data["role"][0], _('"badrole" is not a valid choice.'))

        # Password
        request = self.client.patch(
          "/user/users/" + str(self.user.id) + "/",
          {"password": "1111"},
          format="json"
        )

        self.assertEqual(request.status_code, 400)
        self.assertEqual(request.data["error"], [_("Password cannot be changed")])

class UserChangePassword(TestCase):
    """
    Test cases of the API endpoints and workflows related to user model
    """

    client: APIClient
    user: User
    admin: User

    def setUp(self):
        """
        Create a player to test getters
        """
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="randomplayer",
            password="IUseAVerySecurePassword",
            is_active=True,
        )
        self.admin = User.objects.create_user(
            username="adminplayer",
            password="^ThisIsAnAdminPassword42$",
        )
        self.admin.role = Role.ADMIN
        self.admin.save()

    def test_change_password(self):
        """
        Test that an admin can change the password of an user
        """
        self.client.force_authenticate(user=self.admin)
        request = self.client.post(
          "/user/change-password/" + str(self.user.id) + "/",
          {"password": "newpassword"}, format="json"
        )

        self.assertEqual(request.status_code, 200)
        self.assertTrue(User.objects.get(username="randomplayer").check_password("newpassword"))

    def test_change_password_not_logged_in(self):
        """
        Test that you can't change the password of an user if you're not logged in
        """
        request = self.client.post("/user/change-password/1/", {"password": "newpassword"}, format="json")

        self.assertEqual(request.status_code, 403)

    def test_change_password_not_found(self):
        """
        Test that you can't change the password of an user that does not exist
        """
        self.client.force_authenticate(user=self.admin)
        request = self.client.post("/user/change-password/35z7/", {"password": "newpassword"}, format="json")

        self.assertEqual(request.status_code, 404)

    def test_change_password_not_staff(self):
        """
        Test that the user can't change a password if he's not staff
        """
        self.client.force_authenticate(user=self.user)
        request = self.client.post("/user/change-password/1/", {"password": "newpassword"}, format="json")

        self.assertEqual(request.status_code, 403)

    def test_change_password_staff(self):
        """
        Test that the user can change the password of another user if he's staff
        """
        self.client.force_authenticate(user=self.admin)
        request = self.client.post
