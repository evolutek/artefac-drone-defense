import { useEffect, useState } from 'react';
import { DroneLifecycleEvent } from '../types';

interface ToastNotification {
  id: number;
  message: string;
  type: 'spawning' | 'ready' | 'removed';
  droneId: string;
}

interface DroneEventToastProps {
  latestEvent: DroneLifecycleEvent | null;
}

export function DroneEventToast({ latestEvent }: DroneEventToastProps) {
  const [notifications, setNotifications] = useState<ToastNotification[]>([]);

  useEffect(() => {
    if (!latestEvent) return;

    // Create notification based on event type
    let message = '';
    let type: 'spawning' | 'ready' | 'removed' = 'spawning';

    if (latestEvent.type === 'drone_spawning') {
      message = `${latestEvent.drone_id} is spawning...`;
      type = 'spawning';
    } else if (latestEvent.type === 'drone_ready') {
      message = `${latestEvent.drone_id} is ready! 🚁`;
      type = 'ready';
    } else if (latestEvent.type === 'drone_removed') {
      message = `${latestEvent.drone_id} removed`;
      type = 'removed';
    }

    const notification: ToastNotification = {
      id: Date.now(),
      message,
      type,
      droneId: latestEvent.drone_id,
    };

    setNotifications(prev => [...prev, notification]);

    // Auto-remove after 4 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== notification.id));
    }, 4000);
  }, [latestEvent]);

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {notifications.map(notification => (
        <div
          key={notification.id}
          className={`
            px-6 py-3 rounded-lg shadow-lg transform transition-all duration-300
            animate-slide-in-right
            ${
              notification.type === 'spawning'
                ? 'bg-yellow-500 text-white'
                : notification.type === 'ready'
                ? 'bg-green-500 text-white'
                : 'bg-gray-500 text-white'
            }
          `}
        >
          <div className="flex items-center space-x-3">
            {notification.type === 'spawning' && (
              <svg
                className="animate-spin h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            )}
            {notification.type === 'ready' && (
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            )}
            {notification.type === 'removed' && (
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            )}
            <p className="font-semibold">{notification.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
