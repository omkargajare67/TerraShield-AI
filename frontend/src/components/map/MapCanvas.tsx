import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import {
  Pentagon,
  Square,
  Trash2,
  Crosshair,
  MapPin,
  Check,
  Compass,
} from 'lucide-react';

export interface StudyAreaSelection {
  boundaryGeojson: any;
  bounds: { minx: number; miny: number; maxx: number; maxy: number };
  areaHa: number;
}

interface MapCanvasProps {
  parcelsGeojson?: any;
  boundaryGeojson?: any;
  selectedParcelId?: string | null;
  onSelectParcel?: (parcelId: string | null) => void;
  className?: string;
  height?: string;
  enableDrawing?: boolean;
  onBoundarySelected?: (selection: StudyAreaSelection | null) => void;
}

// Preset disaster-prone & watershed focus areas
const QUICK_PRESETS = [
  {
    name: 'Wayanad Meppadi (Kerala)',
    center: [11.55, 76.12] as [number, number],
    zoom: 13,
    bounds: { minx: 76.08, miny: 11.51, maxx: 76.15, maxy: 11.59 },
  },
  {
    name: 'Idukki Catchment (Kerala)',
    center: [9.85, 76.98] as [number, number],
    zoom: 12,
    bounds: { minx: 76.92, miny: 9.80, maxx: 77.05, maxy: 9.90 },
  },
  {
    name: 'Munnar Gap (Western Ghats)',
    center: [10.08, 77.06] as [number, number],
    zoom: 13,
    bounds: { minx: 77.02, miny: 10.04, maxx: 77.10, maxy: 10.12 },
  },
  {
    name: 'Shimla Ridge (Himachal)',
    center: [31.10, 77.17] as [number, number],
    zoom: 13,
    bounds: { minx: 77.12, miny: 31.06, maxx: 77.22, maxy: 31.14 },
  },
  {
    name: 'Joshimath Slopes (Uttarakhand)',
    center: [30.55, 79.56] as [number, number],
    zoom: 13,
    bounds: { minx: 79.52, miny: 30.52, maxx: 79.60, maxy: 30.58 },
  },
];

function calculatePolygonAreaHa(coords: [number, number][]): number {
  if (coords.length < 3) return 0;
  const lons = coords.map((c) => c[0]);
  const lats = coords.map((c) => c[1]);
  const meanLat = lats.reduce((a, b) => a + b, 0) / lats.length;
  const meanLon = lons.reduce((a, b) => a + b, 0) / lons.length;
  const latRad = (meanLat * Math.PI) / 180;
  const cosLat = Math.cos(latRad);
  const mPerDegLat = 111132.954 - 559.822 * Math.cos(2 * latRad) + 1.175 * Math.cos(4 * latRad);
  const mPerDegLon = 111412.84 * cosLat - 93.5 * Math.cos(3 * latRad);

  let area = 0;
  for (let i = 0; i < coords.length; i++) {
    const j = (i + 1) % coords.length;
    const xi = (coords[i][0] - meanLon) * mPerDegLon;
    const yi = (coords[i][1] - meanLat) * mPerDegLat;
    const xj = (coords[j][0] - meanLon) * mPerDegLon;
    const yj = (coords[j][1] - meanLat) * mPerDegLat;
    area += xi * yj - xj * yi;
  }
  return (Math.abs(area) * 0.5) / 10000;
}

export const MapCanvas: React.FC<MapCanvasProps> = ({
  parcelsGeojson,
  boundaryGeojson,
  selectedParcelId,
  onSelectParcel,
  className = '',
  height = '500px',
  enableDrawing = true,
  onBoundarySelected,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Drawing state
  const [drawMode, setDrawMode] = useState<'none' | 'polygon' | 'rectangle'>('none');
  const [polygonPoints, setPolygonPoints] = useState<[number, number][]>([]); // [lat, lng]
  const [boxStartPoint, setBoxStartPoint] = useState<[number, number] | null>(null);
  const [currentSelection, setCurrentSelection] = useState<StudyAreaSelection | null>(null);

  const layersRef = useRef<{
    parcelsLayer?: L.GeoJSON;
    boundaryLayer?: L.GeoJSON;
    drawnLayer?: L.LayerGroup;
    previewLayer?: L.Polygon | L.Rectangle;
    markersLayer?: L.LayerGroup;
  }>({});

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [11.60, 76.05],
        zoom: 12,
        zoomControl: false,
        attributionControl: false,
      });

      L.control.zoom({ position: 'topright' }).addTo(map);

      // OpenStreetMap Tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
      }).addTo(map);

      // Initialize drawing layers
      layersRef.current.drawnLayer = L.layerGroup().addTo(map);
      layersRef.current.markersLayer = L.layerGroup().addTo(map);

      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 150);

    return () => {
      clearTimeout(timer);
    };
  }, []);

  // Update Boundary Layer
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (layersRef.current.boundaryLayer) {
      map.removeLayer(layersRef.current.boundaryLayer);
      layersRef.current.boundaryLayer = undefined;
    }

    if (boundaryGeojson && boundaryGeojson.features && boundaryGeojson.features.length > 0) {
      const boundaryLayer = L.geoJSON(boundaryGeojson, {
        style: {
          color: '#10b981',
          weight: 2.5,
          fillColor: '#10b981',
          fillOpacity: 0.12,
          dashArray: '5, 5',
        },
      }).addTo(map);
      layersRef.current.boundaryLayer = boundaryLayer;

      // Fit bounds if no parcels
      if (!parcelsGeojson || !parcelsGeojson.features || parcelsGeojson.features.length === 0) {
        try {
          const b = boundaryLayer.getBounds();
          if (b.isValid()) {
            map.fitBounds(b, { padding: [30, 30] });
          }
        } catch {
          // ignore
        }
      }
    }
  }, [boundaryGeojson, parcelsGeojson]);

  // Update Parcels Layer
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

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
              fillOpacity: 0.35,
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
              fillColor: '#10b981',
              color: '#064e3b',
              weight: 2.5,
              fillOpacity: 0.85,
            };
          } else if (rank && rank <= 5) {
            return {
              fillColor: '#34d399',
              color: '#047857',
              weight: 2,
              fillOpacity: 0.70,
            };
          } else if (rank) {
            return {
              fillColor: '#6ee7b7',
              color: '#059669',
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
          const scoreText =
            props.priority_score_index !== undefined
              ? `${props.priority_score_index.toFixed(1)}%`
              : (props.demo_leverage_score || 'N/A');
          const areaText = props.plantable_area_ha
            ? `${props.plantable_area_ha.toFixed(2)} ha`
            : `${props.total_area_ha || props.area_hectares || 'N/A'} ha`;

          layer.bindTooltip(
            `<div class="font-sans text-xs font-medium"><strong>${pid}</strong> (${rankText})<br>Score: ${scoreText}</div>`,
            { sticky: true }
          );

          layer.bindPopup(
            `
            <div style="font-family: sans-serif; font-size: 12px; color: #1e293b; padding: 4px;">
              <div style="font-weight: 700; font-size: 13px; color: #047857; margin-bottom: 4px;">${pid} (${rankText})</div>
              <div><b>Priority Score:</b> ${scoreText}</div>
              <div><b>Plantable Area:</b> ${areaText}</div>
              <div><b>Hillslope Mean:</b> ${props.slope_mean_deg ? props.slope_mean_deg.toFixed(1) + '°' : 'N/A'}</div>
              <div><b>Baseline Stability (FS₀):</b> ${props.fs_baseline_mean ? props.fs_baseline_mean.toFixed(2) : 'N/A'}</div>
              <div><b>Modeled ΔFS Gain:</b> +${props.fs_delta_mean ? props.fs_delta_mean.toFixed(2) : 'N/A'}</div>
              <div><b>Primary Driver:</b> ${props.primary_driver || 'Stability Gain'}</div>
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

      try {
        const bounds = parcelsLayer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [25, 25] });
        }
      } catch {
        // ignore
      }
    }
  }, [parcelsGeojson, selectedParcelId, onSelectParcel]);

  // Complete and emit drawn boundary
  const finalizeSelection = useCallback(
    (lonLatPoints: [number, number][]) => {
      if (lonLatPoints.length < 3) return;

      const lons = lonLatPoints.map((p) => p[0]);
      const lats = lonLatPoints.map((p) => p[1]);
      const minx = Math.min(...lons);
      const maxx = Math.max(...lons);
      const miny = Math.min(...lats);
      const maxy = Math.max(...lats);

      const closedCoords = [...lonLatPoints];
      if (
        closedCoords[0][0] !== closedCoords[closedCoords.length - 1][0] ||
        closedCoords[0][1] !== closedCoords[closedCoords.length - 1][1]
      ) {
        closedCoords.push(closedCoords[0]);
      }

      const areaHa = calculatePolygonAreaHa(closedCoords);

      const featureCollection = {
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            geometry: {
              type: 'Polygon',
              coordinates: [closedCoords],
            },
            properties: {
              area_ha: Math.round(areaHa * 100) / 100,
              minx,
              miny,
              maxx,
              maxy,
            },
          },
        ],
      };

      const sel: StudyAreaSelection = {
        boundaryGeojson: featureCollection,
        bounds: { minx, miny, maxx, maxy },
        areaHa: Math.round(areaHa * 100) / 100,
      };

      setCurrentSelection(sel);
      if (onBoundarySelected) {
        onBoundarySelected(sel);
      }

      // Render on map
      const map = mapInstanceRef.current;
      if (map && layersRef.current.drawnLayer) {
        layersRef.current.drawnLayer.clearLayers();
        layersRef.current.markersLayer?.clearLayers();

        const latLngs = closedCoords.map((c) => [c[1], c[0]] as [number, number]);
        const poly = L.polygon(latLngs, {
          color: '#10b981',
          weight: 3,
          fillColor: '#10b981',
          fillOpacity: 0.22,
          dashArray: '6, 6',
        }).addTo(layersRef.current.drawnLayer);

        poly.bindTooltip(
          `<strong>Selected Area: ${sel.areaHa.toLocaleString()} ha</strong><br/>Click "Analyze This Area" to run.`,
          { sticky: true }
        );
      }

      // Exit draw mode
      setDrawMode('none');
      setPolygonPoints([]);
      setBoxStartPoint(null);
    },
    [onBoundarySelected]
  );

  // Clear Boundary
  const handleClear = useCallback(() => {
    setDrawMode('none');
    setPolygonPoints([]);
    setBoxStartPoint(null);
    setCurrentSelection(null);
    if (layersRef.current.drawnLayer) {
      layersRef.current.drawnLayer.clearLayers();
    }
    if (layersRef.current.markersLayer) {
      layersRef.current.markersLayer.clearLayers();
    }
    if (onBoundarySelected) {
      onBoundarySelected(null);
    }
  }, [onBoundarySelected]);

  // Quick Preset Selection
  const handleSelectPreset = (preset: (typeof QUICK_PRESETS)[0]) => {
    const map = mapInstanceRef.current;
    if (!map) return;

    map.flyTo(preset.center, preset.zoom, { duration: 1.2 });

    const { minx, miny, maxx, maxy } = preset.bounds;
    const boxCoords: [number, number][] = [
      [minx, miny],
      [maxx, miny],
      [maxx, maxy],
      [minx, maxy],
      [minx, miny],
    ];

    finalizeSelection(boxCoords);
  };

  // Map Click Handling for Drawing
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !enableDrawing) return;

    const handleMapClick = (e: L.LeafletMouseEvent) => {
      const lat = e.latlng.lat;
      const lng = e.latlng.lng;

      if (drawMode === 'polygon') {
        const nextPoints: [number, number][] = [...polygonPoints, [lat, lng]];
        setPolygonPoints(nextPoints);

        // Render point marker
        if (layersRef.current.markersLayer) {
          const marker = L.circleMarker([lat, lng], {
            radius: 5,
            fillColor: '#10b981',
            color: '#064e3b',
            weight: 2,
            fillOpacity: 1,
          }).addTo(layersRef.current.markersLayer);

          // Clicking on the first point finishes polygon
          if (nextPoints.length >= 3 && nextPoints.length > 1) {
            marker.on('click', () => {
              const lonLatPoints = nextPoints.map((p) => [p[1], p[0]] as [number, number]);
              finalizeSelection(lonLatPoints);
            });
          }
        }

        // Update preview polyline
        if (layersRef.current.drawnLayer) {
          layersRef.current.drawnLayer.clearLayers();
          if (nextPoints.length >= 2) {
            L.polyline(nextPoints, {
              color: '#34d399',
              weight: 2.5,
              dashArray: '4, 4',
            }).addTo(layersRef.current.drawnLayer);
          }
        }
      } else if (drawMode === 'rectangle') {
        if (!boxStartPoint) {
          setBoxStartPoint([lat, lng]);
          if (layersRef.current.markersLayer) {
            layersRef.current.markersLayer.clearLayers();
            L.circleMarker([lat, lng], {
              radius: 6,
              fillColor: '#3b82f6',
              color: '#1d4ed8',
              weight: 2,
              fillOpacity: 1,
            }).addTo(layersRef.current.markersLayer);
          }
        } else {
          // Second click completes rectangle
          const [startLat, startLng] = boxStartPoint;
          const minx = Math.min(startLng, lng);
          const maxx = Math.max(startLng, lng);
          const miny = Math.min(startLat, lat);
          const maxy = Math.max(startLat, lat);

          const boxCoords: [number, number][] = [
            [minx, miny],
            [maxx, miny],
            [maxx, maxy],
            [minx, maxy],
            [minx, miny],
          ];
          finalizeSelection(boxCoords);
        }
      }
    };

    const handleMouseMove = (e: L.LeafletMouseEvent) => {
      if (drawMode === 'rectangle' && boxStartPoint && layersRef.current.drawnLayer) {
        const [startLat, startLng] = boxStartPoint;
        const bounds = L.latLngBounds([startLat, startLng], [e.latlng.lat, e.latlng.lng]);
        layersRef.current.drawnLayer.clearLayers();
        L.rectangle(bounds, {
          color: '#3b82f6',
          weight: 2,
          dashArray: '4, 4',
          fillColor: '#60a5fa',
          fillOpacity: 0.15,
        }).addTo(layersRef.current.drawnLayer);
      }
    };

    map.on('click', handleMapClick);
    map.on('mousemove', handleMouseMove);

    return () => {
      map.off('click', handleMapClick);
      map.off('mousemove', handleMouseMove);
    };
  }, [drawMode, polygonPoints, boxStartPoint, enableDrawing, finalizeSelection]);

  // Complete current polygon manually
  const completeCurrentPolygon = () => {
    if (polygonPoints.length < 3) return;
    const lonLatPoints = polygonPoints.map((p) => [p[1], p[0]] as [number, number]);
    finalizeSelection(lonLatPoints);
  };

  return (
    <div
      className={`relative w-full rounded-2xl overflow-hidden border border-terra-border/50 shadow-md ${className}`}
      style={{ height }}
    >
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Interactive Selection Toolbar */}
      {enableDrawing && (
        <div className="absolute top-4 left-4 z-[400] flex flex-wrap items-center gap-2 bg-terra-deep/90 border border-terra-border/70 backdrop-blur-md p-1.5 rounded-xl shadow-xl text-xs text-terra-ivory font-sans">
          {/* Draw Polygon Button */}
          <button
            onClick={() => {
              setDrawMode(drawMode === 'polygon' ? 'none' : 'polygon');
              setPolygonPoints([]);
              setBoxStartPoint(null);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              drawMode === 'polygon'
                ? 'bg-terra-mint text-terra-deep font-semibold shadow'
                : 'hover:bg-terra-forest/60 text-terra-ivory'
            }`}
            title="Click points on map to outline a hillslope or catchment polygon"
          >
            <Pentagon className="w-3.5 h-3.5" />
            <span>{drawMode === 'polygon' ? 'Drawing...' : 'Draw Polygon'}</span>
          </button>

          {/* Draw Box Button */}
          <button
            onClick={() => {
              setDrawMode(drawMode === 'rectangle' ? 'none' : 'rectangle');
              setPolygonPoints([]);
              setBoxStartPoint(null);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              drawMode === 'rectangle'
                ? 'bg-blue-500 text-white font-semibold shadow'
                : 'hover:bg-terra-forest/60 text-terra-ivory'
            }`}
            title="Click two diagonal corners on the map to select a study area"
          >
            <Square className="w-3.5 h-3.5" />
            <span>{drawMode === 'rectangle' ? 'Click 2 Corners' : 'Draw Box'}</span>
          </button>

          {/* Complete Polygon Button (visible when >=3 points placed) */}
          {drawMode === 'polygon' && polygonPoints.length >= 3 && (
            <button
              onClick={completeCurrentPolygon}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 text-white font-semibold shadow hover:bg-emerald-600 transition cursor-pointer animate-pulse"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Finish ({polygonPoints.length} pts)</span>
            </button>
          )}

          {/* Clear Button */}
          {currentSelection && (
            <button
              onClick={handleClear}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-rose-300 hover:bg-rose-500/20 transition cursor-pointer font-medium"
              title="Clear selected boundary"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}

          {/* Quick Presets Dropdown */}
          <div className="relative group">
            <button
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-terra-forest/60 text-terra-muted hover:text-terra-ivory transition cursor-pointer"
              title="Jump to critical landslide corridors"
            >
              <Compass className="w-3.5 h-3.5 text-terra-mint" />
              <span className="hidden sm:inline">Presets</span>
            </button>
            <div className="absolute left-0 mt-1 hidden group-hover:block w-52 bg-terra-deep/95 border border-terra-border/80 backdrop-blur-xl rounded-xl shadow-2xl py-1 z-50">
              <div className="px-3 py-1 text-[10px] uppercase font-bold tracking-wider text-terra-slate">
                Select Corridor
              </div>
              {QUICK_PRESETS.map((p) => (
                <button
                  key={p.name}
                  onClick={() => handleSelectPreset(p)}
                  className="w-full text-left px-3 py-1.5 text-xs text-terra-ivory hover:bg-terra-forest/70 hover:text-terra-mint transition flex items-center gap-1.5"
                >
                  <MapPin className="w-3 h-3 text-terra-mint shrink-0" />
                  <span className="truncate">{p.name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Active Draw Instruction Banner */}
      {drawMode !== 'none' && (
        <div className="absolute top-16 left-4 z-[400] bg-terra-deep/95 border border-terra-mint/40 text-terra-mint text-xs px-3.5 py-2 rounded-xl shadow-lg flex items-center gap-2 font-mono">
          <Crosshair className="w-4 h-4 animate-spin text-terra-mint" />
          <span>
            {drawMode === 'polygon'
              ? `Click to place polygon vertex (${polygonPoints.length} placed). Click "Finish" or double-click to close.`
              : boxStartPoint
              ? 'Click opposite corner to finish bounding box.'
              : 'Click first corner of study area box.'}
          </span>
        </div>
      )}

      {/* Selected Boundary Acreage Badge */}
      {currentSelection && (
        <div className="absolute top-4 right-4 z-[400] bg-terra-deep/90 border border-terra-mint/40 backdrop-blur-md px-3.5 py-2 rounded-xl text-xs text-terra-ivory font-sans shadow-xl flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-terra-mint animate-pulse" />
          <div>
            <span className="font-semibold text-terra-mint">
              {currentSelection.areaHa.toLocaleString()} ha
            </span>{' '}
            <span className="text-terra-slate text-[11px]">
              (~{(currentSelection.areaHa / 100).toFixed(2)} km²)
            </span>
          </div>
        </div>
      )}

      {/* Floating Priority Legend */}
      <div className="absolute bottom-4 right-4 z-[400] bg-terra-deep/90 border border-terra-border/80 backdrop-blur-md px-3.5 py-2.5 rounded-xl text-xs text-terra-ivory font-sans shadow-xl pointer-events-auto max-w-[220px]">
        <div className="font-bold text-terra-mint text-xs mb-1.5 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-terra-mint animate-pulse" />
          Restoration Priority Legend
        </div>
        <div className="space-y-1.5 text-[11px]">
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#10b981] border border-[#064e3b] shrink-0" />
            <span className="font-semibold text-terra-ivory">Rank #1 (Top Priority)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#34d399] border border-[#047857] shrink-0" />
            <span className="text-terra-muted">Top Tier (Ranks 2–5)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#6ee7b7] border border-[#059669] shrink-0" />
            <span className="text-terra-muted">Eligible Candidate</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#a0aec0] border border-[#718096] border-dashed shrink-0" />
            <span className="text-terra-slate">Excluded (Slope/Mask)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[#f59e0b] border border-[#b45309] shrink-0" />
            <span className="text-amber-300">Insufficient Data</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MapCanvas;
