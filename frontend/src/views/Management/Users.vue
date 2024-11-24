<script setup lang="ts">
import ManagementMenu from '@/components/ManagementMenu.vue';
import PaginatedTable from '@/components/PaginatedTable.vue';
import type { Device } from '@/models/device';
import type { User } from '@/models/user';
import { UserRole } from '@/models/user';
import { useDeviceStore } from '@/stores/devices.store';
import { useNotificationStore } from '@/stores/notification.stores';
import { useUserStore } from '@/stores/user.store';

const {
  create_user, reset_password, delete_user, edit_user,
} = useUserStore();

const {
  change_userdevice_marks,
} = useDeviceStore();

const { addNotification } = useNotificationStore();

</script>

<template>
  <div class="m-4 flex flex-col">
    <div class="mb-5 border-b-2 border-gray-500 pb-2 text-4xl font-bold text-gray-300">
      Interface d'administration
    </div>
    <div class="flex flex-col md:flex-row">
      <ManagementMenu type="users"/>
      <PaginatedTable
        url="/user/users"
        :properties="[
          {
            name: '#',
            key: 'id',
            ordering: true,
          },
          {
            name: 'Pseudo',
            key: 'username',
            ordering: false,
          },
          {
            name: 'Role',
            key: 'role',
            ordering: false,
          },
          {
            name: 'Nombre d\'appareils connectés',
            key: 'device_nb',
            ordering: true,
            function: (user: unknown) => (user as User).devices.length.toString(),
          },
          {
            name: 'Nombre max d\'appareils',
            key: 'max_device_nb',
            ordering: true,
          },
          {
            name: 'Tournoi',
            key: 'tournaments',
            ordering: false,
          },
          {
            name: 'Equipe',
            key: 'team',
            ordering: false,
          },
          {
            name: 'Accès aux sites bloqués',
            key: 'bypass',
            ordering: false,
          },
        ]"
        :create="{
          modal: {
            title: 'Ajouter un utilisateur',
            fields: [
              {
                name: 'Pseudo',
                key: 'username',
                type: 'text',
                required: true,
              },
              {
                name: 'Role',
                key: 'role',
                type: 'text',
                required: true,
                choices: [
                  {
                    key: UserRole.Player,
                    value: 'Joueur',
                  },
                  {
                    key: UserRole.Manager,
                    value: 'Manager',
                  },
                  {
                    key: UserRole.Guest,
                    value: 'Invité',
                  },
                  {
                    key: UserRole.Staff,
                    value: 'Staff',
                  },
                  {
                    key: UserRole.Admin,
                    value: 'Admin',
                  },
                ],
                value: UserRole.Player,
              },
              {
                name: 'Mot de passe',
                key: 'password',
                type: 'password',
                required: true,
              },
              {
                name: 'Tournoi',
                key: 'tournaments',
                type: 'text',
                required: false,
              },
              {
                name: 'Equipe',
                key: 'team',
                type: 'text',
                required: false,
              },
              {
                name: 'Donner accès aux sites bloqués',
                key: 'bypass',
                type: 'checkbox',
                required: false,
              },
            ],
          },
          function: async (data) => {
            return await create_user(data as unknown as User);
          },
        }"
        :pagination="true"
        :search="true"
        :actions="[
          {
            hint: 'Modifier l\'utilisateur',
            icon: 'pencil',
            key: 'update',
            modal: {
              title: 'Modifier l\'utilisateur',
              fields: [
                {
                  name: 'Pseudo',
                  key: 'username',
                  type: 'text',
                },
                {
                  name: 'Nombre d\'appareils autorisés',
                  key: 'max_device_nb',
                  type: 'number',
                },
                {
                  name: 'Role',
                  key: 'role',
                  type: 'text',
                  choices: [
                    {
                      key: UserRole.Player,
                      value: 'Joueur',
                    },
                    {
                      key: UserRole.Manager,
                      value: 'Manager',
                    },
                    {
                      key: UserRole.Guest,
                      value: 'Invité',
                    },
                    {
                      key: UserRole.Staff,
                      value: 'Staff',
                    },
                    {
                      key: UserRole.Admin,
                      value: 'Admin',
                    },
                  ],
                },
                {
                  name: 'Tournoi',
                  key: 'tournaments',
                  type: 'text',
                },
                {
                  name: 'Equipe',
                  key: 'team',
                  type: 'text',
                },
                {
                  name: 'Donner accès aux sites bloqués',
                  key: 'bypass',
                  type: 'checkbox',
                  required: false,
                },
              ],
            },
            function: async (device, fields) => {
              if (await edit_user((device as unknown as User).id, fields as unknown as User)) {
                addNotification('L\'utilisateur a bien été mis à jour', 'info');
              }
            },
          },
          {
            hint: 'Changer le mot de passe',
            icon: 'key',
            key: 'reset',
            modal: {
              title: 'Changer le mot de passe',
              fields: [
                {
                  name: 'Nouveau mot de passe',
                  key: 'password',
                  type: 'password',
                },
              ],
            },
            function: async (device, fields) => {
              if (await reset_password((device as unknown as User).id, fields.password)) {
                addNotification('Le mot de passe a bien été changé', 'info');
              }
            },
          },
          {
            hint: 'Modifier les marks',
            icon: 'location-dot',
            key: 'devices',
            modal: {
              title: 'Modifier les marks',
              fields: (devices: unknown) => {
                return (devices as Device[]).map((device: any) => ({
                  name: `Mark de ${device.name} (${device.ip})`,
                  key: device.id,
                  type: 'number',
                  value: device.mark,
                  required: true,
                  device,
                }));
              },
            },
            function: async (user, fields) => {
              if (await change_userdevice_marks(fields)) {
                addNotification('Les marks ont bien été modifiés', 'info');
              }
            },
          },
          {
            hint: 'Supprimer l\'utilisateur',
            icon: 'trash-can',
            key: 'delete',
            modal: {
              title: 'Supprimer l\'utilisateur',
              fields: [
                {
                  name: 'Voulez-vous vraiment supprimer cet utilisateur ?',
                  key: 'confirm',
                  type: 'hidden',
                },
              ],
            },
            function: async (device, fields) => {
              if (await delete_user((device as unknown as User).id)) {
                addNotification('L\'utilisateur a bien été supprimé', 'info');
              }
            },
          },
        ]"
      />
    </div>
  </div>
</template>
