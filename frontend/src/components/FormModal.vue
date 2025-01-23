<script setup lang="ts">
import { ref } from 'vue';
import { useUserStore } from '@/stores/user.store';

const { create_temp_password } = useUserStore();

export interface Props {
  open: boolean;
  title: string;
  confirm?: boolean;
  fields: {
    name: string;
    key: string;
    value: string;
    type: string;
    choices?: { key: string; value: string }[];
    required?: boolean;
  }[];
  function: () => void;
}

const props = defineProps<Props>();
defineEmits(['update:open']);

const showPassword = ref<{ [key: string]: boolean }>({});

</script>

<template>
  <div
    v-show="props.open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    @click.self="$emit('update:open', false)"
    @keydown.escape="$emit('update:open', false)"
  >
    <form
      class="flex min-w-[20%] flex-col rounded-lg bg-theme-bg p-4"
      @submit.prevent="props.function"
    >
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-2xl text-white">
          {{ props.title }}
        </h2>
        <button
          class="float-right text-2xl text-gray-300"
          type="button"
          @click="$emit('update:open', false)"
        >
          &times;
        </button>
      </div>
      <div class="mb-4 flex flex-col gap-4">
        <div
          v-for="field in props.fields"
          :key="field.key"
          class="flex flex-col"
        >
          <label :for="field.key" class="text-sm text-gray-300">{{ field.name }}</label>
          <select
            v-if="field.choices"
            :id="field.key"
            v-model="field.value"
            class="rounded-md border border-black bg-theme-nav p-2 text-white"
            :required="field.required"
          >
            <option
              v-for="choice in field.choices"
              :key="choice.key"
              :value="choice.key"
            >
              {{ choice.value }}
            </option>
          </select>
          <textarea
            v-else-if="field.type === 'textarea'"
            :id="field.key"
            v-model="field.value"
            class="h-48 rounded-md border border-black bg-theme-nav p-2 text-white"
            :required="field.required"
          />
          <div v-else-if="field.type === 'checkbox'" class="flex items-center">
            <input
              :id="field.key"
              v-model="field.value"
              type="checkbox"
              class="ml-auto rounded-md border border-black bg-theme-nav p-2 text-white"
            />
          </div>
          <!-- If type is password, don't autocomplete with saved password -->
          <div
            v-else
            class="relative flex w-full items-center"
          >
            <input
              :id="field.key"
              v-model="field.value"
              :type="field.type === 'password' ? (showPassword[field.key] ? 'text' : 'password') : field.type"
              class="w-full rounded-md border border-black bg-theme-nav p-2 text-white"
              autocomplete="off"
              :required="field.required"
            />
            <!-- Button to hide / show the password -->
            <button
              v-if="field.type === 'password'"
              class="absolute right-8 top-2 text-white"
              type="button"
              @click="showPassword[field.key] = !showPassword[field.key]"
            >
              <fa-awesome-icon
                v-if="!showPassword[field.key]"
                icon="eye"
              />
              <fa-awesome-icon
                v-else
                icon="eye-slash"
              />
            </button>
            <!-- Button to regenerate a password -->
            <button
              v-if="field.type === 'password'"
              class="absolute right-2 top-2 text-white"
              type="button"
              @click="field.value = create_temp_password(); showPassword[field.key] = true"
            >
              <fa-awesome-icon
                icon="redo"
              />
            </button>
          </div>
        </div>
      </div>
      <div
        v-if="!props.confirm"
        class="flex justify-end"
      >
        <button
          class="mr-2 rounded-md bg-theme-nav px-4 py-2 text-white"
          type="button"
          @click="$emit('update:open', false)"
        >
          Annuler
        </button>
        <button
          class="rounded-md bg-blue-700 px-4 py-2 text-white"
          type="submit"
        >
          Valider
        </button>
      </div>
      <div
        v-else
        class="flex justify-end"
      >
        <button
          class="mr-2 rounded-md bg-blue-700 px-4 py-2 text-white"
          type="button"
          @click="$emit('update:open', false)"
        >
          Ok
        </button>
      </div>
    </form>
  </div>
</template>
