<script setup lang="ts">
import axios from 'axios';
import {
  computed, onMounted, reactive, type Ref,
  ref,
} from 'vue';
import FormModal from '@/components/FormModal.vue';
import { useNotificationStore } from '@/stores/notification.stores';

const { addNotification } = useNotificationStore();

const searchValue = ref('');
const dataSet = ref([]) as Ref<{ [key: string]: string }[]>;

export interface Props {
  properties: {
    name: string;
    key: string;
    ordering: boolean;
    function?: (data: unknown) => string;
  }[];
  url?: string;
  data?: { [key: string]: string }[];
  create?: {
    multiple?: (
      (fields: {
        [key: string]: string;
      }[]) => Promise<string | boolean | void>
    );
    modal: {
      title: string;
      fields: {
        name: string;
        key: string;
        type: string;
        value?: string;
        choices?: { key: string; value: string }[];
        required?: boolean;
      }[];
    };
    function: (
      (fields: {
        [key: string]: string;
      }) => Promise<string | boolean | void>
    );
  };
  pagination: boolean;
  search: boolean;
  actions?: {
    hint: string;
    key: string;
    icon: string;
    modal?: {
      title: string;
      fields: {
        name: string;
        key: string;
        type: string;
        choices?: { key: string; value: string }[];
        required?: boolean;
      }[] | ((data:unknown) => {
        name: string;
        key: string;
        value: string;
        type: string;
        choices?: { key: string; value: string }[];
        required?: boolean;
      }[]);
    };
    function: (
      (object: { [key: string]: string }) => Promise<string | boolean | void>
    ) | (
      (
        object: { [key: string]: string },
        fields: {
          [key: string]: string;
        }
      ) => Promise<string | boolean | void>
    );
  }[];
}

const props = defineProps<Props>();

// ------- Table -------
const tabledata = reactive({
  loading: true as boolean,
  objects: [] as { [key: string]: string }[],
  currentPage: 0 as number,
  pageSize: 10 as number,
  total: 0 as number,
  order: '',
});

const totalPages = computed(() => Math.ceil(tabledata.total / tabledata.pageSize));

const paginatedData = computed(() => {
  if (props.pagination === false) return tabledata.objects;
  const start = (tabledata.currentPage - 1) * tabledata.pageSize;
  const end = start + tabledata.pageSize;
  return tabledata.objects.slice(start, end);
});

const getProperty = (
  object: { [key: string]: string },
  key: string,
  fct?: (data: unknown) => string,
) => {
  if (fct) return fct(object);
  if (typeof object[key] === 'boolean') return object[key] ? '✔' : '✘';
  if (object[key] !== undefined) return object[key];
  return '';
};

const fetchData = async (page_number: number) => {
  tabledata.loading = true;
  if (!props.data && props.url && props.pagination) {
    if (tabledata.order === '') {
      if (props.properties[0].function) {
        tabledata.order = props.properties[0].function(dataSet.value[0]);
      } else {
        tabledata.order = props.properties[0].key;
      }
    }

    let start = (page_number - 1) * tabledata.pageSize;
    let { url } = props;
    if (url.includes('?')) {
      url += '&';
    } else {
      url += '?';
    }
    if (page_number !== -1) {
      for (let i = 0; i < start; i += 1) {
        if (!tabledata.objects[i]) tabledata.objects.push({});
      }
      url += `page=${page_number}&page_size=${tabledata.pageSize}&order=${tabledata.order}&filter=${searchValue.value}`;
    } else {
      start = 0;
      url += `page=1&page_size=${tabledata.pageSize}&order=${tabledata.order}&filter=${searchValue.value}`;
    }

    axios.get<{
      results: { [key: string]: string }[];
      count: number;
    }>(url)
      .then((response) => {
        tabledata.total = response.data.count;
        if (page_number !== -1) {
          tabledata.objects.splice(start, response.data.results.length, ...response.data.results);
          tabledata.currentPage = page_number;
        } else {
          tabledata.objects = response.data.results;
          tabledata.currentPage = 1;
        }
        tabledata.loading = false;
      })
      .catch((error) => {
        addNotification(
          `Erreur lors de la récupération des données: ${error}`,
          'error',
        );
      });
  } else if (props.data || (props.url && !props.pagination)) {
    if (tabledata.order === '') {
      if (props.properties[0].function) {
        tabledata.order = props.properties[0].function(dataSet.value[0]);
      } else {
        tabledata.order = props.properties[0].key;
      }
    }

    // Set dataset, allow ordering and searching
    if (props.data && props.data.length > 0) {
      dataSet.value = props.data;
    }
    tabledata.objects = dataSet.value;
    // Fuzzy search on all properties
    if (searchValue.value) {
      tabledata.objects = tabledata.objects.filter((object) => props.properties.some((property) => {
        if (property.function) {
          return property.function(object).toLowerCase().includes(searchValue.value.toLowerCase());
        }
        if (object[property.key].toString().toLowerCase().includes(searchValue.value.toLowerCase())) {
          return true;
        }
        return false;
      }));
    }

    // order by the first property
    tabledata.objects.sort((a, b) => {
      if (tabledata.order[0] === '-') {
        return a[tabledata.order.slice(1)] > b[tabledata.order.slice(1)] ? -1 : 1;
      }
      return a[tabledata.order] > b[tabledata.order] ? 1 : -1;
    });

    tabledata.currentPage = 1;
    tabledata.total = tabledata.objects.length;
    tabledata.loading = false;
  } else {
    addNotification(
      'Erreur lors de l\'initialisation de la table',
      'error',
    );
  }
};

const GetPage = async (page_number: number) => {
  // if Data is already on the page, don't fetch it again
  if (
    tabledata.objects[(page_number - 1) * tabledata.pageSize]
    && tabledata.objects[(page_number - 1) * tabledata.pageSize].id
  ) {
    tabledata.currentPage = page_number;
    return;
  }
  await fetchData(page_number);
};

const prevPage = async () => {
  if (tabledata.currentPage > 1) {
    await GetPage(tabledata.currentPage - 1);
  }
};

const nextPage = async () => {
  if (tabledata.currentPage < totalPages.value) {
    await GetPage(tabledata.currentPage + 1);
  }
};

const changeNumberPerPage = async (event: Event) => {
  // Reset the objects list, set the number per page, go to the first page and fetch the data again
  tabledata.pageSize = parseInt((event.target as HTMLSelectElement)?.value, 10);
  await fetchData(-1);
};

const sortByProperty = async (property: string) => {
  if (tabledata.order === property) {
    tabledata.order = `-${property}`;
  } else {
    tabledata.order = property;
  }
  await fetchData(-1);
};

const dynamicSearch = async () => {
  await fetchData(-1);
};

onMounted(async () => {
  if (props.url && !props.data && !props.pagination) {
    const response = await axios.get<{ [key: string]: string }[]>(`${props.url}?filter=${searchValue.value}`);
    dataSet.value = response.data;
  }
  await fetchData(1);
});

// ------- Modal -------
const modal = reactive({
  open: false,
  title: '',
  fields: [] as {
    name: string;
    key: string;
    value: string;
    type: string;
    choices?: { key: string; value: string }[];
    required?: boolean;
  }[],
  function: async () => {},
});

const confirm_modal = reactive({
  open: false,
  title: '',
  fields: [] as {
    name: string;
    key: string;
    value: string;
    type: string;
    choices?: { key: string; value: string }[];
    required?: boolean;
  }[],
  function: async () => {},
});

const openFormModal = (
  action: {
    hint: string;
    key: string;
    icon: string;
    modal?: {
      title: string;
      fields: {
        name: string;
        key: string;
        type: string;
        choices?: { key: string; value: string }[];
        required?: boolean;
      }[] | ((data:unknown) => {
        name: string;
        key: string;
        value: string;
        type: string;
        choices?: { key: string; value: string }[];
        required?: boolean;
      }[]);
    };
    function: (
      (object: { [key: string]: string }) => Promise<string | boolean | void>
    ) | (
      (object: { [key: string]: string }, fields: {
        [key: string]: string;
      }) => Promise<string | boolean | void>
    );
  },
  object: { [key: string]: string },
) => {
  if (action.modal) {
    // if modal.fields is a function, call it with the object
    if (typeof action.modal.fields === 'function') {
      modal.fields = action.modal.fields(object[action.key]);
    } else {
      modal.fields = action.modal.fields.map((field) => ({
        name: field.name,
        key: field.key,
        value: object[field.key],
        choices: field.choices,
        type: field.type,
        required: field.required,
      }));
    }

    modal.function = async () => {
      const data: { [key: string]: string } = {};

      modal.fields.forEach((field) => {
        if (field.value !== '') {
          data[field.key] = field.value;
        }
      });
      const confirm = await action.function(object, data);
      // if the function returns a string, open a confirmation modal
      if (typeof confirm === 'string') {
        confirm_modal.title = 'Confirmation';
        confirm_modal.fields = [
          {
            name: confirm,
            key: 'confirmation',
            value: '',
            type: 'hidden',
          },
        ];
        confirm_modal.open = true;
      }
      // if the function returns a boolean, fetch the data
      if (confirm !== false) {
        await fetchData(-1);
        modal.open = false;
      }
    };
    modal.title = action.modal.title;
    modal.open = true;
  } else {
    (
      action.function as (
        (object: { [key: string]: string }) => void
      )
    )(object);
  }
};

const openFormModalCreate = (
  create: {
    modal: {
      title: string;
      fields: {
        name: string;
        key: string;
        type: string;
        value?: string;
        choices?: { key: string; value: string }[];
        required?: boolean;
      }[];
    };
    function: (
      (fields: {
        [key: string]: string;
      }) => Promise<string | boolean | void>
    );
  },
) => {
  modal.fields = create.modal.fields.map((field) => ({
    name: field.name,
    key: field.key,
    value: field.value || '',
    type: field.type,
    choices: field.choices,
    required: field.required,
  }));
  modal.function = async () => {
    const data: { [key: string]: string } = {};

    modal.fields.forEach((field) => {
      if (field.value !== '') {
        data[field.key] = field.value;
      }
    });
    let confirm = await create.function(data);
    // if the function returns a string, open a confirmation modal
    if (typeof confirm === 'string') {
      confirm_modal.title = 'Confirmation';
      confirm_modal.fields = [
        {
          name: confirm,
          key: 'confirmation',
          value: '',
          type: 'hidden',
        },
      ];
      confirm_modal.function = async () => {
        confirm = await create.function(data);
        if (confirm !== false) {
          await fetchData(-1);
          modal.open = false;
        }
        confirm_modal.open = false;
      };
      confirm_modal.open = true;
    }
    // if the function returns a boolean, fetch the data
    if (confirm !== false) {
      await fetchData(-1);
      modal.open = false;
    }
  };
  modal.title = create.modal.title;
  modal.open = true;
};

// Creation of multiple objects if allowed (e.g. multiple whitelist device)
// Open the modal with only one text field
// The format should be "property1|property2|property3|..."
const openFormModalCreateMultiple = (
  create: {
    modal: {
      title: string;
      fields: {
        name: string;
        key: string;
        type: string;
      }[];
    };
    multiple?: (
      (fields: {
        [key: string]: string;
      }[]) => Promise<string | boolean | void>);
  },
) => {
  // create the name of the unique field from the properties
  const name = create.modal.fields.map((field) => field.name).join(' | ');

  modal.fields = [
    {
      name,
      key: 'multiple',
      value: '',
      type: 'textarea',
    },
  ];
  modal.function = async () => {
    // verify the format of the unique field
    if (
      !modal.fields[0].value.includes('|')
    ) {
      addNotification(
        'Le format n\'est pas correct',
        'error',
      );
      return;
    }

    // Create the fields from the unique field
    const fields: {
      name: string;
      key: string;
      value: string;
      type: string;
    }[][] = [];
    modal.fields[0].value.split('\n').forEach((line) => {
      const values = line.split('|');
      if (values.length !== create.modal.fields.length) {
        addNotification(
          'Le format n\'est pas correct',
          'error',
        );
        return;
      }
      const field = create.modal.fields.map((f, index) => ({
        name: f.name,
        key: f.key,
        value: values[index].trim(),
        type: f.type,
      }));
      fields.push(field);
    });

    // When fields are valid, create the objects one by one
    if (create.multiple) {
      const datas: { [key: string]: string }[] = [];
      fields.forEach((field) => {
        const data: { [key: string]: string } = {};
        field.forEach((f) => {
          if (f.value !== '') {
            data[f.key] = f.value;
          }
        });
        datas.push(data);
      });
      await create.multiple(datas);
    }
    await fetchData(-1);
    modal.open = false;
  };
  modal.title = create.modal.title;
  modal.open = true;
};

</script>

<template>
  <div class="flex flex-1 flex-col">
    <div class="m-2 flex flex-1 flex-col gap-2">
      <div class="flex flex-col justify-between gap-2 md:flex-row">
        <div
          v-memo="[
            tabledata.pageSize,
          ]"
          class="flex gap-2"
        >
          <div
            v-if="props.pagination"
            class="flex items-center gap-2"
          >
            <label for="pageSize" class="text-white">
              Nombre par pages :
            </label>
            <select
              id="pageSize"
              class="h-8 w-auto rounded-lg border border-zinc-800 bg-table py-0 pr-6 text-xs text-white"
              @change="changeNumberPerPage"
            >
              <option value="10">
                10
              </option>
              <option value="25">
                25
              </option>
              <option value="50">
                50
              </option>
              <option value="100">
                100
              </option>
            </select>
          </div>
        </div>
        <div
          class="flex gap-2 md:flex-row"
          :class="{
            'flex-col': props.create && props.create.multiple,
          }"
        >
          <div
            class="flex flex-1 flex-col justify-center"
          >
            <label
              for="searchInput"
              class="text-white"
              hidden
            >
              Rechercher:
            </label>
            <input
              v-if="props.search"
              id="searchInput"
              v-model="searchValue"
              class="rounded-lg border border-zinc-800 bg-table p-2 text-white"
              type="text"
              placeholder="Rechercher"
              @input="dynamicSearch"
            />
          </div>
          <div
            class="flex flex-row justify-center gap-2"
          >
            <div
              class="flex flex-col justify-center"
            >
              <button
                v-if="props.create"
                class="rounded-lg bg-blue-500 p-2 text-white"
                type="button"
                @click="openFormModalCreate(props.create)"
              >
                Ajouter
              </button>
            </div>
            <div
              class="flex flex-col justify-center"
            >
              <button
                v-if="props.create && props.create.multiple"
                class="rounded-lg bg-blue-500 p-2 text-white"
                type="button"
                @click="openFormModalCreateMultiple(props.create)"
              >
                Ajouter plusieurs
              </button>
            </div>
          </div>
        </div>
      </div>
      <div class="flex flex-row justify-between overflow-x-auto overflow-y-hidden md:overflow-x-scroll">
        <table
          class="w-full rounded-lg border border-black bg-table text-gray-300"
        >
          <thead
            v-memo="[
              props.properties,
              tabledata.order,
            ]"
            class="bg-zinc-800"
          >
            <tr>
              <th
                v-for="property in props.properties"
                :key="property.key"
                class="border-2 border-zinc-800 px-2"
                :class="{
                  'cursor-pointer': property.ordering,
                }"
              >
                <div
                  class="flex items-center justify-between"
                  @click="property.ordering && sortByProperty(property.key)"
                  @keydown.enter="property.ordering && sortByProperty(property.key)"
                >
                  {{ property.name }}
                  <div
                    v-if="property.ordering"
                  >
                    <span
                      v-if="tabledata.order === property.key || tabledata.order === `-${property.key}`"
                      class="ml-2 text-blue-500"
                    >
                      <fa-awesome-icon
                        v-if="tabledata.order === property.key"
                        icon="sort-up"
                      />
                      <fa-awesome-icon
                        v-else
                        icon="sort-down"
                      />
                    </span>
                    <span v-else class="ml-2">
                      <fa-awesome-icon
                        icon="sort"
                        class="text-white"
                      />
                    </span>
                  </div>
                </div>
              </th>
              <th
                v-if="props.actions"
                class="border-2 border-zinc-800"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody
            v-memo="[
              paginatedData,
              props.properties,
              props.actions,
              tabledata.loading,
            ]"
            class="relative"
            :class="{
              'h-8': tabledata.loading,
            }"
          >
            <tr
              v-show="tabledata.loading"
              class="absolute left-0 top-0 z-10 flex size-full items-center justify-center gap-2 bg-zinc-800/70 text-2xl"
            >
              Chargement
              <fa-awesome-icon
                icon="spinner"
                class="animate-spin"
              />
            </tr>
            <tr v-for="(object, index) in paginatedData" :key="object.id">
              <td
                v-for="property in props.properties"
                :key="property.key"
                class="border-2 border-zinc-800 pl-2"
              >
                {{ getProperty(object, property.key, property.function) }}
              </td>
              <td
                v-if="props.actions"
                class="relative w-[4%] border-2 border-zinc-800 px-2"
              >
                <div class="flex items-center justify-center gap-2">
                  <div
                    v-for="action in props.actions"
                    :key="action.key"
                    class="group size-8 cursor-pointer rounded bg-gray-500 p-1 text-center hover:bg-gray-600"
                    @click="openFormModal(action, object)"
                    @keydown.enter="openFormModal(action, object)"
                  >
                    <fa-awesome-icon
                      :icon="action.icon"
                      class="text-white"
                    />
                    <div
                      class="pointer-events-none absolute right-[-40px] z-20 mr-10 mt-10 w-32 rounded bg-gray-800 p-2 text-xs text-white opacity-0 transition-opacity duration-200 group-hover:opacity-100"
                      :class="{
                        'bottom-8': index === paginatedData.length - 1,
                        'top-0': index !== paginatedData.length - 1,
                      }"
                    >
                      {{ action.hint }}
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div
      v-if="props.pagination && totalPages > 1"
      v-memo="[
        tabledata.currentPage,
        totalPages,
      ]"
      class="flex flex-col items-center justify-between md:flex-row"
    >
      <div
        class="hidden gap-2 text-center md:block md:text-left"
      >
        Page {{ tabledata.currentPage }} / {{ totalPages }}
      </div>
      <div class="flex justify-between gap-2 md:justify-end">
        <button
          :class="{
            invisible: tabledata.currentPage <= 1,
          }"
          type="button"
          @click="prevPage"
        >
          Previous
        </button>
        <div class="flex gap-2">
          <button
            type="button"
            class="hidden size-8 rounded-lg text-blue-500 md:block"
            :class="{
              'bg-blue-600 text-white': tabledata.currentPage === 1,
              invisible: tabledata.currentPage <= 2,
            }"
            @click="GetPage(1)"
          >
            1
          </button>
          <button
            type="button"
            class="hidden size-8 rounded-lg text-blue-500 md:block"
            :class="{
              invisible: tabledata.currentPage < 3,
            }"
          >
            ...
          </button>
          <button
            v-for="i in [-1, 0, 1]"
            :key="i"
            type="button"
            class="size-8 rounded-lg text-blue-500"
            :class="{
              'bg-blue-600 text-white': i === 0,
              invisible: tabledata.currentPage + i < 1 || tabledata.currentPage + i > totalPages,
              'hidden md:block': i === -1 || i === 1,
            }"
            @click="GetPage(i + tabledata.currentPage)"
          >
            {{ i + tabledata.currentPage }}
          </button>
          <button
            type="button"
            class="hidden size-8 rounded-lg text-blue-500 md:block"
            :class="{
              invisible: tabledata.currentPage > totalPages - 2,
            }"
          >
            ...
          </button>

          <button
            type="button"
            class="hidden size-8 rounded-lg text-blue-500 md:block"
            :class="{
              'bg-blue-600 text-white': tabledata.currentPage === totalPages,
              invisible: tabledata.currentPage >= totalPages - 1,
            }"
            @click="GetPage(totalPages)"
          >
            {{ totalPages }}
          </button>
        </div>
        <button
          :class="{
            invisible: tabledata.currentPage >= totalPages,
          }"
          type="button"
          @click="nextPage"
        >
          Next
        </button>
      </div>
    </div>
  </div>
  <FormModal
    :open="modal.open"
    :title="modal.title"
    :fields="modal.fields"
    :function="modal.function"
    @update:open="modal.open = $event"
  />
  <FormModal
    :confirm="true"
    :open="confirm_modal.open"
    :title="confirm_modal.title"
    :fields="confirm_modal.fields"
    :function="confirm_modal.function"
    @update:open="confirm_modal.open = $event"
  />
</template>
