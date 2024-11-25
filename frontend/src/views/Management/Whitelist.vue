<script setup lang="ts">
import ManagementMenu from '@/components/ManagementMenu.vue';
import PaginatedTable from '@/components/PaginatedTable.vue';
import type { Device } from '@/models/device';
import { useDeviceStore } from '@/stores/devices.store';
import { useNotificationStore } from '@/stores/notification.stores';

const {
  createDevice, createDevicesFromList, deleteDevice, editDevice,
} = useDeviceStore();

const { addNotification } = useNotificationStore();

</script>

<template>
  <div class="m-4 flex flex-col">
    <div class="mb-5 border-b-2 border-gray-500 pb-2 text-4xl font-bold text-gray-300">
      Interface d'administration
    </div>
    <div class="flex flex-col md:flex-row">
      <ManagementMenu type="whitelist"/>
      <PaginatedTable
        url="/network/devices/whitelist/"
        :properties="[
          {
            name: '#',
            key: 'id',
            ordering: true,
          },
          {
            name: 'MAC',
            key: 'mac',
            ordering: false,
          },
          {
            name: 'Nom',
            key: 'name',
            ordering: false,
          },
          {
            name: 'Mark',
            key: 'mark',
            ordering: true,
          },
          {
            name: 'Accès aux sites bloqués',
            key: 'bypass',
            ordering: false,
          },
        ]"
        :pagination="true"
        :search="true"
        :actions="[
          {
            hint: 'Modifier l\'appareil',
            icon: 'pencil',
            key: 'update',
            modal: {
              title: 'Modifier l\'appareil',
              fields: [
                {
                  name: 'Nom',
                  key: 'name',
                  type: 'text',
                  required: true,
                },
                {
                  name: 'MAC',
                  key: 'mac',
                  type: 'text',
                  required: true,
                },
                {
                  name: 'Mark',
                  key: 'mark',
                  type: 'number',
                  required: true,
                },
                {
                  name: 'Donner accès aux sites bloqués',
                  key: 'bypass',
                  type: 'checkbox',
                  required: false,
                },
              ],
            },
            function: async (device, data) => {
              const success = await editDevice((device as unknown as Device).id, data as unknown as Device)
              if (success) {
                addNotification('L\'appareil a bien été modifié', 'info');
              }
              return success;
            },
          },
          {
            hint: 'Supprimer l\'appareil',
            icon: 'trash-can',
            key: 'delete',
            modal: {
              title: 'Supprimer l\'appareil',
              fields: [
                {
                  name: 'Voulez-vous vraiment supprimer cet appareil ?',
                  key: 'confirm',
                  type: 'hidden',
                },
              ],
            },
            function: async (device, fields) => {
              const success = await deleteDevice((device as unknown as Device).id);
              if (success) {
                addNotification('L\'appareil a bien été supprimé', 'info');
              }
              return success;
            },
          },
        ]"
        :create="{
          multiple: async (data) => {
            const success = await createDevicesFromList(data as unknown as Device[]);
            if (success) {
              addNotification('Les appareils ont bien été ajoutés', 'info');
            }
            return success;
          },
          modal: {
            title: 'Ajouter à la whitelist',
            fields: [
              {
                name: 'Nom',
                key: 'name',
                type: 'text',
                required: true,
              },
              {
                name: 'MAC',
                key: 'mac',
                type: 'text',
                required: true,
              },
              {
                name: 'Mark',
                key: 'mark',
                type: 'number',
                required: true,
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
            const success = await createDevice(data as unknown as Device);
            if (success) {
              addNotification('L\'appareil a bien été ajouté', 'info');
            }
            return success;
          },
        }"
      />
    </div>
  </div>
</template>
