import type { UserDevice } from './device';

export enum UserRole {
  Player = 'player',
  Manager = 'manager',
  Guest = 'guest',
  Staff = 'staff',
  Admin = 'admin',
}

export interface User {
  id: number;
  last_login: Date;
  username: string;
  date_joined: Date;
  is_active: boolean;
  role: UserRole;
  max_device_nb: number;
  tournament?: string;
  team?: string;
  bypass: boolean;
  devices: UserDevice[];
}
