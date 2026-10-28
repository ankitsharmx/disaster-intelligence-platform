"use client";

import React, { useEffect, useRef } from "react";
import L from "leaflet";

interface LeafletMapProps {
  center: [number, number];
  zoom?: number;
  layersData: {
    boundaries?: any;
    facilities?: any;
    incidents?: any;
    alerts?: any[];
  };
  visibleLayers: {
    boundaries: boolean;
    facilities: boolean;
    incidents: boolean;
    alerts: boolean;
    riskZones: boolean;
  };
  onSelectFeature?: (feature: any) => void;
}

export default function LeafletMap({
  center,
  zoom = 11,
  layersData,
  visibleLayers,
  onSelectFeature,
}: LeafletMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Layer groups for toggleable layers
  const boundaryLayerGroup = useRef<L.GeoJSON | null>(null);
  const facilityLayerGroup = useRef<L.LayerGroup | null>(null);
  const incidentLayerGroup = useRef<L.LayerGroup | null>(null);
  const alertLayerGroup = useRef<L.LayerGroup | null>(null);
  const riskLayerGroup = useRef<L.LayerGroup | null>(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center,
      zoom,
      zoomControl: true,
    });

    // OpenStreetMap base tile layer with mandatory attribution
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
    }).addTo(map);

    // Initialize layer groups
    facilityLayerGroup.current = L.layerGroup().addTo(map);
    incidentLayerGroup.current = L.layerGroup().addTo(map);
    alertLayerGroup.current = L.layerGroup().addTo(map);
    riskLayerGroup.current = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Pan to center when changed
  useEffect(() => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView(center, zoom);
    }
  }, [center, zoom]);

  // Update Boundaries Layer
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    if (boundaryLayerGroup.current) {
      boundaryLayerGroup.current.remove();
      boundaryLayerGroup.current = null;
    }

    if (visibleLayers.boundaries && layersData.boundaries) {
      boundaryLayerGroup.current = L.geoJSON(layersData.boundaries, {
        style: {
          color: "#ea580c",
          weight: 2.5,
          fillColor: "#ea580c",
          fillOpacity: 0.08,
          dashArray: "4, 4",
        },
        onEachFeature: (feature, layer) => {
          layer.on("click", () => {
            onSelectFeature?.({
              type: "boundary",
              properties: feature.properties,
            });
          });
        },
      }).addTo(map);
    }
  }, [layersData.boundaries, visibleLayers.boundaries]);

  // Update Facilities Layer
  useEffect(() => {
    if (!facilityLayerGroup.current) return;
    facilityLayerGroup.current.clearLayers();

    if (!visibleLayers.facilities || !layersData.facilities?.features) return;

    layersData.facilities.features.forEach((feature: any) => {
      const [lon, lat] = feature.geometry.coordinates;
      const props = feature.properties;
      const isHospital = props.category === "hospital";
      const isShelter = props.category === "shelter";

      const iconHtml = `
        <div style="
          background-color: ${isHospital ? "#e11d48" : isShelter ? "#2563eb" : "#475569"};
          color: white;
          width: 28px;
          height: 28px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 2px solid white;
          box-shadow: 0 2px 5px rgba(0,0,0,0.4);
          font-size: 13px;
          font-weight: bold;
        ">
          ${isHospital ? "H" : isShelter ? "S" : "P"}
        </div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: "custom-facility-marker",
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([lat, lon], { icon: customIcon });
      marker.on("click", () => {
        onSelectFeature?.({
          type: "facility",
          properties: props,
          coordinates: [lat, lon],
        });
      });

      marker.bindTooltip(`<b>${props.name}</b><br/>${props.category.toUpperCase()}`, {
        direction: "top",
        offset: [0, -12],
      });

      facilityLayerGroup.current?.addLayer(marker);
    });
  }, [layersData.facilities, visibleLayers.facilities]);

  // Update Verified Incidents Layer (STRICTLY VERIFIED ONLY)
  useEffect(() => {
    if (!incidentLayerGroup.current) return;
    incidentLayerGroup.current.clearLayers();

    if (!visibleLayers.incidents || !layersData.incidents?.features) return;

    layersData.incidents.features.forEach((feature: any) => {
      const [lon, lat] = feature.geometry.coordinates;
      const props = feature.properties;

      // Unverified reports are NEVER rendered
      if (props.status !== "verified") return;

      const iconHtml = `
        <div style="
          background-color: #d97706;
          color: white;
          width: 26px;
          height: 26px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 2px solid #fff;
          box-shadow: 0 2px 5px rgba(0,0,0,0.5);
          font-size: 14px;
        ">
          ⚠️
        </div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: "custom-incident-marker",
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });

      const marker = L.marker([lat, lon], { icon: customIcon });
      marker.on("click", () => {
        onSelectFeature?.({
          type: "incident",
          properties: props,
          coordinates: [lat, lon],
        });
      });

      marker.bindTooltip(
        `<b>VERIFIED INCIDENT</b><br/>${props.type.toUpperCase()}<br/>Score: ${props.confidence_score ? (props.confidence_score * 100).toFixed(0) + "%" : "Verified"}`,
        { direction: "top", offset: [0, -12] }
      );

      incidentLayerGroup.current?.addLayer(marker);
    });
  }, [layersData.incidents, visibleLayers.incidents]);

  // Update Alert Affected Areas Layer
  useEffect(() => {
    if (!alertLayerGroup.current) return;
    alertLayerGroup.current.clearLayers();

    if (!visibleLayers.alerts || !layersData.alerts) return;

    layersData.alerts.forEach((alert: any) => {
      // Draw indicative circle around district center or boundary
      const circle = L.circle(center, {
        color: alert.severity === "critical" ? "#dc2626" : "#f97316",
        fillColor: alert.severity === "critical" ? "#dc2626" : "#f97316",
        fillOpacity: 0.18,
        radius: 6000,
        weight: 2,
      });

      circle.on("click", () => {
        onSelectFeature?.({
          type: "alert",
          properties: alert,
          coordinates: center,
        });
      });

      circle.bindTooltip(`<b>ALERT: ${alert.title}</b><br/>${alert.severity.toUpperCase()}`, {
        direction: "center",
      });

      alertLayerGroup.current?.addLayer(circle);
    });
  }, [layersData.alerts, visibleLayers.alerts, center]);

  // Update Indicative Risk Zones
  useEffect(() => {
    if (!riskLayerGroup.current) return;
    riskLayerGroup.current.clearLayers();

    if (!visibleLayers.riskZones) return;

    // Indicative simulated flood buffer
    const floodBuffer = L.circle([center[0] + 0.015, center[1] - 0.02], {
      color: "#0284c7",
      fillColor: "#0284c7",
      fillOpacity: 0.12,
      radius: 4000,
      dashArray: "6, 6",
      weight: 1.5,
    });

    floodBuffer.bindTooltip("<b>Indicative Inundation Risk Zone</b><br/>Calculated from river stage model", {
      direction: "center",
    });

    riskLayerGroup.current.addLayer(floodBuffer);
  }, [visibleLayers.riskZones, center]);

  return <div ref={mapContainerRef} className="w-full h-full min-h-[550px] rounded-xl z-0" />;
}
