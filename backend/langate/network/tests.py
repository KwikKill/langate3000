import json

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse

from unittest.mock import patch, MagicMock

from rest_framework import status
from rest_framework.test import APIClient

from langate.network.models import DeviceManager, Device, UserDevice
from langate.network.utils import get_mark
from langate.user.models import User, Role
from .serializers import FullDeviceSerializer

# Using fixed values for the settings
SETTINGS = {
  "marks": [
    {
      "name": "sans vpn",
      "value": 100,
      "priority": 0
    },
    {
      "name": "vpn1",
      "value": 101,
      "priority": 0.1
    },
    {
      "name": "vpn2",
      "value": 102,
      "priority": 0.2
    },
    {
      "name": "vpn3",
      "value": 103,
      "priority": 0.7
    }
  ]
}



class TestDeviceManager(TestCase):
    """
    Test cases for the DeviceManager class
    """

    user: User

    def setUp(self):
        """
        Set up the test case
        """
        self.user = User.objects.create(
          username="testuser",
          password="password"
        )

    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    @patch('langate.settings.netcontrol.disconnect_user', return_value = None)
    def test_create_base_device_valid(self, mock_disconnect_user, mock_connect_user):
        """
        Test the creation of a base device with valid parameters
        """
        device = DeviceManager.create_device(mac="00:11:22:33:44:55", name="TestDevice")
        self.assertIsNotNone(device)
        self.assertEqual(device.mac, "00:11:22:33:44:55")
        self.assertEqual(device.name, "TestDevice")
        self.assertFalse(device.whitelisted)

    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    @patch('langate.settings.netcontrol.disconnect_user', return_value = None)
    def test_create_device_invalid_mac(self, mock_disconnect_user, mock_connect_user):
        """
        Test the creation of a device with an invalid MAC address
        """
        with self.assertRaises(ValidationError):
            DeviceManager.create_device(mac="invalid_mac", name="TestDevice")

    @patch('langate.network.models.generate_dev_name', return_value="GeneratedName")
    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    @patch('langate.settings.netcontrol.disconnect_user', return_value = None)
    def test_create_device_no_name(self, mock_disconnect_user, mock_connect_user, mock_gen_name):
        """
        Test the creation of a device with no name
        """
        device = DeviceManager.create_device(mac="00:11:22:33:44:55", name=None)
        mock_gen_name.assert_called_once()
        self.assertEqual(device.name, "GeneratedName")

    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    @patch('langate.settings.netcontrol.disconnect_user', return_value = None)
    def test_create_whitelist_device_valid(self, mock_disconnect_user, mock_connect_user):
        """
        Test the creation of a whitelisted device with valid parameters
        """
        device = DeviceManager.create_device(mac="00:11:22:33:44:55", name="TestDevice", whitelisted=True)
        self.assertIsNotNone(device)
        self.assertEqual(device.mac, "00:11:22:33:44:55")
        self.assertEqual(device.name, "TestDevice")
        self.assertTrue(device.whitelisted)

    def test_create_whitelist_device_invalid_mac(self):
        """
        Test the creation of a whitelisted device with an invalid MAC address
        """
        with self.assertRaises(ValidationError):
            DeviceManager.create_device(mac="invalid_mac", name="TestDevice", whitelisted=True)

    @patch('langate.network.models.generate_dev_name', return_value="GeneratedName")
    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    @patch('langate.settings.netcontrol.disconnect_user', return_value = None)
    def test_create_whitelist_device_no_name(self, mock_disconnect_user, mock_connect_user, mock_gen_name):
        """
        Test the creation of a whitelisted device with no name
        """
        device = DeviceManager.create_device(mac="00:11:22:33:44:55", name=None, whitelisted=True)
        mock_gen_name.assert_called_once()
        self.assertEqual(device.name, "GeneratedName")

    @patch('langate.settings.netcontrol.get_mac', return_value="00:11:22:33:44:55")
    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    def test_create_user_device_valid(self,  mock_connect_user, mock_get_mac):
        """
        Test the creation of a user device with valid parameters
        """
        device = DeviceManager.create_user_device(
          user=self.user, ip="123.123.123.123", name="TestDevice"
        )
        self.assertIsNotNone(device)
        self.assertEqual(device.mac, "00:11:22:33:44:55")
        self.assertEqual(device.name, "TestDevice")
        self.assertFalse(device.whitelisted)
        self.assertEqual(device.user, self.user)
        self.assertEqual(device.ip, "123.123.123.123")

    @patch('langate.settings.netcontrol.get_mac', return_value="00:11:22:33:44:55")
    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    def test_create_user_device_invalid_ip(self, mock_connect_user, mock_get_mac):
        """
        Test the creation of a user device with an invalid MAC address
        """
        with self.assertRaises(ValidationError):
            DeviceManager.create_user_device(
              user=self.user, ip="123.123.123.823", name="TestDevice"
            )

    @patch('langate.network.models.generate_dev_name', return_value="GeneratedName")
    @patch('langate.settings.netcontrol.get_mac', return_value="00:11:22:33:44:55")
    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    def test_create_user_device_no_name(self, mock_connect_user, mock_get_mac, mock_gen_name):
        """
        Test the creation of a user device with no name
        """
        device = DeviceManager.create_user_device(
          user=self.user, ip="123.123.123.123", name=None
        )
        mock_gen_name.assert_called_once()
        self.assertEqual(device.name, "GeneratedName")

    @patch('langate.settings.netcontrol.get_mac', return_value="00:11:22:33:44:55")
    @patch('langate.settings.netcontrol.connect_user', return_value = None)
    def test_create_device_duplicate_mac(self, mock_connect_user, mock_get_mac):
        """
        Test the creation of a device with a duplicate MAC address
        """
        with self.assertRaises(ValidationError):
            DeviceManager.create_device(mac="00:11:22:33:44:55", name="TestDevice")
            DeviceManager.create_device(mac="00:11:22:33:44:55", name="TestDevice2")

class TestNetworkAPI(TestCase):
    """
    Test cases for the DeviceDetail view
    """
    def setUp(self):
        """
        Set up the test case
        """
        self.client = APIClient()

        self.user = User.objects.create(
          username="admin",
          password="password",
          role=Role.ADMIN
        )

        self.player = User.objects.create(
          username="player",
          password="password",
          role=Role.PLAYER
        )

        self.user_device = UserDevice.objects.create(
          user=User.objects.create(username="testuser"),
          ip="123.123.123.123",
          mac="00:11:22:33:44:55",
          name="TestDevice",
        )
        self.device = Device.objects.create(
          mac="00:11:22:33:44:56",
          name="TestDeviceWhitelist",
          whitelisted=True,
          bypass=True,
        )

    def test_get_user_device_success(self):
        """
        Test the retrieval of a user device
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('device-detail', args=[self.user_device.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected = {
          'id': self.user_device.pk,
          'name': 'TestDevice',
          'mac': '00:11:22:33:44:55',
          'whitelisted': False,
          'bypass': False,
          'ip': '123.123.123.123',
          'user': 'testuser',
        }

        self.assertJSONEqual(response.content, expected)

    def test_get_device_success(self):
        """
        Test the retrieval of a device
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('device-detail', args=[self.device.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected = {
          'id': self.device.pk,
          'name': 'TestDeviceWhitelist',
          'mac': '00:11:22:33:44:56',
          'whitelisted': True,
          'bypass': True,
          'ip': None,
          'user': None,
        }

        self.assertJSONEqual(response.content, expected)

    def test_get_device_not_found(self):
        """
        Test the retrieval of a non-existent device
        """
        self.client.force_authenticate(user=self.user)

        url = reverse('device-detail', args=[999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_device_no_auth(self):
        """
        Test the retrieval of a device without authentication
        """
        response = self.client.get(reverse('device-detail', args=[self.device.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_device_unauthorized(self):
        """
        Test the retrieval of a device by an unauthorized user
        """
        self.client.force_authenticate(user=self.player)

        response = self.client.get(reverse('device-detail', args=[self.device.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('langate.settings.netcontrol.disconnect_user', return_value=None)
    def test_delete_device_success(self, mock_disconnect_user):
        """
        Test the deletion of a device
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(reverse('device-detail', args=[self.user_device.pk]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Device.objects.filter(pk=self.user_device.pk).exists())
        self.assertFalse(UserDevice.objects.filter(pk=self.user_device.pk).exists())

    @patch('langate.settings.netcontrol.disconnect_user', return_value=None)
    def test_delete_device_not_found(self, mock_disconnect_user):
        """
        Test the deletion of a non-existent device
        """
        self.client.force_authenticate(user=self.user)

        url = reverse('device-detail', args=[999])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('langate.settings.netcontrol.disconnect_user', return_value=None)
    def test_delete_device_no_auth(self, mock_disconnect_user):
        """
        Test the deletion of a device without authentication
        """
        response = self.client.delete(reverse('device-detail', args=[self.device.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('langate.settings.netcontrol.disconnect_user', return_value=None)
    def test_delete_device_unauthorized(self, mock_disconnect_user):
        """
        Test the deletion of a device by an unauthorized user
        """
        self.client.force_authenticate(user=self.player)

        response = self.client.delete(reverse('device-detail', args=[self.device.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('langate.settings.netcontrol.disconnect_user', return_value=None)
    @patch('langate.settings.netcontrol.connect_user', return_value=None)
    @patch('langate.settings.netcontrol.set_mark', return_value=None)
    def test_patch_device_success(self, mock_set_mark, mock_connect_user, mock_disconnect_user):
        """
        Test the update of a device
        """
        self.client.force_authenticate(user=self.user)

        new_data = {
          'mac': '00:11:22:33:44:57',
          'name': 'new_name'
        }
        with patch('langate.settings.netcontrol.get_mac') as mock_get_mac:
            mock_get_mac.return_value = new_data['mac']
            response = self.client.patch(reverse('device-detail', args=[self.device.pk]), new_data)
            self.device.refresh_from_db()
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.device.mac, new_data['mac'])
            self.assertEqual(self.device.name, new_data['name'])

    def test_patch_device_not_found(self):
        """
        Test the update of a non-existent device
        """
        self.client.force_authenticate(user=self.user)

        url = reverse('device-detail', args=[999])
        response = self.client.patch(url, {})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_device_no_auth(self):
        """
        Test the update of a device without authentication
        """
        response = self.client.patch(reverse('device-detail', args=[self.device.pk]), {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_device_unauthorized(self):
        """
        Test the update of a device by an unauthorized user
        """
        self.client.force_authenticate(user=self.player)

        response = self.client.patch(reverse('device-detail', args=[self.device.pk]), {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_device_invalid_data(self):
        """
        Test the update of a device with invalid data
        """
        self.client.force_authenticate(user=self.user)

        invalid_data = {'mac': 's'}
        response = self.client.patch(
          reverse('device-detail', args=[self.device.pk]),
          invalid_data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_device_list_success(self):
        """
        Test the retrieval of a list of devices
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('device-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # The response must be paginated
        self.assertIn('results', response.json())
        self.assertIn('count', response.json())
        self.assertIn('next', response.json())
        self.assertIn('previous', response.json())

        # The response must contain the devices
        self.assertEqual(response.json()['count'], 2)
        self.assertEqual(len(response.json()['results']), 2)

        # The response must contain the correct devices
        expected = {
          'count': 2,
          'next': None,
          'previous': None,
          'results': [
            {
              'id': self.user_device.pk,
              'name': 'TestDevice',
              'mac': '00:11:22:33:44:55',
              'whitelisted': False,
              'bypass': False,
              'ip': '123.123.123.123',
              'user': 'testuser',
            },
            {
              'id': self.device.pk,
              'name': 'TestDeviceWhitelist',
              'mac': '00:11:22:33:44:56',
              'whitelisted': True,
              'bypass': True,
              'ip': None,
              'user': None,
            }
          ]
        }

        self.assertJSONEqual(response.content, expected)

    def test_get_device_list_no_auth(self):
        """
        Test the retrieval of a list of devices without authentication
        """
        response = self.client.get(reverse('device-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_device_list_unauthorized(self):
        """
        Test the retrieval of a list of devices by an unauthorized user
        """
        self.client.force_authenticate(user=self.player)

        response = self.client.get(reverse('device-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user_device_list_success(self):
        """
        Test the retrieval of a list of user devices
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('user-devices'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # The response must be paginated
        self.assertIn('results', response.json())
        self.assertIn('count', response.json())
        self.assertIn('next', response.json())
        self.assertIn('previous', response.json())

        # The response must contain the devices
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(len(response.json()['results']), 1)

        # The response must contain the correct devices
        expected = {
          'count': 1,
          'next': None,
          'previous': None,
          'results': [
            {
              'id': self.user_device.pk,
              'name': 'TestDevice',
              'mac': '00:11:22:33:44:55',
              'whitelisted': False,
              'bypass': False,
              'ip': '123.123.123.123',
              'user': 'testuser',
              'mark': SETTINGS['marks'][0]['value']
            }
          ]
        }

        self.assertJSONEqual(response.content, expected)

    def test_get_user_device_list_no_auth(self):
        """
        Test the retrieval of a list of user devices without authentication
        """
        response = self.client.get(reverse('user-devices'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user_device_list_unauthorized(self):
        """
        Test the retrieval of a list of user devices by an unauthorized user
        """
        self.client.force_authenticate(user=self.player)

        response = self.client.get(reverse('user-devices'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('langate.settings.netcontrol.connect_user', return_value=None)
    def test_post_device_success(self, mock_connect_user):
        """
        Test the creation of a device
        """
        self.client.force_authenticate(user=self.user)

        new_data = {
          'mac': '00:11:22:33:44:57',
          'name': 'new_name'
        }
        with patch('langate.settings.netcontrol.get_mac') as mock_get_mac:
            mock_get_mac.return_value = new_data['mac']
            response = self.client.post(reverse('device-list'), new_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            device = Device.objects.get(mac='00:11:22:33:44:57')
            self.assertEqual(device.name, 'new_name')

    @patch('langate.settings.netcontrol.disconnect_user', return_value=None)
    @patch('langate.settings.netcontrol.connect_user', return_value=None)
    @patch('langate.settings.netcontrol.set_mark', return_value=None)
    @patch('langate.settings.netcontrol.get_mac', return_value="00:11:22:33:44:57")
    def test_post_user_device_success(self, mock_get_mac, mock_set_mark, mock_connect_user, mock_disconnect_user):
        """
        Test the creation of a user device
        """
        self.client.force_authenticate(user=self.user)

        new_data = {
          'ip': '123.123.123.123',
          'name': 'new_name',
          'user': self.user.id,
        }
        response = self.client.post(reverse('device-list'), new_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        device = UserDevice.objects.get(mac='00:11:22:33:44:57')
        self.assertEqual(device.name, 'new_name')

    def test_post_device_invalid_data(self):
        """
        Test the creation of a device with invalid data
        """
        self.client.force_authenticate(user=self.user)

        invalid_data = {'mac': 's'}
        response = self.client.post(reverse('device-list'), invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_device_no_auth(self):
        """
        Test the creation of a device without authentication
        """
        response = self.client.post(reverse('device-list'), {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_device_unauthorized(self):
        """
        Test the creation of a device by an unauthorized user
        """
        self.client.force_authenticate(user=self.player)

        response = self.client.post(reverse('device-list'), {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class TestMarkAPI(TestCase):
    """
    Test cases for the MarkDetail view
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('mark-list')
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.user.role = Role.STAFF
        self.user.save()
        self.client.force_authenticate(user=self.user)
        self.settings = {"marks":[
          {"value": 100, "name": "Mark 1", "priority": 0.5},
          {"value": 101, "name": "Mark 2", "priority": 0.5}
        ]}
        self.SETTINGS = self.settings
        Device.objects.create(mac="00:00:00:00:00:01", mark=100, whitelisted=False)
        Device.objects.create(mac="00:00:00:00:00:02", mark=101, whitelisted=True)
        Device.objects.create(mac="00:00:00:00:00:03", mark=101, whitelisted=False)

    @patch('langate.network.views.SETTINGS')
    def test_get_marks(self, mock_settings):
        mock_settings.__getitem__.side_effect = self.SETTINGS.__getitem__

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for i in range(len(self.settings["marks"])):
            self.assertEqual(response.data[i]["value"], self.settings["marks"][i]["value"])
            self.assertEqual(response.data[i]["name"], self.settings["marks"][i]["name"])
            self.assertEqual(response.data[i]["priority"], self.settings["marks"][i]["priority"])
            self.assertEqual(response.data[i]["devices"], Device.objects.filter(mark=self.settings["marks"][i]["value"], whitelisted=False).count())
            self.assertEqual(response.data[i]["whitelisted"], Device.objects.filter(mark=self.settings["marks"][i]["value"], whitelisted=True).count())

    @patch('langate.settings.netcontrol.set_mark', return_value=None)
    @patch('langate.network.views.save_settings')
    def test_patch_marks(self, mock_save_settings, mock_set_mark):
        mock_save_settings.side_effect = lambda x: None

        new_marks = [
          {"value": 102, "name": "Mark 3", "priority": 0.3},
          {"value": 103, "name": "Mark 4", "priority": 0.7}
        ]
        response = self.client.patch(self.url, new_marks, format='json')

        from langate.settings import SETTINGS as ORIGINAL_SETTINGS

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(ORIGINAL_SETTINGS["marks"]), 2)
        self.assertEqual(ORIGINAL_SETTINGS["marks"][0]["value"], 102)
        self.assertEqual(ORIGINAL_SETTINGS["marks"][1]["value"], 103)

    def test_patch_invalid_marks(self):
        invalid_marks = [
          {"value": 102, "name": "Mark 3", "priority": "aa"},
          {"value": 103, "name": "Mark 4", "priority": 0.6}
        ]
        response = self.client.patch(self.url, invalid_marks, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid mark")

    @patch('langate.network.views.save_settings')
    def test_patch_marks_not_authenticated(self, mock_save_settings):
        self.client.force_authenticate(user=None)
        response = self.client.patch(self.url, [], format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class TestsGameMarkAPI(TestCase):
  def setUp(self):
    self.settings = {
      "marks": [
        {
          "name": "sans vpn",
          "value": 100,
          "priority": 0
        },
        {
          "name": "vpn1",
          "value": 101,
          "priority": 0.1
        },
        {
          "name": "vpn2",
          "value": 102,
          "priority": 0.2
        },
        {
          "name": "vpn3",
          "value": 103,
          "priority": 0.7
        }
      ],
      "games": {
        "game1": [100],
        "game2": [101, 102]
      }
    }

    self.client = APIClient()
    self.url = reverse('game-list')
    self.user = User.objects.create_user(username='testuser', password='testpassword')
    self.user.role = Role.STAFF
    self.user.save()
    self.client.force_authenticate(user=self.user)

  @patch('langate.network.views.SETTINGS')
  def test_get_games(self, mock_settings):
    mock_settings.__getitem__.side_effect = self.settings.__getitem__

    response = self.client.get(self.url)
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertIsInstance(response.data, dict)
    self.assertEqual(response.data, self.settings["games"])

  @patch('langate.network.views.save_settings')
  def test_patch_games_valid(self, mock_save_settings):
    mock_save_settings.side_effect = lambda x: None

    valid_data = {"Game1": [102], "Game2": [103, 101]}

    response = self.client.patch(self.url, data=json.dumps(valid_data), content_type='application/json')
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertEqual(response.data, valid_data)

  def test_patch_games_invalid(self):
    invalid_data = [
      {"name": "Game1"},
      {"value": "game2"}
    ]
    response = self.client.patch(self.url, data=json.dumps(invalid_data), content_type='application/json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("error", response.data)

  @patch('langate.network.views.save_settings')
  def test_patch_games_not_authenticated(self, mock_save_settings):
    self.client.force_authenticate(user=None)
    response = self.client.patch(self.url, data=json.dumps({}), content_type='application/json')
    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
