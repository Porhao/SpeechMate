import { api } from "./api";

export interface AppNotification {
  id: string;
  kind: string;
  title: string;
  body: string;
  link: string | null;
  read: boolean;
  created_at: string;
}

export const notificationService = {
  list: () => api.get<{ unread: number; items: AppNotification[] }>("/notifications"),
  markRead: (id: string) => api.post<AppNotification>(`/notifications/${id}/read`, {}),
  markAllRead: () => api.post<{ ok: boolean }>("/notifications/read-all", {}),
};
