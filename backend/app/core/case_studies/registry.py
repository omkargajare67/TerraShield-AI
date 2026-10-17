"""Configuration-driven registry of real-world landslide case studies.

Maintains curated, factual disaster scenarios, source citations, observed spatial
event footprints, dataset provenance, and execution parameters.
"""

from typing import Dict, List, Optional
from backend.app.core.case_studies.models import (
    CaseStudy,
    CaseStudyDataset,
    CaseStudySourceReference,
)

# -----------------------------------------------------------------------------
# Case A: Wayanad, Kerala, India (30 July 2024)
# -----------------------------------------------------------------------------
WAYANAD_OBSERVED_INVENTORY = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "OBS-WY-01",
            "geometry": {"type": "Point", "coordinates": [76.155, 11.542]},
            "properties": {
                "name": "Punchirimattom Crown Initiation Scarp",
                "feature_type": "Initiation Scarp",
                "elevation_m": 1540,
                "event_date": "2024-07-30",
                "description": "Primary slope collapse originating in tea plantation escarpment following >350mm torrential monsoon cloudburst.",
                "source": "ISRO / NRSC Rapid Disaster Mapping (August 2024)",
            },
        },
        {
            "type": "Feature",
            "id": "OBS-WY-02",
            "geometry": {"type": "Point", "coordinates": [76.138, 11.528]},
            "properties": {
                "name": "Mundakkai Debris Surge Track",
                "feature_type": "Debris Flow Channel",
                "elevation_m": 960,
                "event_date": "2024-07-30",
                "description": "High-velocity debris surge channel carrying boulders, uprooted timber, and liquefied saprolitic mud.",
                "source": "Geological Survey of India (GSI) Bhusanket Field Inspection",
            },
        },
        {
            "type": "Feature",
            "id": "OBS-WY-03",
            "geometry": {"type": "Point", "coordinates": [76.121, 11.512]},
            "properties": {
                "name": "Chooralmala Confluence Fan & Deposition Zone",
                "feature_type": "Deposition Fan",
                "elevation_m": 820,
                "event_date": "2024-07-30",
                "description": "River confluence deposition zone where debris flow overwhelmed settlement, market, and road bridge.",
                "source": "ISRO / NRSC & KSDMA Assessment Reports",
            },
        },
        {
            "type": "Feature",
            "id": "OBS-WY-POLY-01",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [76.152, 11.545],
                        [76.160, 11.540],
                        [76.148, 11.530],
                        [76.135, 11.522],
                        [76.125, 11.510],
                        [76.118, 11.513],
                        [76.128, 11.526],
                        [76.142, 11.538],
                        [76.152, 11.545],
                    ]
                ],
            },
            "properties": {
                "name": "Mundakkai–Chooralmala Documented Runout Corridor",
                "feature_type": "Mapped Debris Corridor Perimeter",
                "runout_length_km": 8.6,
                "area_ha": 312.4,
                "event_date": "2024-07-30",
                "description": "Observed 8.6-km debris flow corridor delineated from post-disaster high-resolution optical satellite imagery.",
                "source": "ISRO / NRSC Disaster Assessment (Aug 2024)",
            },
        },
    ],
}

CASE_WAYANAD = CaseStudy(
    id="wayanad_2024",
    name="Wayanad Mundakkai–Chooralmala Disaster (Kerala, 2024)",
    country="India",
    state_province="Kerala",
    district="Wayanad",
    locality="Mundakkai, Chooralmala & Punchirimattom (Meppadi Panchayat)",
    event_date="2024-07-30",
    disaster_type="Catastrophic Debris Flow & Multi-Stage Landslide Complex",
    short_description=(
        "On 30 July 2024, twin catastrophic debris flows originated on the upper slopes of "
        "Punchirimattom tea estates and travelled 8.6 km along the Iruvanipuzha river corridor, "
        "burying the settlements of Mundakkai and Chooralmala under heavy boulders and saturated saprolite."
    ),
    region_tag="western_ghats",
    temporal_tag="recent",
    analysis_mode="POST_EVENT_RESTORATION",
    verification_status="VERIFIED_OBSERVATION",
    readiness="READY_TO_ANALYZE",
    bounds={"minx": 76.08, "miny": 11.48, "maxx": 76.18, "maxy": 11.58},
    center=[11.53, 76.13],
    study_area_ha=12064.0,
    geometry_provenance="Verified watershed boundary and ISRO/NRSC satellite event corridor mapping",
    geometry_confidence="HIGH_CADASTRAL",
    source_references=[
        CaseStudySourceReference(
            title="Satellite-based Landslide Assessment of Wayanad Disaster, Kerala",
            organization="National Remote Sensing Centre (NRSC / ISRO), Hyderabad",
            publication_year=2024,
            document_type="Technical Disaster Assessment Report",
            verification_notes="Multi-temporal optical imagery from Cartosat-3 and Sentinel-2 mapping crown scarp and debris path.",
        ),
        CaseStudySourceReference(
            title="Bhusanket National Landslide Early Warning & Incident Database",
            organization="Geological Survey of India (GSI), Landslide Studies Division",
            publication_year=2024,
            document_type="National Geohazard Bulletin",
            verification_notes="Field geotechnical reconnaissance of saprolite failure surface and slope angles.",
        ),
        CaseStudySourceReference(
            title="Heavy Rainfall Observations for Western Ghats Ghat Section (July 2024)",
            organization="India Meteorological Department (IMD)",
            publication_year=2024,
            document_type="Meteorological Summary",
            verification_notes="Automated Weather Station (AWS) recorded >350 mm within 24 hours prior to failure.",
        ),
    ],
    terrain_datasets=[
        CaseStudyDataset(
            name="NASA SRTM NASADEM Global 1 Arc-Second (30m)",
            provider="NASA / USGS",
            resolution_m=30.0,
            dataset_type="elevation",
            status="VERIFIED_LOCAL",
            attribution="NASA JPL Caltech Open Data / OpenTopography",
            notes="Locally cached and verified raster covering Vythiri and Meppadi taluks.",
        ),
        CaseStudyDataset(
            name="Copernicus DEM GLO-30 Digital Elevation Model",
            provider="European Space Agency (ESA) / Airbus",
            resolution_m=30.0,
            dataset_type="elevation",
            status="STAC_ACQUIRABLE",
            attribution="Copernicus Open Access / Planetary Computer",
            notes="Alternative digital elevation fixture available via STAC API.",
        ),
    ],
    vegetation_datasets=[
        CaseStudyDataset(
            name="Sentinel-2 L2A Bottom-Of-Atmosphere NDVI (10m)",
            provider="European Space Agency (ESA)",
            resolution_m=10.0,
            dataset_type="multispectral_ndvi",
            status="VERIFIED_LOCAL",
            attribution="Copernicus Sentinel Data (2024)",
            notes="Pre-processed cloud-masked BOA NDVI composite covering the Western Ghats escarpment.",
        )
    ],
    observed_landslide_inventory=WAYANAD_OBSERVED_INVENTORY,
    inventory_summary="Observed 8.6 km debris corridor, crown initiation point, and confluence outwash fan mapped by ISRO NRSC.",
    data_acquisition_requirements="Requires DEM and Sentinel-2 L2A tile covering EPSG:4326 UTM 43N bounding box [76.08, 11.48, 76.18, 11.58].",
    licensing_and_attribution="Datasets available under NASA Open Data Policy and Copernicus Open Access Terms.",
    known_limitations=[
        "Uniform soil parameters assumed across complex metamorphic granulite/charnockite bedrock.",
        "Absence of official cadastral parcel property registers prevents legal ownership verification.",
        "Vegetation proxy (NDVI) measures photosynthetic openness, not specific root tensile strength of tea bushes vs native timber.",
    ],
    suggested_geotech_preset="wayanad_saprolite",
    suggested_cell_size_m=300.0,
    linked_project_id="wayanad_pilot",
)

# -----------------------------------------------------------------------------
# Case B: Malin, Maharashtra, India (30 July 2014)
# -----------------------------------------------------------------------------
MALIN_OBSERVED_INVENTORY = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "OBS-MLN-01",
            "geometry": {"type": "Point", "coordinates": [73.6875, 19.1633]},
            "properties": {
                "name": "Malin Hilltop Crown Scarp",
                "feature_type": "Initiation Scarp",
                "elevation_m": 920,
                "event_date": "2014-07-30",
                "description": "Upper hill slope failure initiation scarp where soil slip detached from basalt terrace.",
                "source": "Geological Survey of India (GSI) 2014 Malin Investigation Report",
            },
        },
        {
            "type": "Feature",
            "id": "OBS-MLN-02",
            "geometry": {"type": "Point", "coordinates": [73.6881, 19.1582]},
            "properties": {
                "name": "Malin Village Inundation Site",
                "feature_type": "Settlement Burial Zone",
                "elevation_m": 780,
                "event_date": "2014-07-30",
                "description": "Village settlement completely overwhelmed under 10–15 feet of liquefied mud and basalt boulders.",
                "source": "GSI & National Disaster Response Force (NDRF)",
            },
        },
        {
            "type": "Feature",
            "id": "OBS-MLN-POLY-01",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [73.6860, 19.1645],
                        [73.6895, 19.1638],
                        [73.6902, 19.1575],
                        [73.6868, 19.1568],
                        [73.6852, 19.1610],
                        [73.6860, 19.1645],
                    ]
                ],
            },
            "properties": {
                "name": "Malin Debris Slide Perimeter",
                "feature_type": "Documented Slide Footprint",
                "area_ha": 34.8,
                "event_date": "2014-07-30",
                "description": "Approximate boundary of translational debris slide documented by GSI field team.",
                "source": "GSI Special Publication (2014)",
            },
        },
    ],
}

CASE_MALIN = CaseStudy(
    id="malin_2014",
    name="Malin Debris Flow Disaster (Maharashtra, 2014)",
    country="India",
    state_province="Maharashtra",
    district="Pune",
    locality="Malin Village, Ambegaon Taluka (Western Ghats / Sahyadri Range)",
    event_date="2014-07-30",
    disaster_type="Rain-Triggered Translational Debris Avalanche",
    short_description=(
        "On the morning of 30 July 2014, an entire hillslope above the village of Malin collapsed "
        "following prolonged monsoon saturation, burying 44 houses and killing over 150 residents. "
        "The event remains a canonical example of catastrophic translational sliding in the Deccan Traps."
    ),
    region_tag="western_ghats",
    temporal_tag="historical",
    analysis_mode="PRE_EVENT_RETROSPECTIVE",
    verification_status="HISTORICAL_CATALOG",
    readiness="READY_TO_ANALYZE",
    bounds={"minx": 73.65, "miny": 19.13, "maxx": 73.72, "maxy": 19.19},
    center=[19.16, 73.68],
    study_area_ha=4120.0,
    geometry_provenance="Geological Survey of India post-disaster field maps and Sahyadri catchment delineation",
    geometry_confidence="MODERATE_WATERSHED",
    source_references=[
        CaseStudySourceReference(
            title="Geotechnical Investigation of Malin Landslide, Ambegaon Taluka, Pune District, Maharashtra",
            organization="Geological Survey of India (GSI), Central Region",
            publication_year=2014,
            document_type="Special Technical Investigation Publication",
            verification_notes="Comprehensive stratigraphic and slope failure survey detailing soil horizon and basalt trap bedding.",
        ),
        CaseStudySourceReference(
            title="Landslide Atlas of India (Western Ghats Section)",
            organization="National Remote Sensing Centre (NRSC / ISRO)",
            publication_year=2023,
            document_type="National Atlas",
            verification_notes="Catastrophic historical events catalogue and vulnerability ranking.",
        ),
    ],
    terrain_datasets=[
        CaseStudyDataset(
            name="Copernicus DEM GLO-30 (30m)",
            provider="European Space Agency / Planetary Computer STAC",
            resolution_m=30.0,
            dataset_type="elevation",
            status="STAC_ACQUIRABLE",
            attribution="Copernicus DEM Open Access",
            notes="Acquirable via automated one-click Planetary Computer STAC discovery.",
        )
    ],
    vegetation_datasets=[
        CaseStudyDataset(
            name="Sentinel-2 L2A Surface Reflectance (10m)",
            provider="European Space Agency",
            resolution_m=10.0,
            dataset_type="multispectral_ndvi",
            status="STAC_ACQUIRABLE",
            attribution="Copernicus Sentinel Data",
            notes="Available for multi-temporal retrospective and present-day vegetative comparison.",
        )
    ],
    observed_landslide_inventory=MALIN_OBSERVED_INVENTORY,
    inventory_summary="Documented GSI crown scarp, runout footprint, and village impact zone.",
    data_acquisition_requirements="Query Planetary Computer STAC for cop-dem-glo-30 and sentinel-2-l2a at [73.65, 19.13, 73.72, 19.19].",
    licensing_and_attribution="Government of India Open Access and ESA Copernicus Free & Open Data Policy.",
    known_limitations=[
        "Agricultural levelling and hill terrace modifications preceding the 2014 event are not resolved in 30m DEM.",
        "Rainfall-induced pore pressure surge requires calibrated transient hydrology.",
    ],
    suggested_geotech_preset="colluvial_clay_silt",
    suggested_cell_size_m=200.0,
    linked_project_id=None,
)

# -----------------------------------------------------------------------------
# Case C: Himachal Pradesh Monsoon Landslide Corridor, India (2023)
# -----------------------------------------------------------------------------
HIMACHAL_OBSERVED_INVENTORY = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "OBS-HP-01",
            "geometry": {"type": "Point", "coordinates": [77.1821, 31.6744]},
            "properties": {
                "name": "Pandoh Dam Road Slump",
                "feature_type": "Road-Cut Toe Failure",
                "elevation_m": 890,
                "event_date": "2023-07-10",
                "description": "Major highway road-cut slump and debris blockage along National Highway 21.",
                "source": "NRSC / ISRO Multi-temporal Landslide Inventory of HP (2023)",
            },
        },
        {
            "type": "Feature",
            "id": "OBS-HP-02",
            "geometry": {"type": "Point", "coordinates": [77.1235, 31.7112]},
            "properties": {
                "name": "Mandi Beas River Toe Scarp",
                "feature_type": "River Undercutting Scarp",
                "elevation_m": 820,
                "event_date": "2023-07-11",
                "description": "Toe scouring and valley slope reactivation triggered by swollen Beas River flood surge.",
                "source": "Geological Survey of India Northern Region Reconnaissance",
            },
        },
        {
            "type": "Feature",
            "id": "OBS-HP-03",
            "geometry": {"type": "Point", "coordinates": [77.2052, 31.7481]},
            "properties": {
                "name": "Aut Valley Tributary Debris Surge",
                "feature_type": "Debris Flow Tributary",
                "elevation_m": 940,
                "event_date": "2023-08-14",
                "description": "Violent debris flow charging down steep tributary torrent, carrying massive quartzite blocks.",
                "source": "Himachal Pradesh State Disaster Management Authority (HPSDMA)",
            },
        },
    ],
}

CASE_HIMACHAL = CaseStudy(
    id="himachal_2023",
    name="Himachal Pradesh Monsoon Landslide Corridor (Beas Basin / Mandi, 2023)",
    country="India",
    state_province="Himachal Pradesh",
    district="Mandi",
    locality="Beas River Gorge & Pandoh Highway Corridor",
    event_date="2023-07-10 to 2023-08-15",
    disaster_type="Regional Clustered Monsoon Debris Flows & Valley Slope Failures",
    short_description=(
        "During July and August 2023, extreme monsoon cloudbursts in Himachal Pradesh triggered over "
        "2,000 documented landslides. The Beas river valley between Mandi and Pandoh witnessed severe toe-scour "
        "reactivation, burying transport lifelines and impacting hundreds of hillside settlements."
    ),
    region_tag="himalayas",
    temporal_tag="recent",
    analysis_mode="POST_EVENT_RESTORATION",
    verification_status="HISTORICAL_CATALOG",
    readiness="READY_TO_ANALYZE",
    bounds={"minx": 77.05, "miny": 31.65, "maxx": 77.25, "maxy": 31.78},
    center=[31.71, 77.15],
    study_area_ha=14500.0,
    geometry_provenance="ISRO NRSC Himalayan Disaster Mapping & Beas Sub-catchment boundary",
    geometry_confidence="MODERATE_WATERSHED",
    source_references=[
        CaseStudySourceReference(
            title="Multi-temporal Landslide Inventory of Himachal Pradesh During Southwest Monsoon 2023",
            organization="National Remote Sensing Centre (NRSC / ISRO), Hyderabad",
            publication_year=2023,
            document_type="Technical Disaster Assessment Report",
            verification_notes="Mapped over 2,200 landslides across Mandi, Kullu, and Shimla using high-resolution Resourcesat-2A.",
        ),
        CaseStudySourceReference(
            title="Post-Disaster Needs Assessment (PDNA) - Himachal Pradesh Monsoon Disasters 2023",
            organization="Himachal Pradesh State Disaster Management Authority (HPSDMA) & NDMA",
            publication_year=2023,
            document_type="Government Post-Disaster Report",
            verification_notes="Assesses infrastructure impact, catchment degradation, and hillslope stabilization needs.",
        ),
    ],
    terrain_datasets=[
        CaseStudyDataset(
            name="Copernicus DEM GLO-30 (30m)",
            provider="European Space Agency / Planetary Computer",
            resolution_m=30.0,
            dataset_type="elevation",
            status="STAC_ACQUIRABLE",
            attribution="Copernicus Open Access",
            notes="Acquirable via automated one-click Planetary Computer STAC pipeline.",
        )
    ],
    vegetation_datasets=[
        CaseStudyDataset(
            name="Sentinel-2 L2A Multispectral NDVI (10m)",
            provider="European Space Agency",
            resolution_m=10.0,
            dataset_type="multispectral_ndvi",
            status="STAC_ACQUIRABLE",
            attribution="Copernicus Sentinel Data (2023)",
            notes="Sentinel-2 L2A tile available via Planetary Computer STAC.",
        )
    ],
    observed_landslide_inventory=HIMACHAL_OBSERVED_INVENTORY,
    inventory_summary="Documented highway road-cut failures, Beas toe scour zones, and tributary debris surge points from NRSC/ISRO.",
    data_acquisition_requirements="Copernicus GLO-30 DEM and Sentinel-2 L2A tile covering [77.05, 31.65, 77.25, 31.78].",
    licensing_and_attribution="ISRO Open Spatial Data & Copernicus Open Access.",
    known_limitations=[
        "Anthropogenic slope cuts (road widening, tunneling spoil) significantly alter local stability beyond 30m DEM resolution.",
        "Deep metamorphic jointing (phyllites/slates) governs wedge failures not fully captured by isotropic infinite-slope formulas.",
    ],
    suggested_geotech_preset="residual_sandy_loam",
    suggested_cell_size_m=250.0,
    linked_project_id=None,
)

# -----------------------------------------------------------------------------
# Case D: Kedarnath, Uttarakhand, India (June 2013)
# -----------------------------------------------------------------------------
KEDARNATH_OBSERVED_INVENTORY = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "OBS-KED-01",
            "geometry": {"type": "Point", "coordinates": [79.0621, 30.7584]},
            "properties": {
                "name": "Chorabari Lake Moraine Breach",
                "feature_type": "Moraine Breach Origin",
                "elevation_m": 3960,
                "event_date": "2013-06-17",
                "description": "Glacial moraine dam collapse releasing over 400,000 m³ of impounded water and debris.",
                "source": "Wadia Institute of Himalayan Geology (WIHG, Dehradun)",
            },
        },
        {
            "type": "Feature",
            "id": "OBS-KED-02",
            "geometry": {"type": "Point", "coordinates": [79.0669, 30.7342]},
            "properties": {
                "name": "Kedarnath Township Outwash Fan",
                "feature_type": "Deposition Fan & Settlement Inundation",
                "elevation_m": 3580,
                "event_date": "2013-06-17",
                "description": "Catastrophic debris surge entering Kedarnath township, diverting into eastern and western river channels.",
                "source": "WIHG & NRSC Disaster Assessment (2013)",
            },
        },
        {
            "type": "Feature",
            "id": "OBS-KED-03",
            "geometry": {"type": "Point", "coordinates": [79.0552, 30.7018]},
            "properties": {
                "name": "Rambara Gorge Debris Surge",
                "feature_type": "Runout Gorge Impact",
                "elevation_m": 2750,
                "event_date": "2013-06-17",
                "description": "Narrow gorge where debris surge completely wiped out Rambara settlement and pedestrian trail.",
                "source": "Geological Survey of India (GSI)",
            },
        },
    ],
}

CASE_KEDARNATH = CaseStudy(
    id="kedarnath_2013",
    name="Kedarnath Glacial Debris Surge & Landslide Complex (Uttarakhand, 2013)",
    country="India",
    state_province="Uttarakhand",
    district="Rudraprayag",
    locality="Mandakini Valley, Kedarnath Temple & Rambara Corridor",
    event_date="2013-06-16 to 2013-06-17",
    disaster_type="Glacial Lake Outburst Flood (GLOF) & High-Energy Debris Surge",
    short_description=(
        "On 16–17 June 2013, extraordinary rainfall and rapid snowmelt caused the collapse of "
        "Chorabari glacial moraine dam, sending massive surges of water, boulders, and pulverized granite "
        "down the Mandakini valley, devastating Kedarnath and downstream settlements."
    ),
    region_tag="himalayas",
    temporal_tag="historical",
    analysis_mode="PRE_EVENT_RETROSPECTIVE",
    verification_status="HISTORICAL_CATALOG",
    readiness="READY_TO_ANALYZE",
    bounds={"minx": 79.02, "miny": 30.68, "maxx": 79.12, "maxy": 30.77},
    center=[30.73, 79.07],
    study_area_ha=7800.0,
    geometry_provenance="Wadia Institute of Himalayan Geology & NRSC Kedarnath disaster extent mapping",
    geometry_confidence="HIGH_CADASTRAL",
    source_references=[
        CaseStudySourceReference(
            title="The Kedarnath Tragedy: Geomorphological and Geotechnical Assessment",
            organization="Wadia Institute of Himalayan Geology (WIHG), Dehradun",
            publication_year=2013,
            document_type="Scientific Monograph",
            verification_notes="Field mapping of Chorabari breach, high-water marks, and sediment outwash volumes.",
        ),
        CaseStudySourceReference(
            title="Kedarnath Disaster Rapid Mapping and Geomorphic Inventory",
            organization="National Remote Sensing Centre (NRSC / ISRO)",
            publication_year=2013,
            document_type="Disaster Response Atlas",
            verification_notes="Spaceborne mapping of debris fans, scarp failures, and bridge washouts.",
        ),
    ],
    terrain_datasets=[
        CaseStudyDataset(
            name="Copernicus DEM GLO-30 (30m)",
            provider="European Space Agency",
            resolution_m=30.0,
            dataset_type="elevation",
            status="STAC_ACQUIRABLE",
            attribution="Copernicus Open Access",
            notes="Available for high-altitude periglacial slope calculation.",
        )
    ],
    vegetation_datasets=[
        CaseStudyDataset(
            name="Sentinel-2 L2A Surface Reflectance (10m)",
            provider="European Space Agency",
            resolution_m=10.0,
            dataset_type="multispectral_ndvi",
            status="STAC_ACQUIRABLE",
            attribution="Copernicus Sentinel Data",
            notes="Multispectral imagery demonstrating alpine periglacial vs sub-alpine treeline limits.",
        )
    ],
    observed_landslide_inventory=KEDARNATH_OBSERVED_INVENTORY,
    inventory_summary="Chorabari moraine dam breach point, Kedarnath outwash fan, and Rambara gorge impact point.",
    data_acquisition_requirements="Copernicus GLO-30 DEM covering Mandakini headwaters [79.02, 30.68, 79.12, 30.77].",
    licensing_and_attribution="WIHG scientific publication citations and Copernicus Open Access.",
    known_limitations=[
        "Infinite-slope models evaluate translational soil slips, not glacial moraine dam hydrodynamic breaches.",
        "Alpine terrain above 3,500m lies beyond the biological limit of forest tree planting.",
    ],
    suggested_geotech_preset="residual_sandy_loam",
    suggested_cell_size_m=300.0,
    linked_project_id=None,
)

# -----------------------------------------------------------------------------
# Case E: Gorkha–Budhi Gandaki, Nepal (11 October 2026)
# -----------------------------------------------------------------------------
NEPAL_OBSERVED_INVENTORY = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "OBS-NPL-01",
            "geometry": {"type": "Point", "coordinates": [84.8452, 28.2851]},
            "properties": {
                "name": "Budhi Gandaki Provisional Toe Failure",
                "feature_type": "Reported Scarp Area",
                "elevation_m": 1850,
                "event_date": "2026-10-11",
                "description": "Reported steep valley-wall failure site undergoing active emergency reconnaissance.",
                "source": "Nepal National Disaster Risk Reduction & Management Authority (NDRRMA)",
            },
        },
        {
            "type": "Feature",
            "id": "OBS-NPL-02",
            "geometry": {"type": "Point", "coordinates": [84.8624, 28.2410]},
            "properties": {
                "name": "Downstream Budhi Gandaki Surge Zone",
                "feature_type": "River Obstruction & Surge Zone",
                "elevation_m": 1420,
                "event_date": "2026-10-11",
                "description": "Downstream river gorge area subject to flash-flood alert following reported landslide debris entry.",
                "source": "Department of Hydrology and Meteorology (DHM), Nepal",
            },
        },
    ],
}

CASE_NEPAL = CaseStudy(
    id="nepal_gorkha_2026",
    name="Gorkha–Budhi Gandaki Valley Landslide & Flash-Flood (Nepal, 2026)",
    country="Nepal",
    state_province="Gandaki Province",
    district="Gorkha",
    locality="Budhi Gandaki River Valley / Manaslu Foothills",
    event_date="2026-10-11",
    disaster_type="Valley Slope Failure & River Obstruction Flash-Flood Context",
    short_description=(
        "On 11 October 2026, severe valley slope failures were reported along the deeply incised "
        "Budhi Gandaki river gorge in northern Gorkha district. Preliminary warnings identified potential "
        "temporary river damming and downstream flash-flood risks along the Manaslu trekking corridor."
    ),
    region_tag="nepal",
    temporal_tag="recent",
    analysis_mode="MONITORING_CONTEXT",
    verification_status="PROVISIONAL_RECENT",
    readiness="AWAITING_ADDITIONAL_DATA",
    bounds={"minx": 84.75, "miny": 28.18, "maxx": 84.95, "maxy": 28.35},
    center=[28.26, 84.85],
    study_area_ha=19200.0,
    geometry_provenance="Provisional incident reports and administrative river valley bounds",
    geometry_confidence="PROVISIONAL_CORRIDOR",
    source_references=[
        CaseStudySourceReference(
            title="Emergency Incident Bulletin on Valley Slope Failures in Gandaki River Basins",
            organization="National Disaster Risk Reduction and Management Authority (NDRRMA), Nepal",
            publication_year=2026,
            document_type="Provisional Situation Bulletin",
            verification_notes="Preliminary incident reports; comprehensive post-disaster field lidar pending.",
        ),
        CaseStudySourceReference(
            title="Hydrological River Warning & Flood Monitoring Alert",
            organization="Department of Hydrology and Meteorology (DHM), Government of Nepal",
            publication_year=2026,
            document_type="Hydrometeorological Advisory",
            verification_notes="River gauge sensor anomalies recorded along the Budhi Gandaki catchment.",
        ),
        CaseStudySourceReference(
            title="Himalayan Landslide and Dam Hazard Monitoring System",
            organization="International Centre for Integrated Mountain Development (ICIMOD)",
            publication_year=2026,
            document_type="Regional Geohazard Monitor",
            verification_notes="Ongoing satellite radar coherence monitoring across High Himalayan valleys.",
        ),
    ],
    terrain_datasets=[
        CaseStudyDataset(
            name="Copernicus DEM GLO-30 (30m)",
            provider="European Space Agency",
            resolution_m=30.0,
            dataset_type="elevation",
            status="STAC_ACQUIRABLE",
            attribution="Copernicus Open Access",
            notes="30m elevation baseline available for exploratory slope and drainage analysis.",
        )
    ],
    vegetation_datasets=[
        CaseStudyDataset(
            name="Sentinel-2 L2A Surface Reflectance (10m)",
            provider="European Space Agency",
            resolution_m=10.0,
            dataset_type="multispectral_ndvi",
            status="STAC_ACQUIRABLE",
            attribution="Copernicus Sentinel Data",
            notes="Optical satellite coverage subject to post-monsoon cloud cover constraints.",
        )
    ],
    observed_landslide_inventory=NEPAL_OBSERVED_INVENTORY,
    inventory_summary="Provisional scarp location and downstream river surge alert points (authoritative spatial polygon closure pending).",
    data_acquisition_requirements="Copernicus GLO-30 STAC tile covering Budhi Gandaki gorge [84.75, 28.18, 84.95, 28.35].",
    licensing_and_attribution="NDRRMA Public Disaster Bulletins and Copernicus Open Access.",
    known_limitations=[
        "Authoritative post-event high-resolution aerial survey data are actively evolving and not yet certified.",
        "Spatial perimeter is provisional; users should not interpret this entry as an official cadastral disaster footprint.",
        "Deep seismically induced fissuring from the 2015 Gorkha earthquake sequence predisposes slopes in ways standard shallow infinite slope models cannot fully represent.",
    ],
    suggested_geotech_preset="colluvial_clay_silt",
    suggested_cell_size_m=300.0,
    linked_project_id=None,
)

# -----------------------------------------------------------------------------
# Case F: Cascade Foothills Demonstration Basin (Offline Algorithm Benchmark)
# -----------------------------------------------------------------------------
CASE_CASCADE_DEMO = CaseStudy(
    id="cascade_demo",
    name="Cascade Foothills Demonstration Basin (Offline Algorithm Benchmark)",
    country="United States",
    state_province="Washington",
    district="King County",
    locality="Cascade Mountain Foothills Synthetic Basin",
    event_date="N/A (Development Benchmark)",
    disaster_type="Synthetic Benchmarking Fixture",
    short_description=(
        "Deterministic synthetic 256x256 test DEM with known elevation gradients, designed for offline "
        "algorithmic testing, automated unit test suites, and UI development without requiring live network access."
    ),
    region_tag="offline_demo",
    temporal_tag="benchmark",
    analysis_mode="OFFLINE_TESTING",
    verification_status="OFFLINE_BENCHMARK",
    readiness="READY_TO_ANALYZE",
    bounds={"minx": -121.82, "miny": 47.42, "maxx": -121.74, "maxy": 47.48},
    center=[47.45, -121.78],
    study_area_ha=450.0,
    geometry_provenance="Synthetic test fixture coordinates",
    geometry_confidence="SYNTHETIC",
    source_references=[
        CaseStudySourceReference(
            title="TerraShield AI Offline Synthetic Development Fixture",
            organization="TerraShield AI Engineering Team",
            publication_year=2026,
            document_type="Software Testing Specification",
            verification_notes="Synthetic fixture: DO NOT interpret as observations from a real disaster.",
        )
    ],
    terrain_datasets=[
        CaseStudyDataset(
            name="Synthetic 256x256 Test DEM",
            provider="TerraShield AI Test Fixtures",
            resolution_m=30.0,
            dataset_type="elevation",
            status="SYNTHETIC",
            attribution="TerraShield AI Internal",
            notes="Mathematically generated elevation gradient for regression testing.",
        )
    ],
    vegetation_datasets=[],
    observed_landslide_inventory=None,
    inventory_summary="No real landslide inventory exists. Purely synthetic test fixture.",
    data_acquisition_requirements="None (bundled offline in data/sample/sample_dem.tif).",
    licensing_and_attribution="TerraShield AI Project Repository Internal.",
    known_limitations=[
        "Contains synthetic elevation data and illustrative geotechnical parameters.",
        "Must NOT be cited or represented as real historical landslide observations.",
    ],
    suggested_geotech_preset="glacial_till_demo",
    suggested_cell_size_m=300.0,
    linked_project_id="cascade_demo",
)

# Registry dictionary
CASE_STUDIES_REGISTRY: Dict[str, CaseStudy] = {
    "wayanad_2024": CASE_WAYANAD,
    "malin_2014": CASE_MALIN,
    "himachal_2023": CASE_HIMACHAL,
    "kedarnath_2013": CASE_KEDARNATH,
    "nepal_gorkha_2026": CASE_NEPAL,
    "cascade_demo": CASE_CASCADE_DEMO,
}


class CaseStudyRegistry:
    """Access interface for the Case Study Library."""

    @classmethod
    def list_all(cls, region: Optional[str] = None, readiness: Optional[str] = None) -> List[CaseStudy]:
        """List all registered case studies with optional filtering."""
        items = list(CASE_STUDIES_REGISTRY.values())
        if region:
            items = [c for c in items if c.region_tag == region]
        if readiness:
            items = [c for c in items if c.readiness == readiness]
        return items

    @classmethod
    def get(cls, case_id: str) -> Optional[CaseStudy]:
        """Retrieve a single case study by ID."""
        return CASE_STUDIES_REGISTRY.get(case_id)
