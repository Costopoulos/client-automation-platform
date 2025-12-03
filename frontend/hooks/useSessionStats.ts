import { useState, useEffect } from "react";

const STORAGE_KEY = "techflow_session_stats";

interface SessionStats {
  approvedCount: number;
  rejectedCount: number;
}

const defaultStats: SessionStats = {
  approvedCount: 0,
  rejectedCount: 0,
};

/**
 * Custom hook to manage session statistics with localStorage persistence
 * 
 * Statistics persist across page refreshes and browser sessions.
 * Can be manually reset using the reset function.
 */
export function useSessionStats() {
  const [stats, setStats] = useState<SessionStats>(() => {
    // Initialize from localStorage on mount
    if (typeof window === "undefined") return defaultStats;

    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (error) {
      console.error("Failed to load session stats from localStorage:", error);
    }
    return defaultStats;
  });

  // Persist to localStorage whenever stats change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stats));
    } catch (error) {
      console.error("Failed to save session stats to localStorage:", error);
    }
  }, [stats]);

  const incrementApproved = () => {
    setStats((prev) => ({
      ...prev,
      approvedCount: prev.approvedCount + 1,
    }));
  };

  const incrementRejected = () => {
    setStats((prev) => ({
      ...prev,
      rejectedCount: prev.rejectedCount + 1,
    }));
  };

  const reset = () => {
    setStats(defaultStats);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.error("Failed to clear session stats from localStorage:", error);
    }
  };

  return {
    approvedCount: stats.approvedCount,
    rejectedCount: stats.rejectedCount,
    incrementApproved,
    incrementRejected,
    reset,
  };
}
