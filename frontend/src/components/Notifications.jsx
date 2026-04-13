import React, { useState, useEffect, useRef } from 'react';
import { getNotifications, markNotificationsAsRead } from '../services/socialService';
import { FulfillmentIcon, SavedIcon, VisitsIcon, FollowerIcon, RatedIcon, CustomIcon } from './Icons';

const Notifications = () => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    fetchNotifications();
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const fetchNotifications = async () => {
    try {
      const data = await getNotifications();
      const groupedNotifications = groupNotifications(data);
      setNotifications(groupedNotifications);
      setUnreadCount(groupedNotifications.filter(n => !n.is_read).length);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    }
  };

  const groupNotifications = (notifications) => {
    const grouped = {};
    notifications.forEach(notification => {
      const key = getGroupKey(notification);
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(notification);
    });
    return Object.values(grouped).map(group => {
      const first = group[0];
      return {
        ...first,
        count: group.length,
        verb: getGroupedVerb(first.notification_type, group.length),
      };
    });
  };

  const getGroupKey = (notification) => {
    switch (notification.notification_type) {
      case 'new_follower':
        return 'new_follower';
      case 'node_saved':
      case 'node_bought':
      case 'peer_review_received':
        return `${notification.notification_type}_${notification.research_node?.id}`;
      default:
        return notification.id;
    }
  };

  const getGroupedVerb = (type, count) => {
    switch (type) {
      case 'new_follower':
        return count === 1 ? 'started following you' : `${count} users started following you`;
      case 'node_saved':
        return count === 1 ? 'saved your research node' : `${count} users saved your research node`;
      case 'assignment_received':
        return 'received a new research assignment';
      case 'payout_received':
        return 'received a bounty payout';
      case 'peer_review_received':
        return count === 1 ? 'peer reviewed your node' : `${count} agents peer reviewed your node`;
      default:
        return '';
    }
  };

  const handleToggle = async () => {
    setIsOpen(!isOpen);
    if (!isOpen && unreadCount > 0) {
      try {
        await markNotificationsAsRead();
        setUnreadCount(0);
      } catch (error) {
        console.error("Failed to mark notifications as read:", error);
      }
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'new_follower':
        return <FollowerIcon />;
      case 'node_saved':
        return <SavedIcon />;
      case 'payout_received':
        return <FulfillmentIcon />;
      case 'peer_review_received':
        return <RatedIcon />;
      case 'high_views':
        return <VisitsIcon />;
      case 'custom':
        return <CustomIcon />;
      default:
        return <CustomIcon />;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button onClick={handleToggle} className="relative p-2 flex flex-row gap-2 rounded-full bg-gradient-to-r from-blue-300 to-indigo-400 hover:from-blue-400 hover:to-indigo-500">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        <div className="font-semibold hidden sm:inline">Notifications</div>
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-red-100 transform translate-x-1/2 -translate-y-1/2 bg-red-400 rounded-full">
            {unreadCount}
          </span>
        )}
      </button>
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-zinc-800 rounded-md shadow-lg z-20">
          {notifications.length > 0 ? (
            <div className="max-h-96 overflow-y-auto">
              {notifications.map((notification) => (
                <div key={notification.id} className={`px-4 py-2 rounded-md ${notification.is_read ? "" : "bg-zinc-700"} hover:bg-zinc-600 flex items-start`}>
                  <div className="flex-shrink-0 mr-3 mt-1">
                    {getNotificationIcon(notification.notification_type)}
                  </div>
                  <div className="flex-grow min-w-0">
                    <p className="text-sm truncate">{notification.count === 1 ? notification.actor?.username : ""} {notification.verb}</p>
                    {notification.research_node && (
                      <p className="text-sm truncate">{notification.research_node.title}</p>
                    )}
                    <p className="text-xs text-gray-500">
                      {new Date(notification.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-4 font-semibold text-zinc-200">No notifications yet</p>
          )}
        </div>
      )}
    </div>
  );
};

export default Notifications;


