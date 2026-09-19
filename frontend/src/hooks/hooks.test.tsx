import React, { useRef } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useClickOutside } from './useClickOutside';
import { useAgentNameAvailability } from './useAgentNameAvailability';
import { groupNotifications, useNotifications } from './useNotifications';
import type { Notification } from '../api/generated/api';

const { checkAgentName, getNotifications, markNotificationsAsRead } = vi.hoisted(() => ({
  checkAgentName: vi.fn(),
  getNotifications: vi.fn(),
  markNotificationsAsRead: vi.fn(),
}));

vi.mock('../services/fetchService', () => ({ checkAgentName }));
vi.mock('../services/socialService', () => ({ getNotifications, markNotificationsAsRead }));

const NameAvailabilityDemo = ({ name, editingName }: { name: string; editingName?: string }) => {
  const { availability, isChecking } = useAgentNameAvailability(name, editingName);
  return <output>{`${availability}:${isChecking}`}</output>;
};

const NotificationsDemo = () => {
  const { notifications, unreadCount, markAllRead } = useNotifications();
  return <button onClick={() => markAllRead()}>{`${notifications.length}:${unreadCount}`}</button>;
};

const notification = (overrides: Partial<Notification> = {}): Notification => ({
  id: 1,
  notification_type: 'new_follower',
  is_read: false,
  verb: 'started following you',
  created_at: '2026-01-01T00:00:00Z',
  ...overrides,
} as Notification);

describe('useClickOutside', () => {
  it('dismisses on an outside click and Escape, but not while disabled', () => {
    const onDismiss = vi.fn();
    const Demo = ({ enabled }: { enabled: boolean }) => {
      const ref = useRef<HTMLDivElement>(null);
      useClickOutside(ref, onDismiss, { enabled });
      return <div ref={ref}>inside</div>;
    };
    const { rerender } = render(<Demo enabled />);

    fireEvent.mouseDown(screen.getByText('inside'));
    expect(onDismiss).not.toHaveBeenCalled();
    fireEvent.mouseDown(document.body);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onDismiss).toHaveBeenCalledTimes(2);

    rerender(<Demo enabled={false} />);
    fireEvent.mouseDown(document.body);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onDismiss).toHaveBeenCalledTimes(2);
  });
});

describe('useAgentNameAvailability', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    checkAgentName.mockReset();
  });

  it('does not validate short names and accepts an unchanged edit name', async () => {
    const { rerender } = render(<NameAvailabilityDemo name="ab" />);
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    expect(checkAgentName).not.toHaveBeenCalled();
    expect(screen.getByText('null:false')).toBeInTheDocument();

    rerender(<NameAvailabilityDemo name="Existing Agent" editingName="existing agent" />);
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    expect(checkAgentName).not.toHaveBeenCalled();
    expect(screen.getByText('true:false')).toBeInTheDocument();
    vi.useRealTimers();
  });
});

describe('notifications helpers', () => {
  beforeEach(() => {
    getNotifications.mockReset();
    markNotificationsAsRead.mockReset();
  });

  it('groups notifications and updates the unread count after marking read', async () => {
    expect(groupNotifications([notification(), notification({ id: 2 })])).toMatchObject([{ count: 2 }]);
    getNotifications
      .mockResolvedValueOnce([notification()])
      .mockResolvedValue([notification({ is_read: true })]);
    markNotificationsAsRead.mockResolvedValue(undefined);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><NotificationsDemo /></QueryClientProvider>);

    await waitFor(() => expect(screen.getByRole('button')).toHaveTextContent('1:1'));
    fireEvent.click(screen.getByRole('button'));
    await waitFor(() => expect(screen.getByRole('button')).toHaveTextContent('1:0'));
    expect(markNotificationsAsRead).toHaveBeenCalledOnce();
  });
});
