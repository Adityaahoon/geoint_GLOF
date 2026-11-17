import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "../api/client";
import type { HealthResponse, StudyAreaResponse } from "../api/types";

interface AppContextValue {
  health: HealthResponse | null;
  studyArea: StudyAreaResponse | null;
  selectedYear: number;
  setSelectedYear: (year: number) => void;
  selectedRegion: string;
  setSelectedRegion: (region: string) => void;
  refreshHealth: () => Promise<void>;
  loadingInit: boolean;
}

const AppContext = createContext<AppContextValue>({
  health: null,
  studyArea: null,
  selectedYear: 2024,
  setSelectedYear: () => {},
  selectedRegion: "full_aoi",
  setSelectedRegion: () => {},
  refreshHealth: async () => {},
  loadingInit: true,
});

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [studyArea, setStudyArea] = useState<StudyAreaResponse | null>(null);
  const [selectedYear, setSelectedYear] = useState<number>(2024);
  const [selectedRegion, setSelectedRegion] = useState<string>("full_aoi");
  const [loadingInit, setLoadingInit] = useState<boolean>(true);

  const refreshHealth = useCallback(async () => {
    try {
      const h = await api.getHealth();
      setHealth(h);
    } catch {
      // Backend might still be starting
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    async function init() {
      setLoadingInit(true);
      try {
        const [h, sa] = await Promise.allSettled([
          api.getHealth(),
          api.getStudyArea(),
        ]);
        if (!mounted) return;
        if (h.status === "fulfilled") setHealth(h.value);
        if (sa.status === "fulfilled") setStudyArea(sa.value);
      } finally {
        if (mounted) setLoadingInit(false);
      }
    }
    init();
    const timer = setInterval(refreshHealth, 15000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [refreshHealth]);

  return (
    <AppContext.Provider
      value={{
        health,
        studyArea,
        selectedYear,
        setSelectedYear,
        selectedRegion,
        setSelectedRegion,
        refreshHealth,
        loadingInit,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => useContext(AppContext);
