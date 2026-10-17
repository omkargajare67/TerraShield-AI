import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import L from 'leaflet';
import {
  Pentagon,
  Square,
  Trash2,
  Crosshair,
  MapPin,
  Check,
  Compass,
  Trees,
  Eye,
  EyeOff,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export interface StudyAreaSelection {
  boundaryGeojson: any;
  bounds: { minx: number; miny: number; maxx: number; maxy: number };
  areaHa: number;
}

interface MapCanvasProps {
  parcelsGeojson?: any;
  boundaryGeojson?: any;
  observedInventoryGeojson?: any;
  bounds?: { minx: number; miny: number; maxx: number; maxy: number };
  selectedParcelId?: string | null;
  onSelectParcel?: (parcelId: string | null) => void;
  className?: string;
  height?: string;
  enableDrawing?: boolean;
  onBoundarySelected?: (selection: StudyAreaSelection | null) => void;
  studyAreaHa?: number;
  onOpenResults?: () => void;
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

import { calculatePolygonAreaHa } from '../../utils/geo';

// Ray-casting point-in-polygon verification
function isPointInPolygon(pt: [number, number], ring: [number, number][]): boolean {
  const [x, y] = pt;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1];
    const xj = ring[j][0], yj = ring[j][1];
    const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

// Compute verified point on surface guaranteed to lie inside the polygon
function getInteriorPoint(ring: [number, number][]): [number, number] {
  if (!ring || ring.length < 3) return [0, 0];

  // 1. Calculate polygon centroid
  let cx = 0, cy = 0;
  for (let i = 0; i < ring.length; i++) {
    cx += ring[i][0];
    cy += ring[i][1];
  }
  const centroid: [number, number] = [cx / ring.length, cy / ring.length];

  // 2. If centroid is inside, use it
  if (isPointInPolygon(centroid, ring)) {
    return centroid;
  }

  // 3. For concave polygons, find midpoint between centroid and vertices inside the polygon
  for (let i = 0; i < ring.length; i++) {
    const mid: [number, number] = [(centroid[0] + ring[i][0]) / 2, (centroid[1] + ring[i][1]) / 2];
    if (isPointInPolygon(mid, ring)) return mid;
  }

  // 4. Fallback to triangle centroid of first 3 vertices
  const triCentroid: [number, number] = [
    (ring[0][0] + ring[1][0] + ring[2][0]) / 3,
    (ring[0][1] + ring[1][1] + ring[2][1]) / 3,
  ];
  if (isPointInPolygon(triCentroid, ring)) return triCentroid;

  return [ring[0][0], ring[0][1]];
}

// Leaflet DivIcon generator for Tree Markers
function createTreeDivIcon(rank?: number, isSelected?: boolean): L.DivIcon {
  const isTop1 = rank === 1;
  const isTopTier = rank !== undefined && rank > 1 && rank <= 5;
  const size = isTop1 ? 34 : isTopTier ? 28 : 22;

  let bgGradient = 'background: radial-gradient(circle, #059669 0%, #064e3b 100%);';
  let borderStyle = 'border: 2px solid #6ee7b7;';
  let badgeHtml = '';
  let shadow = 'box-shadow: 0 4px 10px rgba(0, 0, 0, 0.45);';

  if (isTop1) {
    bgGradient = 'background: radial-gradient(circle, #047857 0%, #022c22 100%);';
    borderStyle = 'border: 2.5px solid #fbbf24; outline: 2px solid rgba(52, 211, 153, 0.8);';
    shadow = 'box-shadow: 0 0 16px rgba(251, 191, 36, 0.6), 0 4px 12px rgba(0,0,0,0.5);';
    badgeHtml = `
      <div style="position: absolute; top: -8px; right: -8px; background: #fbbf24; color: #064e3b; font-size: 9px; font-weight: 800; padding: 1px 4px; border-radius: 9999px; border: 1px solid #78350f; box-shadow: 0 2px 4px rgba(0,0,0,0.3); font-family: monospace;">
        ★ #1
      </div>
    `;
  } else if (isTopTier) {
    bgGradient = 'background: radial-gradient(circle, #059669 0%, #064e3b 100%);';
    borderStyle = 'border: 2px solid #34d399;';
    shadow = 'box-shadow: 0 0 10px rgba(52, 211, 153, 0.4), 0 3px 8px rgba(0,0,0,0.4);';
    badgeHtml = `
      <div style="position: absolute; top: -6px; right: -6px; background: #34d399; color: #022c22; font-size: 8px; font-weight: 800; padding: 1px 3.5px; border-radius: 9999px; border: 1px solid #064e3b; box-shadow: 0 1px 3px rgba(0,0,0,0.3); font-family: monospace;">
        #${rank}
      </div>
    `;
  }

  const selectedRing = isSelected ? 'outline: 3px solid #38bdf8; transform: scale(1.15);' : '';

  const html = `
    <div style="position: relative; width: ${size}px; height: ${size}px; border-radius: 9999px; ${bgGradient} ${borderStyle} ${shadow} ${selectedRing} display: flex; align-items: center; justify-content: center; cursor: pointer; transition: transform 0.15s ease;"
         title="Recommended Planting Parcel${rank ? ` (Rank #${rank})` : ''}">
      <svg style="width: ${size * 0.55}px; height: ${size * 0.55}px; fill: #ffffff;" viewBox="0 0 24 24">
        <path d="M12 2L4 12h5l-3 7h12l-3-7h5L12 2z"/>
        <rect x="11" y="19" width="2" height="3" fill="#ffffff"/>
      </svg>
      ${badgeHtml}
    </div>
  `;

  return L.divIcon({
    className: 'terra-tree-marker',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// Leaflet DivIcon generator for Cluster Badges
function createTreeClusterIcon(count: number, hasTop1: boolean): L.DivIcon {
  const bg = hasTop1
    ? 'background: #ffffff; border: 2px solid #f59e0b; color: #b45309; box-shadow: 0 4px 12px rgba(245,158,11,0.25);'
    : 'background: #ffffff; border: 1.5px solid #059669; color: #047857; box-shadow: 0 4px 12px rgba(5,150,105,0.2);';

  const treeColor = hasTop1 ? '#d97706' : '#059669';

  const html = `
    <div style="display: flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 9999px; ${bg} font-family: monospace; font-size: 11px; font-weight: 700; cursor: pointer; white-space: nowrap;">
      <svg style="width: 14px; height: 14px; fill: ${treeColor};" viewBox="0 0 24 24">
        <path d="M12 2L4 12h5l-3 7h12l-3-7h5L12 2z"/>
        <rect x="11" y="19" width="2" height="3" fill="${treeColor}"/>
      </svg>
      <span>${count} parcels</span>
    </div>
  `;

  return L.divIcon({
    className: 'terra-tree-cluster',
    html,
    iconSize: [85, 26],
    iconAnchor: [42, 13],
  });
}

function createObservedFeatureDivIcon(featureType?: string): L.DivIcon {
  const typeLower = (featureType || '').toLowerCase();
  const isScarp = typeLower.includes('scarp') || typeLower.includes('initiation');
  const isSurge = typeLower.includes('flow') || typeLower.includes('channel') || typeLower.includes('surge');
  const isFan = typeLower.includes('fan') || typeLower.includes('deposition') || typeLower.includes('burial');

  let bg = 'background: radial-gradient(circle, #dc2626 0%, #7f1d1d 100%);';
  let border = 'border: 2px solid #f87171;';
  let symbol = '⚠';

  if (isScarp) {
    bg = 'background: radial-gradient(circle, #ea580c 0%, #9a3412 100%);';
    border = 'border: 2px solid #fb923c; outline: 1.5px solid rgba(251, 146, 60, 0.6);';
    symbol = '▲';
  } else if (isSurge) {
    bg = 'background: radial-gradient(circle, #dc2626 0%, #991b1b 100%);';
    border = 'border: 2px solid #f87171;';
    symbol = '▼';
  } else if (isFan) {
    bg = 'background: radial-gradient(circle, #b91c1c 0%, #450a0a 100%);';
    border = 'border: 2px solid #fca5a5;';
    symbol = '◆';
  }

  const html = `
    <div style="position: relative; width: 26px; height: 26px; border-radius: 9999px; ${bg} ${border} box-shadow: 0 0 12px rgba(220, 38, 38, 0.7), 0 3px 8px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; cursor: pointer; color: #ffffff; font-size: 11px; font-weight: 900; transition: transform 0.15s ease;"
         title="Observed Disaster Feature: ${featureType || 'Observed Landslide'}">
      <span>${symbol}</span>
    </div>
  `;

  return L.divIcon({
    className: 'terra-observed-marker',
    html,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

export const MapCanvas: React.FC<MapCanvasProps> = ({
  parcelsGeojson,
  boundaryGeojson,
  observedInventoryGeojson,
  bounds,
  selectedParcelId,
  onSelectParcel,
  className = '',
  height = '500px',
  enableDrawing = true,
  onBoundarySelected,
  studyAreaHa,
  onOpenResults,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Drawing state
  const [drawMode, setDrawMode] = useState<'none' | 'polygon' | 'rectangle'>('none');
  const [polygonPoints, setPolygonPoints] = useState<[number, number][]>([]); // [lat, lng]
  const [boxStartPoint, setBoxStartPoint] = useState<[number, number] | null>(null);
  const [currentSelection, setCurrentSelection] = useState<StudyAreaSelection | null>(null);

  // Layer Visibility Controls (Independent Frontend Toggles)
  const [showObservedInventory, setShowObservedInventory] = useState<boolean>(true);
  const [showTreeMarkers, setShowTreeMarkers] = useState<boolean>(true);
  const [showTopPriority, setShowTopPriority] = useState<boolean>(true);
  const [showOtherEligible, setShowOtherEligible] = useState<boolean>(true);
  const [showExcluded, setShowExcluded] = useState<boolean>(true);
  const [showInsufficient, setShowInsufficient] = useState<boolean>(true);
  const [showBoundary, setShowBoundary] = useState<boolean>(true);

  // Collapsible Legend State
  const [isLegendExpanded, setIsLegendExpanded] = useState<boolean>(true);
  const [isFilterPanelOpen, setIsFilterPanelOpen] = useState<boolean>(false);

  // References to leaflet layers
  const layersRef = useRef<{
    parcelsLayer?: L.GeoJSON;
    treeMarkersLayer?: L.LayerGroup;
    boundaryLayer?: L.GeoJSON;
    observedInventoryLayer?: L.LayerGroup;
    drawnLayer?: L.LayerGroup;
    drawingMarkersLayer?: L.LayerGroup;
  }>({});

  // Summary Metrics Derived from actual returned features
  const summaryMetrics = useMemo(() => {
    if (!parcelsGeojson?.features) {
      return {
        totalEvaluated: 0,
        eligibleCount: 0,
        topTierCount: 0,
        excludedCount: 0,
        insufficientCount: 0,
        eligibleAreaHa: 0,
      };
    }

    let eligible = 0;
    let topTier = 0;
    let excluded = 0;
    let insufficient = 0;
    let eligibleArea = 0;

    for (const f of parcelsGeojson.features) {
      const p = f.properties || {};
      const status = String(p.eligibility_status || '').toUpperCase();
      const isExc = p.is_excluded || status === 'EXCLUDED';
      const isIns = status === 'INSUFFICIENT_DATA';
      const rank = p.rank;

      if (isExc) {
        excluded++;
      } else if (isIns) {
        insufficient++;
      } else {
        eligible++;
        if (rank && rank <= 5) {
          topTier++;
        }
        eligibleArea += Number(p.plantable_area_ha || p.total_area_ha || 0);
      }
    }

    return {
      totalEvaluated: parcelsGeojson.features.length,
      eligibleCount: eligible,
      topTierCount: topTier,
      excludedCount: excluded,
      insufficientCount: insufficient,
      eligibleAreaHa: Math.round(eligibleArea * 100) / 100,
    };
  }, [parcelsGeojson]);

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

      // OpenStreetMap Base Tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(map);

      // Initialize groups
      layersRef.current.drawnLayer = L.layerGroup().addTo(map);
      layersRef.current.drawingMarkersLayer = L.layerGroup().addTo(map);
      layersRef.current.treeMarkersLayer = L.layerGroup().addTo(map);
      layersRef.current.observedInventoryLayer = L.layerGroup().addTo(map);

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

  // Update Study Boundary Overlay Layer
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (layersRef.current.boundaryLayer) {
      map.removeLayer(layersRef.current.boundaryLayer);
      layersRef.current.boundaryLayer = undefined;
    }

    if (!showBoundary) return;

    if (boundaryGeojson && boundaryGeojson.features && boundaryGeojson.features.length > 0) {
      const boundaryLayer = L.geoJSON(boundaryGeojson, {
        style: {
          color: '#10b981',
          weight: 2.5,
          fillColor: '#10b981',
          fillOpacity: 0.08,
          dashArray: '6, 6',
        },
      }).addTo(map);
      layersRef.current.boundaryLayer = boundaryLayer;

      // Fit bounds if no parcels layer active
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
  }, [boundaryGeojson, parcelsGeojson, showBoundary]);

  // Navigate map to project bounds when no vector layers are loaded
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !bounds) return;

    if (boundaryGeojson?.features?.length || parcelsGeojson?.features?.length) {
      return;
    }

    try {
      const south = Math.min(bounds.miny, bounds.maxy);
      const north = Math.max(bounds.miny, bounds.maxy);
      const west = Math.min(bounds.minx, bounds.maxx);
      const east = Math.max(bounds.minx, bounds.maxx);

      if (
        !isNaN(south) &&
        !isNaN(north) &&
        !isNaN(west) &&
        !isNaN(east) &&
        south >= -90 &&
        north <= 90 &&
        west >= -180 &&
        east <= 180
      ) {
        const b = L.latLngBounds([south, west], [north, east]);
        if (b.isValid()) {
          map.fitBounds(b, { padding: [30, 30] });
        }
      }
    } catch {
      // ignore
    }
  }, [bounds, boundaryGeojson, parcelsGeojson]);

  // Update Observed Landslide Inventory Layer
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (layersRef.current.observedInventoryLayer) {
      layersRef.current.observedInventoryLayer.clearLayers();
    }

    if (!showObservedInventory || !observedInventoryGeojson?.features?.length) {
      return;
    }

    const group = layersRef.current.observedInventoryLayer;
    if (!group) return;

    for (const f of observedInventoryGeojson.features) {
      const geom = f.geometry;
      const props = f.properties || {};
      const fType = props.feature_type || 'Observed Landslide';
      const name = props.name || f.id || 'Documented Event Feature';
      const desc = props.description || '';
      const source = props.source || 'Authoritative Geospatial Inventory';
      const date = props.event_date || '';
      const elev = props.elevation_m;
      const runout = props.runout_length_km;
      const area = props.area_ha;

      const popupContent = `
        <div style="font-family: 'Plus Jakarta Sans', system-ui, sans-serif; font-size: 11.5px; color: #f8fafc; padding: 10px 12px; max-width: 290px; line-height: 1.45;">
          <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(239, 68, 68, 0.4); padding-bottom: 6px; margin-bottom: 7px;">
            <div style="font-weight: 800; font-size: 10.5px; color: #ef4444; font-family: monospace; letter-spacing: 0.05em; text-transform: uppercase;">OBSERVED EVENT FEATURE</div>
            <div style="background: rgba(239, 68, 68, 0.2); color: #fca5a5; font-size: 9.5px; font-weight: 700; padding: 1.5px 6px; border-radius: 4px; border: 1px solid rgba(239, 68, 68, 0.4);">${fType}</div>
          </div>
          <div style="font-weight: 800; font-size: 13px; color: #ffffff; margin-bottom: 5px;">${name}</div>
          ${desc ? `<div style="font-size: 11px; color: #cbd5e1; margin-bottom: 7px; line-height: 1.35;">${desc}</div>` : ''}
          <div style="background: rgba(0,0,0,0.3); border-radius: 7px; padding: 6px 8px; font-size: 10.5px; font-family: monospace; color: #94a3b8; margin-bottom: 7px;">
            ${date ? `<div><span style="color: #64748b;">Event Date:</span> <b style="color: #f1f5f9;">${date}</b></div>` : ''}
            ${elev ? `<div><span style="color: #64748b;">Elevation:</span> <b style="color: #f1f5f9;">${elev}m</b></div>` : ''}
            ${runout ? `<div><span style="color: #64748b;">Runout Length:</span> <b style="color: #fca5a5;">${runout} km</b></div>` : ''}
            ${area ? `<div><span style="color: #64748b;">Mapped Footprint:</span> <b style="color: #fca5a5;">${area} ha</b></div>` : ''}
            ${source ? `<div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 3px; margin-top: 3px;"><span style="color: #64748b;">Source:</span> <span style="color: #cbd5e1;">${source}</span></div>` : ''}
          </div>
          <div style="font-size: 9.5px; color: #fca5a5; border-top: 1px solid rgba(239,68,68,0.25); padding-top: 5px; line-height: 1.35; font-style: italic;">
            ⚠ Documented historical disaster footprint. Model candidate planting parcels are evaluated separately.
          </div>
        </div>
      `;

      if (geom.type === 'Point') {
        const marker = L.marker([geom.coordinates[1], geom.coordinates[0]], {
          icon: createObservedFeatureDivIcon(fType),
          zIndexOffset: 1000,
        }).bindPopup(popupContent, { maxWidth: 300, className: 'terra-popup' });
        group.addLayer(marker);
      } else if (geom.type === 'Polygon' || geom.type === 'MultiPolygon') {
        const polyLayer = L.geoJSON(f, {
          style: {
            color: '#ef4444',
            weight: 2.5,
            dashArray: '6, 6',
            fillColor: '#ef4444',
            fillOpacity: 0.16,
          },
        }).bindPopup(popupContent, { maxWidth: 300, className: 'terra-popup' });
        group.addLayer(polyLayer);
      }
    }

    // Auto-fit bounds to observed inventory if no parcels and no boundary are loaded
    if ((!parcelsGeojson || !parcelsGeojson.features?.length) && (!boundaryGeojson || !boundaryGeojson.features?.length)) {
      try {
        const b = (L as any).featureGroup(group.getLayers()).getBounds();
        if (b.isValid()) {
          map.fitBounds(b, { padding: [50, 50] });
        }
      } catch {
        // ignore
      }
    }
  }, [observedInventoryGeojson, showObservedInventory, parcelsGeojson, boundaryGeojson]);

  // Build Interactive Parcel Popups
  const buildParcelPopupHtml = useCallback((props: any, pid: string) => {
    const rank = props.rank;
    const eligibility = String(props.eligibility_status || '').toUpperCase();
    const isExcluded = props.is_excluded || eligibility === 'EXCLUDED';
    const isInsufficient = eligibility === 'INSUFFICIENT_DATA';

    let classificationTitle = 'ELIGIBLE PLANTING ZONE';
    let classificationColor = '#10b981';
    let classificationBg = 'rgba(16, 185, 129, 0.15)';

    if (rank === 1) {
      classificationTitle = 'TOP-PRIORITY RESTORATION ZONE (RANK #1)';
      classificationColor = '#34d399';
      classificationBg = 'rgba(6, 78, 59, 0.4)';
    } else if (rank && rank <= 5) {
      classificationTitle = `HIGH PRIORITY RESTORATION ZONE (RANK #${rank})`;
      classificationColor = '#34d399';
      classificationBg = 'rgba(5, 150, 105, 0.25)';
    } else if (isExcluded) {
      classificationTitle = 'EXCLUDED PARCEL';
      classificationColor = '#94a3b8';
      classificationBg = 'rgba(100, 116, 139, 0.2)';
    } else if (isInsufficient) {
      classificationTitle = 'INSUFFICIENT DATA COVERAGE';
      classificationColor = '#fbbf24';
      classificationBg = 'rgba(245, 158, 11, 0.2)';
    }

    const plantableArea = props.plantable_area_ha !== undefined && props.plantable_area_ha !== null
      ? `${Number(props.plantable_area_ha).toFixed(2)} ha`
      : 'N/A';
    const totalArea = props.total_area_ha !== undefined && props.total_area_ha !== null
      ? `${Number(props.total_area_ha).toFixed(2)} ha`
      : 'N/A';
    const slope = props.slope_mean_deg !== undefined && props.slope_mean_deg !== null
      ? `${Number(props.slope_mean_deg).toFixed(1)}°`
      : 'N/A';
    const fs0 = props.fs_baseline_mean !== undefined && props.fs_baseline_mean !== null
      ? Number(props.fs_baseline_mean).toFixed(2)
      : 'N/A';
    const fsReinf = props.fs_reinforced_mean !== undefined && props.fs_reinforced_mean !== null
      ? Number(props.fs_reinforced_mean).toFixed(2)
      : 'N/A';
    const deltaFs = props.fs_delta_mean !== undefined && props.fs_delta_mean !== null
      ? `+${Number(props.fs_delta_mean).toFixed(2)} ΔFS`
      : 'N/A';
    const score = props.priority_score_index !== undefined && props.priority_score_index !== null
      ? `${Number(props.priority_score_index).toFixed(1)}%`
      : 'N/A';
    const ndvi = props.ndvi_mean !== undefined && props.ndvi_mean !== null
      ? Number(props.ndvi_mean).toFixed(2)
      : 'N/A';
    const coverage = props.terrain_coverage_pct !== undefined && props.terrain_coverage_pct !== null
      ? `${Number(props.terrain_coverage_pct).toFixed(0)}%`
      : '100%';

    let rationale = '';
    if (rank === 1) {
      rationale = 'Selected as the #1 priority planting parcel: achieves maximum modeled slope stability gain under the selected bio-engineering objective while satisfying terrain and canopy eligibility criteria.';
    } else if (rank && rank <= 5) {
      rationale = 'Top-tier candidate parcel with high composite restoration score and proven soil reinforcement potential.';
    } else if (!isExcluded && !isInsufficient) {
      rationale = 'The parcel meets all active eligibility rules (gradient, canopy openness, terrain coverage) and is verified suitable for restoration.';
    } else if (isExcluded) {
      rationale = `Excluded from planting: ${props.exclusion_reasons || 'Slope limit exceeded (>45°) or dense existing canopy mask.'}`;
    } else {
      rationale = 'Geospatial observations for elevation or multispectral canopy are incomplete (<75% coverage). Ground validation recommended.';
    }

    return `
      <div style="font-family: 'Plus Jakarta Sans', system-ui, sans-serif; font-size: 11.5px; color: #f8fafc; padding: 10px 12px; max-width: 290px; line-height: 1.45;">
        <!-- Header -->
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(52, 211, 153, 0.25); padding-bottom: 7px; margin-bottom: 8px;">
          <div style="font-weight: 800; font-size: 13px; color: #ffffff; font-family: monospace;">${pid}</div>
          <div style="background: ${classificationBg}; color: ${classificationColor}; font-size: 9.5px; font-weight: 700; padding: 2px 6px; border-radius: 9999px; border: 1px solid ${classificationColor}40; text-transform: uppercase;">
            ${rank ? `Rank #${rank}` : eligibility || 'Candidate'}
          </div>
        </div>

        <!-- Classification Banner -->
        <div style="font-size: 10px; font-weight: 700; color: ${classificationColor}; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.03em;">
          ${classificationTitle}
        </div>

        <!-- Metrics Table -->
        <div style="background: rgba(6, 78, 59, 0.3); border: 1px solid rgba(52, 211, 153, 0.2); border-radius: 8px; padding: 6px 8px; margin-bottom: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 10.5px;">
          <div><span style="color: #94a3b8;">Plantable Area:</span> <b style="color: #ffffff;">${plantableArea}</b></div>
          <div><span style="color: #94a3b8;">Total Area:</span> <b style="color: #ffffff;">${totalArea}</b></div>
          <div><span style="color: #94a3b8;">Mean Hillslope:</span> <b style="color: #ffffff;">${slope}</b></div>
          <div><span style="color: #94a3b8;">Baseline FS₀:</span> <b style="color: #ffffff;">${fs0}</b></div>
          <div><span style="color: #94a3b8;">Reinforced FS:</span> <b style="color: #34d399;">${fsReinf}</b></div>
          <div><span style="color: #94a3b8;">Modeled ΔFS:</span> <b style="color: #34d399;">${deltaFs}</b></div>
          <div><span style="color: #94a3b8;">Priority Score:</span> <b style="color: #fbbf24;">${score}</b></div>
          <div><span style="color: #94a3b8;">NDVI Canopy:</span> <b style="color: #ffffff;">${ndvi}</b></div>
          <div><span style="color: #94a3b8;">Completeness:</span> <b style="color: #ffffff;">${coverage}</b></div>
        </div>

        <!-- Plain Language Rationale -->
        <div style="font-size: 10px; color: #cbd5e1; margin-bottom: 8px; line-height: 1.35; background: rgba(0,0,0,0.25); padding: 5px 7px; border-radius: 6px;">
          <b>Selection Analysis:</b> ${rationale}
        </div>

        <!-- Disclaimer Footnote -->
        <div style="font-size: 9px; color: #64748b; font-style: italic; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 5px;">
          🌲 Tree symbols identify recommended planting parcels, not surveyed positions for individual trees.
        </div>
      </div>
    `;
  }, []);

  // Update Parcels and Tree Markers Layers
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Remove existing parcel and tree marker layers
    if (layersRef.current.parcelsLayer) {
      map.removeLayer(layersRef.current.parcelsLayer);
      layersRef.current.parcelsLayer = undefined;
    }
    if (layersRef.current.treeMarkersLayer) {
      layersRef.current.treeMarkersLayer.clearLayers();
    }

    if (!parcelsGeojson || !parcelsGeojson.features || parcelsGeojson.features.length === 0) {
      return;
    }

    // Filter features based on user toggles
    const activeFeatures = parcelsGeojson.features.filter((f: any) => {
      const p = f.properties || {};
      const status = String(p.eligibility_status || '').toUpperCase();
      const isExc = p.is_excluded || status === 'EXCLUDED';
      const isIns = status === 'INSUFFICIENT_DATA';
      const rank = p.rank;

      if (isExc) return showExcluded;
      if (isIns) return showInsufficient;
      if (rank && rank <= 5) return showTopPriority;
      return showOtherEligible;
    });

    const filteredCollection = {
      type: 'FeatureCollection',
      features: activeFeatures,
    };

    // 1. Render Parcel Polygons Layer
    const parcelsLayer = L.geoJSON(filteredCollection as any, {
      style: (feature) => {
        const props = feature?.properties || {};
        const pid = props.parcel_id || feature?.id;
        const isSelected = selectedParcelId && pid === selectedParcelId;
        const rank = props.rank;
        const eligibility = String(props.eligibility_status || '').toUpperCase();
        const isExcluded = props.is_excluded || eligibility === 'EXCLUDED';
        const isInsufficient = eligibility === 'INSUFFICIENT_DATA';

        if (isSelected) {
          return {
            fillColor: '#38bdf8',
            color: '#0284c7',
            weight: 3.5,
            fillOpacity: 0.70,
          };
        }

        if (isExcluded) {
          return {
            fillColor: '#94a3b8',
            color: '#64748b',
            weight: 1.2,
            dashArray: '4, 4',
            fillOpacity: 0.18,
          };
        }

        if (isInsufficient) {
          return {
            fillColor: '#f59e0b',
            color: '#b45309',
            weight: 1.5,
            dashArray: '3, 3',
            fillOpacity: 0.28,
          };
        }

        // Rank #1: Strong green outline and prominent fill
        if (rank === 1) {
          return {
            fillColor: '#10b981',
            color: '#064e3b',
            weight: 3.5,
            fillOpacity: 0.65,
          };
        }

        // Ranks 2–5: Medium green outline
        if (rank && rank <= 5) {
          return {
            fillColor: '#34d399',
            color: '#047857',
            weight: 2.5,
            fillOpacity: 0.50,
          };
        }

        // Other eligible parcels: Light green translucent fill
        return {
          fillColor: '#6ee7b7',
          color: '#059669',
          weight: 1.5,
          fillOpacity: 0.35,
        };
      },
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};
        const pid = props.parcel_id || feature.id || 'N/A';

        layer.bindPopup(buildParcelPopupHtml(props, pid), { maxWidth: 300 });

        layer.on('click', () => {
          if (onSelectParcel) {
            onSelectParcel(pid);
          }
        });
      },
    }).addTo(map);

    layersRef.current.parcelsLayer = parcelsLayer;

    // 2. Render Tree Markers Layer on Eligible Parcels
    const renderMarkers = () => {
      const markersLayer = layersRef.current.treeMarkersLayer;
      if (!markersLayer) return;
      markersLayer.clearLayers();

      if (!showTreeMarkers) return;

      const currentZoom = map.getZoom();
      const eligibleFeatures = activeFeatures.filter((f: any) => {
        const p = f.properties || {};
        const status = String(p.eligibility_status || '').toUpperCase();
        const isExc = p.is_excluded || status === 'EXCLUDED';
        const isIns = status === 'INSUFFICIENT_DATA';
        return !isExc && !isIns;
      });

      // Spatial Clustering when zoomed out and large number of parcels (> 20)
      if (currentZoom < 13 && eligibleFeatures.length > 20) {
        // Spatial hash grid (0.012 deg ~ 1.3 km)
        const grid: Record<string, { latSum: number; lonSum: number; count: number; hasTop1: boolean; parcels: any[] }> = {};

        for (const f of eligibleFeatures) {
          const props = f.properties || {};
          let pt = props.representative_point;
          if (!pt && f.geometry?.coordinates) {
            const ring = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates[0]?.[0];
            if (ring) pt = getInteriorPoint(ring);
          }
          if (!pt || pt.length < 2) continue;

          // Rank #1 is always displayed individually even when zoomed out!
          if (props.rank === 1) {
            const marker = L.marker([pt[1], pt[0]], {
              icon: createTreeDivIcon(1, selectedParcelId === props.parcel_id),
              zIndexOffset: 1000,
            }).addTo(markersLayer);

            marker.bindPopup(buildParcelPopupHtml(props, props.parcel_id || f.id), { maxWidth: 300 });
            marker.on('click', () => onSelectParcel?.(props.parcel_id || f.id));
            continue;
          }

          const cellKey = `${Math.floor(pt[1] / 0.012)}_${Math.floor(pt[0] / 0.012)}`;
          if (!grid[cellKey]) {
            grid[cellKey] = { latSum: 0, lonSum: 0, count: 0, hasTop1: false, parcels: [] };
          }
          grid[cellKey].latSum += pt[1];
          grid[cellKey].lonSum += pt[0];
          grid[cellKey].count += 1;
          grid[cellKey].parcels.push(f);
        }

        // Render aggregated cluster badges or individual markers
        for (const cell of Object.values(grid)) {
          if (cell.count === 1) {
            const f = cell.parcels[0];
            const p = f.properties || {};
            const pt = p.representative_point || getInteriorPoint(f.geometry.coordinates[0]);
            const marker = L.marker([pt[1], pt[0]], {
              icon: createTreeDivIcon(p.rank, selectedParcelId === p.parcel_id),
            }).addTo(markersLayer);

            marker.bindPopup(buildParcelPopupHtml(p, p.parcel_id || f.id), { maxWidth: 300 });
            marker.on('click', () => onSelectParcel?.(p.parcel_id || f.id));
          } else {
            const avgLat = cell.latSum / cell.count;
            const avgLon = cell.lonSum / cell.count;
            const clusterMarker = L.marker([avgLat, avgLon], {
              icon: createTreeClusterIcon(cell.count, cell.hasTop1),
            }).addTo(markersLayer);

            clusterMarker.on('click', () => {
              map.setView([avgLat, avgLon], Math.min(15, currentZoom + 2), { animate: true });
            });
          }
        }
      } else {
        // Individual Tree Markers at closer zoom levels
        for (const f of eligibleFeatures) {
          const props = f.properties || {};
          const pid = props.parcel_id || f.id;
          const isSelected = Boolean(selectedParcelId && pid === selectedParcelId);

          // Obtain verified interior coordinate [lon, lat]
          let pt = props.representative_point;
          if (!pt && f.geometry?.coordinates) {
            const ring = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates[0]?.[0];
            if (ring) {
              pt = getInteriorPoint(ring);
            }
          }

          if (!pt || pt.length < 2) continue;

          // Place tree icon on parcel interior point [lat, lon]
          const marker = L.marker([pt[1], pt[0]], {
            icon: createTreeDivIcon(props.rank, isSelected),
            zIndexOffset: props.rank === 1 ? 999 : props.rank ? 500 - props.rank : 100,
          }).addTo(markersLayer);

          marker.bindPopup(buildParcelPopupHtml(props, pid), { maxWidth: 300 });

          marker.on('click', () => {
            if (onSelectParcel) {
              onSelectParcel(pid);
            }
          });
        }
      }
    };

    renderMarkers();

    // Listen for zoom changes to adaptively switch between clustering and individual parcel markers
    const onZoomEnd = () => {
      renderMarkers();
    };
    map.on('zoomend', onZoomEnd);

    // Fit view bounds to results
    try {
      const bounds = parcelsLayer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [30, 30] });
      }
    } catch {
      // ignore
    }

    return () => {
      map.off('zoomend', onZoomEnd);
    };
  }, [
    parcelsGeojson,
    selectedParcelId,
    onSelectParcel,
    showTreeMarkers,
    showTopPriority,
    showOtherEligible,
    showExcluded,
    showInsufficient,
    buildParcelPopupHtml,
  ]);

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

      // Render drawn boundary on map
      const map = mapInstanceRef.current;
      if (map && layersRef.current.drawnLayer) {
        layersRef.current.drawnLayer.clearLayers();
        layersRef.current.drawingMarkersLayer?.clearLayers();

        const latLngs = closedCoords.map((c) => [c[1], c[0]] as [number, number]);
        const poly = L.polygon(latLngs, {
          color: '#10b981',
          weight: 3,
          fillColor: '#10b981',
          fillOpacity: 0.18,
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
    if (layersRef.current.drawingMarkersLayer) {
      layersRef.current.drawingMarkersLayer.clearLayers();
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
        if (layersRef.current.drawingMarkersLayer) {
          const marker = L.circleMarker([lat, lng], {
            radius: 5,
            fillColor: '#10b981',
            color: '#064e3b',
            weight: 2,
            fillOpacity: 1,
          }).addTo(layersRef.current.drawingMarkersLayer);

          if (nextPoints.length >= 3) {
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
          if (layersRef.current.drawingMarkersLayer) {
            layersRef.current.drawingMarkersLayer.clearLayers();
            L.circleMarker([lat, lng], {
              radius: 6,
              fillColor: '#3b82f6',
              color: '#1d4ed8',
              weight: 2,
              fillOpacity: 1,
            }).addTo(layersRef.current.drawingMarkersLayer);
          }
        } else {
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

  const completeCurrentPolygon = () => {
    if (polygonPoints.length < 3) return;
    const lonLatPoints = polygonPoints.map((p) => [p[1], p[0]] as [number, number]);
    finalizeSelection(lonLatPoints);
  };

  const hasParcels = Boolean(parcelsGeojson?.features?.length);
  const effectiveStudyArea = studyAreaHa || currentSelection?.areaHa || (summaryMetrics.totalEvaluated > 0 ? summaryMetrics.eligibleAreaHa : 0);

  return (
    <div
      className={`relative w-full rounded-2xl overflow-hidden border border-terra-border/50 shadow-md ${className}`}
      style={{ height }}
    >
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Top Left: Interactive Selection Toolbar */}
      {enableDrawing && (
        <div className="absolute top-3 left-3 z-[400] flex flex-wrap items-center gap-1.5 bg-white/95 border border-slate-200 backdrop-blur-md p-1.5 rounded-xl shadow-md text-xs text-slate-800 font-sans">
          <button
            onClick={() => {
              setDrawMode(drawMode === 'polygon' ? 'none' : 'polygon');
              setPolygonPoints([]);
              setBoxStartPoint(null);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              drawMode === 'polygon'
                ? 'bg-emerald-600 text-white font-semibold shadow-xs'
                : 'hover:bg-slate-100 text-slate-700'
            }`}
            title="Click points on map to outline a hillslope or catchment polygon"
          >
            <Pentagon className="w-3.5 h-3.5 text-emerald-600" />
            <span>{drawMode === 'polygon' ? 'Drawing...' : 'Draw Polygon'}</span>
          </button>

          <button
            onClick={() => {
              setDrawMode(drawMode === 'rectangle' ? 'none' : 'rectangle');
              setPolygonPoints([]);
              setBoxStartPoint(null);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              drawMode === 'rectangle'
                ? 'bg-sky-600 text-white font-semibold shadow-xs'
                : 'hover:bg-slate-100 text-slate-700'
            }`}
            title="Click two diagonal corners on the map to select a study area"
          >
            <Square className="w-3.5 h-3.5 text-sky-600" />
            <span>{drawMode === 'rectangle' ? 'Click 2 Corners' : 'Draw Box'}</span>
          </button>

          {drawMode === 'polygon' && polygonPoints.length >= 3 && (
            <button
              onClick={completeCurrentPolygon}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-semibold shadow hover:bg-emerald-700 transition cursor-pointer animate-pulse"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Finish ({polygonPoints.length} pts)</span>
            </button>
          )}

          {currentSelection && (
            <button
              onClick={handleClear}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-rose-600 hover:bg-rose-50 transition cursor-pointer font-medium"
              title="Clear selected boundary"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}

          <div className="relative group">
            <button
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition cursor-pointer"
              title="Jump to critical landslide corridors"
            >
              <Compass className="w-3.5 h-3.5 text-emerald-600" />
              <span className="hidden sm:inline">Presets</span>
            </button>
            <div className="absolute left-0 mt-1 hidden group-hover:block w-52 bg-white border border-slate-200 backdrop-blur-xl rounded-xl shadow-xl py-1 z-50">
              <div className="px-3 py-1 text-[10px] uppercase font-bold tracking-wider text-slate-400">
                Select Corridor
              </div>
              {QUICK_PRESETS.map((p) => (
                <button
                  key={p.name}
                  onClick={() => handleSelectPreset(p)}
                  className="w-full text-left px-3 py-1.5 text-xs text-slate-700 hover:bg-emerald-50 hover:text-emerald-700 transition flex items-center gap-1.5"
                >
                  <MapPin className="w-3 h-3 text-emerald-600 shrink-0" />
                  <span className="truncate">{p.name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Top Center: Drawing Instruction Banner */}
      {drawMode !== 'none' && (
        <div className="absolute top-16 left-3 z-[400] bg-white/95 border border-emerald-300 text-emerald-800 text-xs px-3.5 py-2 rounded-xl shadow-lg flex items-center gap-2 font-mono">
          <Crosshair className="w-4 h-4 animate-spin text-emerald-600" />
          <span>
            {drawMode === 'polygon'
              ? `Click to place polygon vertex (${polygonPoints.length} placed). Click "Finish" or double-click to close.`
              : boxStartPoint
              ? 'Click opposite corner to finish bounding box.'
              : 'Click first corner of study area box.'}
          </span>
        </div>
      )}

      {/* Top Right: Layer Filter Controls */}
      {hasParcels && (
        <div className="absolute top-3 right-12 z-[400]">
          <div className="bg-white/95 border border-slate-200 backdrop-blur-xl p-1.5 rounded-xl shadow-md flex items-center gap-1.5 text-xs text-slate-800 font-sans">
            <button
              onClick={() => setIsFilterPanelOpen(!isFilterPanelOpen)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs transition cursor-pointer border border-slate-200"
              title="Filter map layers"
            >
              <Layers className="w-3.5 h-3.5 text-indigo-600" />
              <span>Layers</span>
              {isFilterPanelOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {/* Quick Tree Marker Toggle Button */}
            <button
              onClick={() => setShowTreeMarkers(!showTreeMarkers)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer border ${
                showTreeMarkers
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-300 shadow-2xs'
                  : 'bg-slate-100 text-slate-400 border-slate-200 line-through'
              }`}
              title="Toggle tree planting icons on recommended parcels"
            >
              <Trees className="w-3.5 h-3.5 text-emerald-600" />
              <span>Tree Icons</span>
              {showTreeMarkers ? <Eye className="w-3 h-3 text-emerald-600" /> : <EyeOff className="w-3 h-3 text-slate-400" />}
            </button>
          </div>

          {/* Expanded Filter Panel */}
          {isFilterPanelOpen && (
            <div className="absolute right-0 mt-2 w-64 p-3 bg-white border border-slate-200 backdrop-blur-2xl rounded-2xl shadow-2xl space-y-2 z-50 text-xs font-sans">
              <div className="font-bold text-slate-900 text-xs flex items-center justify-between pb-1.5 border-b border-slate-100">
                <span>Map Layer Controls</span>
                <span className="text-[10px] text-slate-400 font-mono">Independent</span>
              </div>

              <div className="space-y-1.5 text-[11px]">
                {/* Observed Disaster Inventory Toggle */}
                <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-50 cursor-pointer">
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-red-600 border border-amber-400" />
                    <span className="text-red-700 font-medium">Observed Disaster Inventory</span>
                  </span>
                  <input
                    type="checkbox"
                    checked={showObservedInventory}
                    onChange={(e) => setShowObservedInventory(e.target.checked)}
                    className="accent-red-600 cursor-pointer"
                  />
                </label>

                {/* Tree Markers Toggle */}
                <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-50 cursor-pointer">
                  <span className="flex items-center gap-2">
                    <Trees className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-slate-800 font-medium">Recommended Tree Icons</span>
                  </span>
                  <input
                    type="checkbox"
                    checked={showTreeMarkers}
                    onChange={(e) => setShowTreeMarkers(e.target.checked)}
                    className="accent-emerald-600 cursor-pointer"
                  />
                </label>

                {/* Top Priority Toggle */}
                <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-50 cursor-pointer">
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-sm bg-[#10b981] border border-[#064e3b]" />
                    <span className="text-slate-800 font-medium">Top Priority (Ranks 1–5)</span>
                  </span>
                  <input
                    type="checkbox"
                    checked={showTopPriority}
                    onChange={(e) => setShowTopPriority(e.target.checked)}
                    className="accent-emerald-600 cursor-pointer"
                  />
                </label>

                {/* Other Eligible Toggle */}
                <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-50 cursor-pointer">
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-sm bg-[#6ee7b7] border border-[#059669]" />
                    <span className="text-slate-800 font-medium">Other Eligible Parcels</span>
                  </span>
                  <input
                    type="checkbox"
                    checked={showOtherEligible}
                    onChange={(e) => setShowOtherEligible(e.target.checked)}
                    className="accent-emerald-600 cursor-pointer"
                  />
                </label>

                {/* Excluded Parcels Toggle */}
                <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-50 cursor-pointer">
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-sm bg-[#94a3b8] border border-[#64748b] border-dashed" />
                    <span className="text-slate-500 font-medium">Excluded Parcels</span>
                  </span>
                  <input
                    type="checkbox"
                    checked={showExcluded}
                    onChange={(e) => setShowExcluded(e.target.checked)}
                    className="accent-emerald-600 cursor-pointer"
                  />
                </label>

                {/* Insufficient Data Toggle */}
                <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-50 cursor-pointer">
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-sm bg-[#f59e0b] border border-[#b45309]" />
                    <span className="text-amber-700 font-medium">Insufficient Data</span>
                  </span>
                  <input
                    type="checkbox"
                    checked={showInsufficient}
                    onChange={(e) => setShowInsufficient(e.target.checked)}
                    className="accent-amber-500 cursor-pointer"
                  />
                </label>

                {/* Boundary Toggle */}
                <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-50 cursor-pointer">
                  <span className="flex items-center gap-2">
                    <span className="w-3.5 h-0 border-t-2 border-dashed border-[#10b981]" />
                    <span className="text-slate-800 font-medium">Study Boundary Outline</span>
                  </span>
                  <input
                    type="checkbox"
                    checked={showBoundary}
                    onChange={(e) => setShowBoundary(e.target.checked)}
                    className="accent-emerald-600 cursor-pointer"
                  />
                </label>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Bottom Right: Floating Restoration Map Legend & Results Summary */}
      <div className="absolute bottom-3 right-3 z-[400] bg-white/95 border border-slate-200 backdrop-blur-xl rounded-2xl shadow-xl p-3 text-xs text-slate-800 font-sans pointer-events-auto max-w-[280px]">
        {/* Header with expand/collapse */}
        <div
          className="flex items-center justify-between cursor-pointer pb-1.5 border-b border-slate-100"
          onClick={() => setIsLegendExpanded(!isLegendExpanded)}
        >
          <div className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Restoration Map Legend</span>
          </div>
          <button className="text-slate-400 hover:text-slate-700 transition">
            {isLegendExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
          </button>
        </div>

        {isLegendExpanded && (
          <div className="space-y-2.5 pt-2">
            {/* Live Metrics Counters (if parcels loaded) */}
            {hasParcels && (
              <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 space-y-1 text-[11px] font-mono">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Recommended parcels:</span>
                  <span className="text-emerald-700 font-bold">{summaryMetrics.eligibleCount}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Highest-priority parcels:</span>
                  <span className="text-emerald-600 font-bold">{summaryMetrics.topTierCount}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Eligible area:</span>
                  <span className="text-slate-900 font-bold">{summaryMetrics.eligibleAreaHa.toLocaleString()} ha</span>
                </div>
                {effectiveStudyArea > 0 && (
                  <div className="flex justify-between items-center pt-1 border-t border-slate-200">
                    <span className="text-slate-500">Study area size:</span>
                    <span className="text-slate-900 font-semibold">{effectiveStudyArea.toLocaleString()} ha</span>
                  </div>
                )}
              </div>
            )}

            {/* Legend Symbols */}
            <div className="space-y-1.5 text-[11px]">
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 rounded-full bg-red-600 border border-amber-300 flex items-center justify-center shrink-0">
                  <span className="text-[8px] font-bold text-white leading-none">⚠</span>
                </span>
                <span className="font-semibold text-red-700">Red Marker — Documented landslide initiation</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-0 border-t-2 border-dashed border-[#ef4444] shrink-0" />
                <span className="text-red-600">Crimson Dashed — Runout corridor footprint</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 rounded-full bg-emerald-600 border border-emerald-700 flex items-center justify-center shrink-0">
                  <svg className="w-2.5 h-2.5 fill-white" viewBox="0 0 24 24">
                    <path d="M12 2L4 12h5l-3 7h12l-3-7h5L12 2z"/>
                  </svg>
                </span>
                <span className="font-semibold text-slate-900">Tree Icon — Recommended planting parcel</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 rounded-sm bg-[#10b981] border border-[#064e3b] shrink-0" />
                <span className="font-semibold text-slate-900">Dark Green — Highest-priority restoration zone</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 rounded-sm bg-[#34d399] border border-[#047857] shrink-0" />
                <span className="text-slate-600">Medium Green — High priority (Ranks 2–5)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 rounded-sm bg-[#6ee7b7] border border-[#059669] shrink-0" />
                <span className="text-slate-600">Green — Other eligible planting zones</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 rounded-sm bg-[#94a3b8] border border-[#64748b] border-dashed shrink-0" />
                <span className="text-slate-400">Grey — Excluded parcel (Slope &gt; 45° / Canopy)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 rounded-sm bg-[#f59e0b] border border-[#b45309] shrink-0" />
                <span className="text-amber-700">Amber — Insufficient data</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-0 border-t-2 border-dashed border-[#10b981] shrink-0" />
                <span className="text-emerald-700">Dashed Outline — Selected study boundary</span>
              </div>
            </div>

            {/* Scientific Explanation Note */}
            <div className="text-[9.5px] text-slate-500 pt-1.5 border-t border-slate-100 leading-snug">
              Tree symbols identify recommended planting parcels. They do not represent surveyed positions for individual trees.
            </div>

            {/* Button to Open Results Dashboard if available */}
            {hasParcels && onOpenResults && (
              <button
                onClick={onOpenResults}
                className="w-full py-1.5 px-2.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-semibold text-[11px] border border-emerald-200 transition text-center cursor-pointer shadow-2xs"
              >
                Inspect Results Table &amp; Audit &rarr;
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MapCanvas;
