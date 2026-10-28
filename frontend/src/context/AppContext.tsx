"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { State, District } from "@/types";
import { api } from "@/lib/api";

interface AppContextType {
  states: State[];
  districts: District[];
  selectedStateId: number | null;
  selectedDistrict: District | null;
  language: "en" | "hi";
  isLocating: boolean;
  locationError: string | null;
  lastUpdated: Date | null;
  setSelectedStateId: (id: number) => void;
  setSelectedDistrict: (district: District | null) => void;
  setLanguage: (lang: "en" | "hi") => void;
  detectLocation: () => Promise<void>;
  refreshTimestamp: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [states, setStates] = useState<State[]>([]);
  const [districts, setDistricts] = useState<District[]>([]);
  const [selectedStateId, setSelectedStateId] = useState<number | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<District | null>(null);
  const [language, setLanguage] = useState<"en" | "hi">("en");
  const [isLocating, setIsLocating] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(new Date());

  // Load States & Districts on initial load
  useEffect(() => {
    async function loadGeography() {
      try {
        const [statesData, districtsData] = await Promise.all([
          api.getStates(),
          api.getDistricts(),
        ]);
        setStates(statesData);
        setDistricts(districtsData);

        // Restore saved district from localStorage or default to Mumbai City
        const savedDistrictId = localStorage.getItem("cap_preferred_district_id");
        if (savedDistrictId) {
          const found = districtsData.find((d) => d.id === parseInt(savedDistrictId));
          if (found) {
            setSelectedDistrict(found);
            setSelectedStateId(found.state_id);
            return;
          }
        }

        // Default to first district if available
        if (districtsData.length > 0) {
          setSelectedDistrict(districtsData[0]);
          setSelectedStateId(districtsData[0].state_id);
        }
      } catch (err) {
        console.error("Failed to load initial geography data", err);
      }
    }
    loadGeography();
  }, []);

  const handleSetSelectedDistrict = (district: District | null) => {
    setSelectedDistrict(district);
    if (district) {
      setSelectedStateId(district.state_id);
      localStorage.setItem("cap_preferred_district_id", district.id.toString());
    } else {
      localStorage.removeItem("cap_preferred_district_id");
    }
  };

  const refreshTimestamp = () => {
    setLastUpdated(new Date());
  };

  // Browser Geolocation Detection
  const detectLocation = async () => {
    if (!navigator.geolocation) {
      setLocationError("Geolocation is not supported by your browser");
      return;
    }

    setIsLocating(true);
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const lat = position.coords.latitude;
          const lon = position.coords.longitude;
          const res = await api.resolveDistrict(lat, lon);
          if (res.found && res.district) {
            handleSetSelectedDistrict(res.district);
          } else {
            setLocationError(res.message || "Your location is outside supported district boundaries.");
          }
        } catch (_err: any) {
          setLocationError("Failed to resolve district from coordinates.");
        } finally {
          setIsLocating(false);
        }
      },
      (error) => {
        setIsLocating(false);
        switch (error.code) {
          case error.PERMISSION_DENIED:
            setLocationError("Location permission denied. Please choose your district manually.");
            break;
          case error.POSITION_UNAVAILABLE:
            setLocationError("Location information is currently unavailable.");
            break;
          case error.TIMEOUT:
            setLocationError("Location request timed out. Please select district manually.");
            break;
          default:
            setLocationError("An error occurred while retrieving location.");
        }
      },
      { timeout: 8000 }
    );
  };

  return (
    <AppContext.Provider
      value={{
        states,
        districts,
        selectedStateId,
        selectedDistrict,
        language,
        isLocating,
        locationError,
        lastUpdated,
        setSelectedStateId,
        setSelectedDistrict: handleSetSelectedDistrict,
        setLanguage,
        detectLocation,
        refreshTimestamp,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
