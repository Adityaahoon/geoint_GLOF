# GlacioGuard AI – REST API contract

Base URL: `http://localhost:8000/api` (Vite dev server proxies `/api` → backend). Interactive docs: `/docs`.
All geometries are GeoJSON in EPSG:4326. Dates ISO-8601. Errors: `{"detail": "message"}` with 4xx/5xx.
Long-running operations return `{"job_id": int}`; poll `GET /jobs/{id}`.

**Scientific-honesty contract for the UI:** any list can be empty. Empty ⇒ show a "no data yet / how to generate"
state, never placeholder numbers. Fields named `caveats`, `quality_flags`, `missing_parameters`, `uncertainty`,
`status`, `is_trained_model`, `scenario_type` MUST be displayed where relevant.

## System
- `GET /health` → `{status, version, database:{dialect, ok}, gee:{available, mode, error, project}, stac:{available:true, providers:[..]}, torch:{available, version, device}, xgboost:{available, error}, data:{dem:bool, osm:bool, composites:int, lakes:int}}`
- `GET /study-area` → `{name, bbox:[w,s,e,n], geometry, utm_epsg, regions:{key:{name,bbox,geometry}}, reference_points:[{name,lat,lon,type}], timeline_periods:[{key,label,start,end}], standard_comparisons:[[a,b]], disaster_context:str}`
- `GET /dashboard/summary` → `{coverage:{years:[{year, missions:[{mission,status,valid_fraction,scene_count,composite_id}]}], dem_available, osm_available, terrain_available}, lakes:{count, total_area_ha, reference_year, method}, indicators:{series:{indicator:[{year,value,mission,quality_flags}]}}, susceptibility:{Low,Moderate,High,"Very High", method, is_trained_model}, recent_jobs:[Job], rainfall_available}`
- `GET /jobs?limit=50` → `[Job]`; `GET /jobs/{id}` → `Job = {id, job_type, status:"queued|running|completed|failed", progress:0..1, parameters, result, log, error, created_at, started_at, finished_at}`

## Rasters & vectors (generic)
- `GET /rasters?kind=&category=&year=` → `[RasterAsset]` where `RasterAsset = {id,name,kind,category,path_name,crs,width,height,band_count,dtype,resolution_x,resolution_y,nodata,bounds_wgs84,statistics:{bands:[{band,min,max,mean,std,valid_pixels,valid_fraction}],band_descriptions},year,acquired_start,acquired_end,source,processing,is_original,parent_id,created_at}`
- `GET /rasters/{id}` → `RasterAsset`
- `GET /rasters/{id}/overlay?bands=4,3,2&cmap=ndvi&vmin=&vmax=&categorical=water` → `{image_url, bounds:[[S,W],[N,E]], legend:{cmap,vmin,vmax,unit,categories?:[{value,label,color}]}}` (image_url is a PNG for Leaflet `ImageOverlay`)
- `GET /rasters/{id}/download` → GeoTIFF file
- `GET /vectors` → `[{key,name,category,feature_count,source,attribution,url}]`; `GET /vectors/{key}` → GeoJSON FeatureCollection

## Satellite
- `GET /satellite/missions` → `[{mission,label,instrument,gee_collection,stac_collection,native_resolution_m,bands:{common:native},operational:[start,end|null],notes:[..],citation}]`
- `POST /satellite/collections` body `{mission, start_date, end_date, region="full_aoi", max_cloud=60, provider="auto|gee|stac"}` → `{provider, count, scenes:[{scene_id,datetime,cloud_cover,footprint,preview_url,quality_flags}], notes:[..]}`
- `POST /satellite/composite` body `{year, mission, region="full_aoi", season_start="09-15", season_end="11-15", max_cloud=60, resolution=null, max_scenes=8, provider="auto"}` → `{job_id}`
- `POST /satellite/composite/batch` body `{start_year, end_year, mission="auto", region, ...}` → `{job_id}` ("auto" = best Landsat per year)
- `GET /satellite/composites?region=` → `[{composite_id, year, mission, region, window:[s,e], scene_count, scenes:[{scene_id,datetime,cloud_cover}], valid_fraction, quality_flags, resolution_m, provider, raster: RasterAsset}]`
- `POST /satellite/export` body `{composite_id}` (local GeoTIFF download URL) or `{year, mission, region, provider:"gee"}` → `{download_url}` | `{task_id, state}`

## GeoTIFF workspace
- `POST /geotiff/upload` multipart `files` (one .tif/.tiff/.geojson/.gpkg, or a .shp with .shx/.dbf/.prj siblings, or a .zip shapefile) → `{type:"raster"|"vector", asset:{...metadata}}`
- `GET /geotiff/uploads` → `{rasters:[RasterAsset], vectors:[VectorAsset]}`; `VectorAsset = {id,name,original_filename,crs,feature_count,geometry_types,columns,bounds_wgs84,created_at}`
- `GET /geotiff/metadata/{id}` → full metadata `{width,height,band_count,dtypes,crs,epsg,is_projected,resolution,units,bounds,nodata,band_descriptions,statistics,bounds_wgs84,warnings?}`
- `POST /geotiff/process` body `{asset_id, operation:"reproject|clip|resample|index|statistics", params}`
  - reproject `{dst_crs:"EPSG:32644", resolution?, resampling:"bilinear|nearest|cubic"}`; clip `{region:"full_aoi"|..., geometry?}`; resample `{resolution, resampling}`; index `{index:"ndwi|mndwi|ndvi|nbr|ndsi", band_map:{green:2,nir:4,...}}`
  → `{asset: RasterAsset}` (new processed asset; original untouched)
- `GET /vectors/uploads/{id}` → GeoJSON (reprojected to 4326)

## Lakes
- `POST /lakes/detect` body `{composite_id, method:"mndwi_otsu"|"unet", min_area_ha=1.0, max_slope_deg=20, threshold=null}` → `{job_id}`
- `GET /lakes/inventory?year=` → GeoJSON FC; feature props `{lake_id, lake_code, name, area_ha, perimeter_m, elevation_m, year, mission, method, observed_start, observed_end, first_detected, last_detected, n_observations, susceptibility_category}`
- `GET /lakes/{id}` → `{lake:{...}, observations:[{year,mission,method,area_ha,perimeter_m,observed_start,observed_end,valid_pixel_fraction,geometry}]}`
- `GET /lakes/statistics` → `{annual:[{year,mission,method,lake_count,total_area_ha,valid_fraction}], per_lake:[{lake_id,lake_code,name,series:[{year,area_ha}]}]}`

## Change detection / glacier / disaster
- `GET /change-detection/indicators?region=full_aoi` → `{region, indicators:{name:{unit,description,series:[{year,value,mission,valid_fraction,scene_count,window,quality_flags}]}}}` names: `water_area_ha, snow_ice_area_ha, ndvi_mean, vegetated_area_ha, exposed_ground_area_ha, mndwi_mean`
- `POST /change-detection/analyse` body `{year_a, year_b, indicator:"water|vegetation|snow_ice|exposed_ground|mndwi|ndvi|nbr", region}` → `{id, year_a, year_b, mission_a, mission_b, indicator, statistics:{area_gain_ha, area_loss_ha, stable_ha, net_change_ha, mean_difference, ...}, caveats:[..], rasters:{difference:RasterAsset, transition:RasterAsset, before:RasterAsset, after:RasterAsset}, legend}`
- `GET /change-detection/results` → list of prior analyses
- `GET /glacier/summary?region=chorabari` → `{series:[{year,snow_ice_area_ha,mission,quality_flags}], outlines: GeoJSON|null, outline_source, notes}`
- `GET /disaster/context` → `{context, mechanisms:[{key,label,description}], key_dates, scenes:{pre:[..], post:[..]}}`
- `POST /disaster/compare` body `{pre_year=2011|2012, post_year=2013|2014, region="mandakini_corridor"}` → like change analyse, plus `{indicators:[...], affected_locations:[{name,lat,lon,change_summary}]}`

## GLOF susceptibility
- `GET /glof/methodology` → `{method, version, is_trained_model, description, criteria:[{key,label,weight,scoring,rationale,reference}], classes:[{label,min,max}], limitations:[..]}`
- `POST /glof/assess` → `{job_id}`
- `GET /glof/assessments` → `[{lake_id, lake_code, name, method, is_trained_model, score, category, factors:{key:{value,unit,score,weight,available}}, missing_parameters:[..], uncertainty:{score_range:[lo,hi], completeness, category_range:[..]}, created_at}]`
- `GET /glof/ml-status` → `{trainable:false, reason, required_data:[..], label_file_present}`

## Terrain
- `POST /terrain/fetch-dem` body `{source:"copernicus"}` → `{job_id}`
- `POST /terrain/analyse` body `{stream_threshold_km2=1.0}` → `{job_id}`
- `GET /terrain/summary` → `{available, statistics, products:{name:RasterAsset}, vectors:[...], dem_source}`
- `POST /terrain/flowpath` body `{lake_id}` or `{lon,lat}` → `{name, geometry(LineString), length_m, elevation_drop_m, profile:[{distance_m,elevation_m}], method, caveat}`

## Flood scenarios (hypothetical, HEC-RAS 2D workflow)
- `GET /flood/scenarios` → `[{id,name,source_lake_id,scenario_type:"hypothetical",description,hydrograph,hydrograph_source,assumptions,boundary_conditions,status:"defined|exported|results_imported",created_at,results:[FloodResult]}]`
- `POST /flood/scenarios` body `{name, source_lake_id, description, hydrograph:{time_s:[],discharge_m3s:[]}|null, hydrograph_source, assumptions:[..], downstream_length_km=25, manning_n=0.06}` → scenario
- `POST /flood/scenarios/{id}/export` → `{download_url}` (zip: terrain GeoTIFF, domain & flowpath GeoJSON, hydrograph CSV template, README)
- `POST /flood/scenarios/{id}/results` multipart `file` + form `variable:"depth|velocity|wse|arrival_time|duration"`, `model_software` → FloodResult
- `FloodResult = {id, scenario_id, variable, raster:RasterAsset, model_software, statistics:{max,mean,area_ha_wet}, extent_geometry}`

## Exposure
- `POST /exposure/fetch-osm` → `{job_id}`
- `GET /exposure/infrastructure?category=` → GeoJSON FC (props `{category,name,osm_id,tags}`); categories: settlement, building, road, bridge, hospital, school, public, helipad, power
- `GET /exposure/infrastructure/summary` → `{counts:{category:n}, road_length_km, source, retrieved_at}`
- `POST /exposure/analyse` body `{scenario_id}` (overlay with imported flood extent) or `{mode:"flowpath_corridor", lake_id, buffer_m=250, hand_max_m=20}` → `{id, analysis_type, statistics:{buildings, road_length_km, bridges, settlements:[..], by_category}, features: GeoJSON FC, caveat}`

## Rainfall
- `GET /rainfall?source=` → `{sources_available:[..], series:{source:[{date,precipitation_mm}]}, notes}`
- `POST /rainfall/fetch` body `{source:"chirps|gpm|nasa_power", start_year=2000, end_year=2026}` → `{job_id}`

## Model Lab
- `GET /models/datasets` → `{segmentation:{status:"awaiting_training_data"|"ready", image_tiles, mask_tiles, splits:{train,val,test}, split_strategy, directory, instructions:[..]}, susceptibility:{status, labelled_events, instructions}}`
- `POST /models/prepare-tiles` body `{composite_id, tile_size=256}` → `{job_id}` (writes image tiles + weak MNDWI pre-labels flagged "unverified" for manual correction)
- `POST /models/train` body `{model_type:"unet"|"deeplabv3plus", epochs=50, batch_size=8, learning_rate=1e-3, tile_size=256}` → `{job_id, run_id}` | 409 if no verified masks
- `GET /models/runs` → `[{id,model_type,task,status,dataset_summary,hyperparameters,history:[{epoch,train_loss,val_loss,val_iou,val_dice}],checkpoint_path,best_epoch,created_at,finished_at,evaluations:[{split,metrics:{iou,dice,precision,recall,f1,accuracy},confusion_matrix:[[tn,fp],[fn,tp]],sample_count}]}]`
- `POST /models/evaluate` body `{run_id, split:"test"}` → `{job_id}`

## Reports
- `POST /reports/generate` body `{title?, sections:["overview","study_area","methodology","datasets","observations","change_detection","deep_learning","susceptibility","flood","exposure","limitations","references"]}` → `{report_id, download_url}`
- `GET /reports` → `[{id,title,created_at,download_url}]`; `GET /reports/{id}/download` → PDF

