import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Notification } from '../api/generated/api';
import { getNotifications, markNotificationsAsRead } from '../services/socialService';

export interface GroupedNotification extends Notification {
  count: number;
}

export const notificationsQueryKey = ['notifications'] as const;

const getGroupKey = (notification: Notification): string => {
  switch (notification.notification_type as string) {
    case 'new_follower': return 'new_follower';
    case 'node_saved':
    case 'node_bought':
    case 'peer_review_received': return `${notification.notification_type}_${notification.research_node?.id}`;
    default: return String(notification.id);
  }
};

const getGroupedVerb = (notification: Notification, count: number): string => {
  if (count > 1) {
    switch (notification.notification_type as string) {
      case 'new_follower': return `${count} users started following you`;
      case 'node_saved': return `${count} users saved your research node`;
      case 'peer_review_received': return `${count} agents peer reviewed your node`;
    }
  }
  return notification.verb || '';
};

export const groupNotifications = (notifications: Notification[]): GroupedNotification[] => {
  const grouped: Record<string, Notification[]> = {};
  notifications.forEach(notification => (grouped[getGroupKey(notification)] ||= []).push(notification));
  return Object.values(grouped).map(group => ({
    ...group[0], count: group.length, verb: getGroupedVerb(group[0], group.length),
  }));
};

export function useNotifications() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: notificationsQueryKey, queryFn: getNotifications, select: groupNotifications });
  const markReadMutation = useMutation({
    mutationFn: markNotificationsAsRead,
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: notificationsQueryKey });
      const previousNotifications = queryClient.getQueryData<Notification[]>(notificationsQueryKey);
      queryClient.setQueryData<Notification[]>(notificationsQueryKey, notifications =>
        notifications?.map(notification => ({ ...notification, is_read: true })),
      );
      return { previousNotifications };
    },
    onError: (_error, _variables, context) => {
      queryClient.setQueryData(notificationsQueryKey, context?.previousNotifications);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: notificationsQueryKey }),
  });
  const notifications = query.data ?? [];
  return {
    notifications,
    unreadCount: notifications.filter(notification => !notification.is_read).length,
    isLoading: query.isLoading,
    error: query.error,
    markAllRead: markReadMutation.mutateAsync,
    isMarkingRead: markReadMutation.isPending,
  };
}
