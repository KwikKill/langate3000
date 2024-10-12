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

    def test_create_base_device_valid(self):
        """
        Test the creation of a base device with valid parameters
        """
        with patch('langate.network.models.netcontrol.query') as mock_query:
            mock_query.return_value = None
            device = DeviceManager.create_device(mac="00:11:22:33:44:55", name="TestDevice")
            self.assertIsNotNone(device)
            self.assertEqual(device.mac, "00:11:22:33:44:55")
            self.assertEqual(device.name, "TestDevice")
            self.assertFalse(device.whitelisted)

    def test_create_device_invalid_mac(self):
        """
        Test the creation of a device with an invalid MAC address
        """
        with self.assertRaises(ValidationError):
            DeviceManager.create_device(mac="invalid_mac", name="TestDevice")

    def test_create_device_no_name(self):
        """
        Test the creation of a device with no name
        """
        with patch('langate.network.models.netcontrol.query') as mock_query, \
             patch('langate.network.models.generate_dev_name', return_value="GeneratedName") as mock_gen_name:
            mock_query.return_value = None
            device = DeviceManager.create_device(mac="00:11:22:33:44:55", name=None)
            mock_gen_name.assert_called_once()
            self.assertEqual(device.name, "GeneratedName")

    def test_create_whitelist_device_valid(self):
        """
        Test the creation of a whitelisted device with valid parameters
        """
        with patch('langate.network.models.netcontrol.query') as mock_query:
            mock_query.return_value = None
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

    def test_create_whitelist_device_no_name(self):
        """
        Test the creation of a whitelisted device with no name
        """
        with patch('langate.network.models.netcontrol.query') as mock_query, \
             patch('langate.network.models.generate_dev_name', return_value="GeneratedName") as mock_gen_name:
            mock_query.return_value = None
            device = DeviceManager.create_device(mac="00:11:22:33:44:55", name=None, whitelisted=True)
            mock_gen_name.assert_called_once()
            self.assertEqual(device.name, "GeneratedName")

    def test_create_user_device_valid(self):
        """
        Test the creation of a user device with valid parameters
        """
        with patch('langate.network.models.netcontrol.query') as mock_query:
            mock_query.return_value = {
              "success": True,
              "mac": "00:11:22:33:44:55",
              "area": "LAN"
            }
            device = DeviceManager.create_user_device(
              user=self.user, ip="123.123.123.123", name="TestDevice"
            )
            self.assertIsNotNone(device)
            self.assertEqual(device.mac, "00:11:22:33:44:55")
            self.assertEqual(device.name, "TestDevice")
            self.assertFalse(device.whitelisted)
            self.assertEqual(device.user, self.user)
            self.assertEqual(device.ip, "123.123.123.123")
            self.assertEqual(device.area, "LAN")

    def test_create_user_device_invalid_ip(self):
        """
        Test the creation of a user device with an invalid MAC address
        """
        with self.assertRaises(ValidationError):
            with patch('langate.network.models.netcontrol.query') as mock_query:
                mock_query.return_value = {
                  "success": True,
                  "mac": "00:11:22:33:44:55",
                  "area": "LAN"
                }
                DeviceManager.create_user_device(
                  user=self.user, ip="123.123.123.823", name="TestDevice"
                )

    def test_create_user_device_no_name(self):
        """
        Test the creation of a user device with no name
        """
        with patch('langate.network.models.netcontrol.query') as mock_query, \
             patch('langate.network.models.generate_dev_name', return_value="GeneratedName") as mock_gen_name:
            mock_query.return_value = {
              "success": True,
              "mac": "00:11:22:33:44:55",
              "area": "LAN"
            }
            device = DeviceManager.create_user_device(
              user=self.user, ip="123.123.123.123", name=None
            )
            mock_gen_name.assert_called_once()
            self.assertEqual(device.name, "GeneratedName")

    def test_create_device_duplicate_mac(self):
        """
        Test the creation of a device with a duplicate MAC address
        """
        with patch('langate.network.models.netcontrol.query') as mock_query:
            mock_query.return_value = {
              "success": True,
              "mac": "00:11:22:33:44:55",
              "area": "LAN"
            }
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
          area="LAN"
        )
        self.device = Device.objects.create(
          mac="00:11:22:33:44:56",
          name="TestDeviceWhitelist",
          whitelisted=True
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
          'ip': '123.123.123.123',
          'user': 'testuser',
          'area': 'LAN'
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
          'ip': None,
          'user': None,
          'area': None
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

    def test_delete_device_success(self):
        """
        Test the deletion of a device
        """
        self.client.force_authenticate(user=self.user)

        with patch('langate.network.models.netcontrol.query') as mock_query:
            mock_query.return_value = {
              "success": True,
              "mac": self.device.mac,
            }
            response = self.client.delete(reverse('device-detail', args=[self.user_device.pk]))
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

            self.assertFalse(Device.objects.filter(pk=self.user_device.pk).exists())
            self.assertFalse(UserDevice.objects.filter(pk=self.user_device.pk).exists())

    def test_delete_device_not_found(self):
        """
        Test the deletion of a non-existent device
        """
        self.client.force_authenticate(user=self.user)

        url = reverse('device-detail', args=[999])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_device_no_auth(self):
        """
        Test the deletion of a device without authentication
        """
        response = self.client.delete(reverse('device-detail', args=[self.device.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_device_unauthorized(self):
        """
        Test the deletion of a device by an unauthorized user
        """
        self.client.force_authenticate(user=self.player)

        response = self.client.delete(reverse('device-detail', args=[self.device.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_device_success(self):
        """
        Test the update of a device
        """
        self.client.force_authenticate(user=self.user)

        new_data = {
          'mac': '00:11:22:33:44:57',
          'name': 'new_name'
        }
        with patch('langate.network.models.netcontrol.query') as mock_query:
            mock_query.return_value = {
              "success": True,
              "mac": new_data['mac'],
            }
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
              'ip': '123.123.123.123',
              'user': 'testuser',
              'area': 'LAN'
            },
            {
              'id': self.device.pk,
              'name': 'TestDeviceWhitelist',
              'mac': '00:11:22:33:44:56',
              'whitelisted': True,
              'ip': None,
              'user': None,
              'area': None
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
              'ip': '123.123.123.123',
              'user': 'testuser',
              'area': 'LAN',
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

    def test_post_device_success(self):
        """
        Test the creation of a device
        """
        self.client.force_authenticate(user=self.user)

        new_data = {
          'mac': '00:11:22:33:44:57',
          'name': 'new_name'
        }
        with patch('langate.network.models.netcontrol.query') as mock_query:
            mock_query.return_value = {
              "success": True,
              "mac": new_data['mac'],
            }
            response = self.client.post(reverse('device-list'), new_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            device = Device.objects.get(mac='00:11:22:33:44:57')
            self.assertEqual(device.name, 'new_name')

    def test_post_user_device_success(self):
        """
        Test the creation of a user device
        """
        self.client.force_authenticate(user=self.user)

        new_data = {
          'ip': '123.123.123.123',
          'name': 'new_name',
          'user': self.user.id,
        }

        with patch('langate.network.models.netcontrol.query') as mock_query:
            mock_query.return_value = {
              "success": True,
              "mac": "00:11:22:33:44:57",
              "area": "LAN"
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

class TestGetMark(TestCase):

  @patch('random.random')
  def test_get_mark_first_priority(self, mock_random):
    mock_random.return_value = 0.06
    expected_mark = SETTINGS["marks"][1]["value"]
    self.assertEqual(get_mark(), expected_mark)

  @patch('random.random')
  def test_get_mark_second_priority(self, mock_random):
    mock_random.return_value = 0.14
    expected_mark = SETTINGS["marks"][2]["value"]
    self.assertEqual(get_mark(), expected_mark)

  @patch('random.random')
  def test_get_mark_third_priority(self, mock_random):
    mock_random.return_value = 0.86
    expected_mark = SETTINGS["marks"][3]["value"]
    self.assertEqual(get_mark(), expected_mark)

  @patch('random.random')
  def test_get_mark_cannot_be_none(self, mock_random):
    for i in range(100):
      mock_random.return_value = (i+1)/100
      unexpected_mark = SETTINGS["marks"][0]["value"]
      self.assertNotEqual(get_mark(), unexpected_mark)

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

    @patch('langate.network.views.save_settings')
    #@patch('langate.network.views.SETTINGS')
    def test_patch_marks(self, mock_save_settings):
        #mock_settings.__getitem__.side_effect = self.SETTINGS.__getitem__
        mock_save_settings.side_effect = lambda x: None

        new_marks = [
          {"value": 102, "name": "Mark 3", "priority": 0.3},
          {"value": 103, "name": "Mark 4", "priority": 0.7}
        ]
        response = self.client.patch(self.url, new_marks, format='json')

        from langate.settings import SETTINGS as ORIGINAL_SETTINGS

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(ORIGINAL_SETTINGS["marks"]), 2)
        self.assertEqual(ORIGINAL_SETTINGS["marks"][0]["value"], 102)
        self.assertEqual(ORIGINAL_SETTINGS["marks"][1]["value"], 103)

    def test_patch_invalid_marks(self):
        invalid_marks = [
          {"value": 102, "name": "Mark 3", "priority": 0.3},
          {"value": 103, "name": "Mark 4", "priority": 0.6}
        ]
        response = self.client.patch(self.url, invalid_marks, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid mark")
