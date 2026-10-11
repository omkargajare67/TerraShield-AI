import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

interface MapCanvasProps {
  parcelsGeojson?: any;
  boundaryGeojson?: any;
  selectedParcelId?: string | null;
  onSelectParcel?: (parcelId: string | null) => void;
  className?: string;
  height?: string;
}

export const MapCanvas: React.FC<MapCanvasProps> = ({
  parcelsGeojson,
  boundaryGeojson,
  selectedParcelId,
  onSelectParcel,
  className = '',
  height = '500px',
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layersRef = useRef<{
    parcelsLayer?: L.GeoJSON;
    boundaryLayer?: L.GeoJSON;
  }>({});

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Initialize Map if not already created
    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [11.60, 76.05],
        zoom: 12,
        zoomControl: false,
        attributionControl: false,
      });

      L.control.zoom({ position: 'topright' }).addTo(map);

      // Free OpenStreetMap Tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
      }).addTo(map);

      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;

    // 1. Render Boundary Layer if present
    if (layersRef.current.boundaryLayer) {
      map.removeLayer(layersRef.current.boundaryLayer);
      layersRef.current.boundaryLayer = undefined;
    }

    if (boundaryGeojson && boundaryGeojson.features && boundaryGeojson.features.length > 0) {
      const boundaryLayer = L.geoJSON(boundaryGeojson, {
        style: {
          color: '#2563eb',
          weight: 2.5,
          fillColor: '#3b82f6',
          fillOpacity: 0.08,
          dashArray: '4, 4',
        },
      }).addTo(map);
      layersRef.current.boundaryLayer = boundaryLayer;
    }

    // 2. Render Parcels Layer
    if (layersRef.current.parcelsLayer) {
      map.removeLayer(layersRef.current.parcelsLayer);
      layersRef.current.parcelsLayer = undefined;
    }

    if (parcelsGeojson && parcelsGeojson.features && parcelsGeojson.features.length > 0) {
      const parcelsLayer = L.geoJSON(parcelsGeojson, {
        style: (feature) => {
          const props = feature?.properties || {};
          const pid = props.parcel_id || feature?.id;
          const isSelected = selectedParcelId && pid === selectedParcelId;
          const rank = props.rank;
          const isExcluded = props.is_excluded || props.eligibility_status === 'EXCLUDED';
          const isInsufficient = props.eligibility_status === 'INSUFFICIENT_DATA';

          if (isSelected) {
            return {
              fillColor: '#3b82f6',
              color: '#1d4ed8',
              weight: 3.5,
              fillOpacity: 0.85,
            };
          }

          if (isExcluded) {
            return {
              fillColor: '#a0aec0',
              color: '#718096',
              weight: 1.5,
              dashArray: '4, 4',
              fillOpacity: 0.40,
            };
          }

          if (isInsufficient) {
            return {
              fillColor: '#f59e0b',
              color: '#b45309',
              weight: 1.5,
              dashArray: '3, 3',
              fillOpacity: 0.45,
            };
          }

          if (rank === 1) {
            return {
              fillColor: '#2f855a',
              color: '#1c4532',
              weight: 2.5,
              fillOpacity: 0.80,
            };
          } else if (rank && rank <= 5) {
            return {
              fillColor: '#48bb78',
              color: '#276749',
              weight: 2,
              fillOpacity: 0.65,
            };
          } else if (rank) {
            return {
              fillColor: '#68d391',
              color: '#2f855a',
              weight: 1.5,
              fillOpacity: 0.50,
            };
          } else {
            return {
              fillColor: '#a7f3d0',
              color: '#34795c',
              weight: 1.2,
              fillOpacity: 0.40,
            };
          }
        },
        onEachFeature: (feature, layer) => {
          const props = feature.properties || {};
          const pid = props.parcel_id || feature.id || 'N/A';
          const rankText = props.rank ? `Rank #${props.rank}` : 'Unranked';
          const scoreText = props.priority_score_index !== undefined ? `${props.priority_score_index.toFixed(1)}/100` : (props.demo_leverage_score || 'N/A');
          const areaText = props.plantable_area_ha ? `${props.plantable_area_ha.toFixed(2)} ha` : `${props.total_area_ha || props.area_hectares || 'N/A'} ha`;

          // Tooltip
          layer.bindTooltip(
            `<div class="font-sans text-xs font-medium"><strong>${pid}</strong> (${rankText})<br>Score: ${scoreText}</div>`,
            { sticky: true }
          );

          // Click Popup
          layer.bindPopup(
            `
            <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 12px; color: #1e293b; padding: 4px;">
              <div style="font-weight: 700; font-size: 13px; color: #1c4532; margin-bottom: 4px;">${pid} (${rankText})</div>
              <div><b>Priority Score:</b> ${scoreText}</div>
              <div><b>Plantable Area:</b> ${areaText}</div>
              <div><b>Hillslope Mean:</b> ${props.slope_mean_deg ? props.slope_mean_deg.toFixed(1) + '°' : 'N/A'}</div>
              <div><b>Baseline FS:</b> ${props.fs_baseline_mean ? props.fs_baseline_mean.toFixed(2) : 'N/A'}</div>
              <div><b>Modeled ΔFS:</b> +${props.fs_delta_mean ? props.fs_delta_mean.toFixed(2) : 'N/A'}</div>
              <div><b>Primary Driver:</b> ${props.primary_driver || 'Baseline Balance'}</div>
            </div>
            `,
            { maxWidth: 260 }
          );

          layer.on('click', () => {
            if (onSelectParcel) {
              onSelectParcel(pid);
            }
          });
        },
      }).addTo(map);

      layersRef.current.parcelsLayer = parcelsLayer;

      // Automatically fit bounds
      try {
        const bounds = parcelsLayer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [25, 25] });
        }
      } catch (e) {
        console.warn('Could not fit bounds on parcels layer:', e);
      }
    } else if (boundaryGeojson && layersRef.current.boundaryLayer) {
      try {
        const bounds = layersRef.current.boundaryLayer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [30, 30] });
        }
      } catch (e) {
        console.warn('Could not fit bounds on boundary layer:', e);
      }
    }
  }, [parcelsGeojson, boundaryGeojson, selectedParcelId, onSelectParcel]);

  return (
    <div className={`relative w-full rounded-2xl overflow-hidden border border-slate-200 shadow-sm ${className}`} style={{ height }}>
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Floating Legend */}
      <div className="absolute bottom-4 right-4 z-[400] glass-card px-3.5 py-2.5 rounded-xl text-xs text-slate-700 font-sans shadow-lg pointer-events-auto">
        <div className="font-bold text-forest-900 text-xs mb-1.5 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-forest-700 animate-pulse" />
          Parcel Priority Legend
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#2f855a] border border-[#1c4532]" />
            <span className="font-semibold text-slate-900">Rank #1 (Highest)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#48bb78] border border-[#276749]" />
            <span>Top Tier (Ranks 2–5)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#68d391] border border-[#2f855a]" />
            <span>Eligible Candidate</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#a0aec0] border border-[#718096] border-dashed" />
            <span className="text-slate-500">Excluded (Slope/Reserve)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#f59e0b] border border-[#b45309]" />
            <span className="text-amber-700">Insufficient Data</span>
          </div>
        </div>
      </div>
    </div>
  );
};
