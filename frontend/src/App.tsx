import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, ClipboardEvent, DragEvent } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, LngLatBoundsLike, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./App.css";

type BackendStatus = "checking" | "online" | "offline";

type ApiError = {
  code: string;
  message: string;
  details?: unknown;
};

type ApiResponse<T> = {
  ok: boolean;
  data: T;
  error: ApiError | null;
};

type HealthResponse = {
  service: string;
  version: string;
  environment: string;
};

type Depot = {
  id: number;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  default_start_time: string;
  active: boolean;
  created_at: string;
  updated_at: string;
};

type Vehicle = {
  id: number;
  name: string;
  max_payload_lbs: number;
  max_volume_cubic_ft: number | null;
  max_route_miles: number | null;
  max_route_minutes: number | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

type VehicleFormState = {
  name: string;
  max_payload_lbs: string;
  max_volume_cubic_ft: string;
  max_route_miles: string;
  max_route_minutes: string;
  active: boolean;
};

type StopType = "pickup" | "delivery" | "pickup_delivery";

type Stop = {
  id: number;
  customer_id: number | null;
  name: string;
  address: string;
  normalized_address: string;
  latitude: number;
  longitude: number;
  stop_type: StopType;
  quantity: number;
  weight_lbs: number;
  service_minutes: number;
  priority: number;
  earliest_time: string | null;
  latest_time: string | null;
  special_instructions: string | null;
  address_status: string;
  active: boolean;
  created_at: string;
  updated_at: string;
};

type StopFormState = {
  name: string;
  address: string;
  normalized_address: string;
  latitude: string;
  longitude: string;
  stop_type: StopType;
  quantity: string;
  weight_lbs: string;
  service_minutes: string;
  priority: string;
  earliest_time: string;
  latest_time: string;
  special_instructions: string;
  address_status: string;
  active: boolean;
};

type RouteStopAssignment = {
  id: number;
  stop_id: number;
  stop_order: number;
  eta: string | null;
  departure_time: string | null;
  distance_from_previous_miles: number | null;
  travel_duration_minutes: number | null;
  service_duration_minutes: number | null;
};

type Route = {
  id: number;
  name: string;
  depot_id: number | null;
  vehicle_id: number | null;
  active: boolean;
  stops: RouteStopAssignment[];
  created_at: string;
  updated_at: string;
};

type RouteVersion = {
  id: number;
  route_id: number;
  version_number: number;
  solver_status: string;
  total_distance_miles: number | null;
  total_travel_duration_minutes: number | null;
  total_service_duration_minutes: number | null;
  total_route_duration_minutes: number | null;
  route_metrics: Record<string, unknown> | null;
  created_at: string;
};

type RouteFormState = {
  name: string;
  depot_id: string;
  vehicle_id: string;
  selected_stop_id: string;
};

type Coordinate = {
  latitude: number;
  longitude: number;
};

type RouteGeometry = {
  polyline: string | null;
  coordinates: Coordinate[];
};

type RouteLeg = {
  start: Coordinate;
  end: Coordinate;
  distance_miles: number;
  travel_duration_minutes: number;
  geometry: RouteGeometry | null;
};

type OptimizedStop = {
  stop_id: number;
  stop_order: number;
  eta_minutes: number | null;
  departure_minutes: number | null;
  distance_from_previous_miles: number | null;
  travel_duration_minutes: number | null;
  service_duration_minutes: number | null;
};

type RouteOptimizationResult = {
  route_id: number;
  route_version_id: number;
  version_number: number;
  solver_status: string;
  optimized_stop_order: number[];
  stops: OptimizedStop[];
  metrics: {
    total_distance_miles: number;
    total_travel_duration_minutes: number;
    total_service_duration_minutes: number;
    total_route_duration_minutes: number;
    number_of_stops: number;
    payload_lbs: number;
    remaining_capacity_lbs: number;
    cache_hit: boolean;
  };
  geometry: RouteGeometry;
  legs: RouteLeg[];
  coordinates: Coordinate[];
};

type DispatchVehicleRoute = {
  vehicle_id: number;
  vehicle_name: string;
  optimized_stop_order: number[];
  total_distance_miles: number;
  total_travel_duration_minutes: number;
  total_service_duration_minutes: number;
  total_route_duration_minutes: number;
  payload_lbs: number;
  remaining_capacity_lbs: number | null;
  geometry: RouteGeometry;
  legs: RouteLeg[];
  coordinates: Coordinate[];
};

type DispatchOptimizeResult = {
  solver_status: string;
  depot_id: number;
  routes: DispatchVehicleRoute[];
};

type AIInstructionAction = {
  action_type:
    | "set_stop_latest_arrival"
    | "set_stop_earliest_arrival"
    | "set_route_return_deadline"
    | "set_stop_priority"
    | "set_stop_service_minutes"
    | "assign_vehicle"
    | "assign_depot";
  target: "route" | "stop" | "vehicle" | "depot";
  entity_id: number | null;
  fields: Record<string, unknown>;
  rationale: string | null;
  confidence: number;
};

type AIInstructionParseResult = {
  original_command: string;
  summary: string;
  proposed_actions: AIInstructionAction[];
  requires_user_confirmation: boolean;
};

type AIResultExplanation = {
  summary: string;
  observations: string[];
  caveats: string[];
};

type AIRouteExplanationResponse = {
  question: string;
  intent: string;
  explanation: AIResultExplanation;
  application_facts: Record<string, unknown>;
};

type ProviderStatusState = "ok" | "warning" | "unavailable";

type ProviderStatusItem = {
  name: string;
  status: ProviderStatusState;
  message: string;
  details: Record<string, unknown>;
};

type ProviderStatusReport = {
  overall_status: ProviderStatusState;
  providers: ProviderStatusItem[];
};

type SystemHealthDisplayStatus = "ONLINE" | "OFFLINE" | "MISSING" | "DISABLED";

type SystemHealthScope = "LOCAL" | "EXTERNAL";

type MapStopMarker = {
  stop: Stop;
  order: number;
};

type ScreenshotPreview = {
  url: string;
  name: string;
  type: string;
  size: number;
};

type ExtractedStop = {
  customer: string | null;
  address: string | null;
  stop_type: "pickup" | "delivery" | "pickup_delivery" | "unknown";
  quantity: number | null;
  weight_lbs: number | null;
  time_window: string | null;
  notes: string | null;
  confidence: number;
};

type VisionExtractionResult = {
  stops: ExtractedStop[];
};

type ReviewStatus =
  | "confirmed"
  | "low_confidence"
  | "ambiguous"
  | "not_found"
  | "user_review_required";

type ScreenshotReviewRow = {
  id: string;
  customer: string;
  address: string;
  normalized_address: string;
  latitude: number | null;
  longitude: number | null;
  geocode_status: string;
  geocode_message: string;
  stop_type: "pickup" | "delivery" | "pickup_delivery" | "unknown";
  quantity: string;
  weight_lbs: string;
  time_window: string;
  notes: string;
  confidence: string;
  validation_status: ReviewStatus;
};

type GeocodeReviewResult = {
  row_id: string;
  original_address: string;
  normalized_address: string | null;
  latitude: number | null;
  longitude: number | null;
  geocode_status: string;
  validation_status: ReviewStatus;
  confidence: number;
  provider: string;
  message: string | null;
};

const acceptedScreenshotTypes = new Set([
  "image/png",
  "image/jpeg",
  "image/webp"
]);

const acceptedScreenshotExtensions = [".png", ".jpg", ".jpeg", ".webp"];
const maxScreenshotBytes = 8 * 1024 * 1024;

const reviewStatuses: ReviewStatus[] = [
  "confirmed",
  "low_confidence",
  "ambiguous",
  "not_found",
  "user_review_required"
];

const systemHealthDefinitions: {
  providerName: string;
  label: string;
  scope: SystemHealthScope;
}[] = [
  { providerName: "backend", label: "FastAPI", scope: "LOCAL" },
  { providerName: "database", label: "SQLite", scope: "LOCAL" },
  { providerName: "ollama", label: "Ollama", scope: "LOCAL" },
  { providerName: "valhalla", label: "Valhalla", scope: "LOCAL" },
  { providerName: "geocoder", label: "Geocoder", scope: "EXTERNAL" },
  { providerName: "map_data", label: "Map data", scope: "LOCAL" }
];

const emptyVehicleForm: VehicleFormState = {
  name: "",
  max_payload_lbs: "",
  max_volume_cubic_ft: "",
  max_route_miles: "",
  max_route_minutes: "",
  active: true
};

const emptyStopForm: StopFormState = {
  name: "",
  address: "",
  normalized_address: "",
  latitude: "",
  longitude: "",
  stop_type: "delivery",
  quantity: "1",
  weight_lbs: "0",
  service_minutes: "0",
  priority: "0",
  earliest_time: "",
  latest_time: "",
  special_instructions: "",
  address_status: "confirmed",
  active: true
};

const emptyRouteForm: RouteFormState = {
  name: "",
  depot_id: "",
  vehicle_id: "",
  selected_stop_id: ""
};

const navigationItems = [
  "Dashboard",
  "Import",
  "Routes",
  "Dispatch",
  "Stops",
  "Vehicles",
  "Drivers",
  "Customers",
  "Route History",
  "Costs",
  "Settings"
];

async function requestJson<T>(
  url: string,
  init?: RequestInit
): Promise<ApiResponse<T>> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    }
  });
  const body = (await response.json()) as ApiResponse<T>;

  if (!response.ok || !body.ok) {
    throw new Error(body.error?.message ?? `Request failed with ${response.status}`);
  }

  return body;
}

function numberOrNull(value: string): number | null {
  if (value.trim() === "") {
    return null;
  }

  return Number(value);
}

function vehicleToForm(vehicle: Vehicle): VehicleFormState {
  return {
    name: vehicle.name,
    max_payload_lbs: String(vehicle.max_payload_lbs),
    max_volume_cubic_ft:
      vehicle.max_volume_cubic_ft === null
        ? ""
        : String(vehicle.max_volume_cubic_ft),
    max_route_miles:
      vehicle.max_route_miles === null ? "" : String(vehicle.max_route_miles),
    max_route_minutes:
      vehicle.max_route_minutes === null ? "" : String(vehicle.max_route_minutes),
    active: vehicle.active
  };
}

function vehicleFormToPayload(form: VehicleFormState) {
  return {
    name: form.name.trim(),
    max_payload_lbs: Number(form.max_payload_lbs),
    max_volume_cubic_ft: numberOrNull(form.max_volume_cubic_ft),
    max_route_miles: numberOrNull(form.max_route_miles),
    max_route_minutes: numberOrNull(form.max_route_minutes),
    active: form.active
  };
}

function stopToForm(stop: Stop): StopFormState {
  return {
    name: stop.name,
    address: stop.address,
    normalized_address: stop.normalized_address,
    latitude: String(stop.latitude),
    longitude: String(stop.longitude),
    stop_type: stop.stop_type,
    quantity: String(stop.quantity),
    weight_lbs: String(stop.weight_lbs),
    service_minutes: String(stop.service_minutes),
    priority: String(stop.priority),
    earliest_time: stop.earliest_time?.slice(0, 5) ?? "",
    latest_time: stop.latest_time?.slice(0, 5) ?? "",
    special_instructions: stop.special_instructions ?? "",
    address_status: stop.address_status,
    active: stop.active
  };
}

function stopFormToPayload(form: StopFormState) {
  return {
    name: form.name.trim(),
    address: form.address.trim(),
    normalized_address: form.normalized_address.trim(),
    latitude: Number(form.latitude),
    longitude: Number(form.longitude),
    stop_type: form.stop_type,
    quantity: Number(form.quantity),
    weight_lbs: Number(form.weight_lbs),
    service_minutes: Number(form.service_minutes),
    priority: Number(form.priority),
    earliest_time: form.earliest_time === "" ? null : form.earliest_time,
    latest_time: form.latest_time === "" ? null : form.latest_time,
    special_instructions:
      form.special_instructions.trim() === ""
        ? null
        : form.special_instructions.trim(),
    address_status: form.address_status.trim(),
    active: form.active
  };
}

function App() {
  const [activeView, setActiveView] = useState(navigationItems[0]);
  const [backendStatus, setBackendStatus] =
    useState<BackendStatus>("checking");
  const [backendDetails, setBackendDetails] = useState<string>("Checking");

  useEffect(() => {
    let cancelled = false;

    async function checkBackendHealth() {
      try {
        const health = await requestJson<HealthResponse>("/api/health");

        if (!cancelled) {
          setBackendStatus("online");
          setBackendDetails(
            `${health.data.service} ${health.data.version} (${health.data.environment})`
          );
        }
      } catch {
        if (!cancelled) {
          setBackendStatus("offline");
          setBackendDetails("Backend unavailable");
        }
      }
    }

    checkBackendHealth();

    return () => {
      cancelled = true;
    };
  }, []);

  const statusLabel = useMemo(() => {
    if (backendStatus === "online") {
      return `Online - ${backendDetails}`;
    }

    if (backendStatus === "offline") {
      return backendDetails;
    }

    return "Checking backend";
  }, [backendDetails, backendStatus]);

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <h1 className="brand-title">RouteForge AI</h1>
          <p className="brand-subtitle">Local route operations</p>
        </div>

        <nav className="nav-list">
          {navigationItems.map((item) => (
            <button
              className={`nav-item ${item === activeView ? "active" : ""}`}
              key={item}
              onClick={() => setActiveView(item)}
              type="button"
            >
              {item}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <h2 className="view-title">{activeView}</h2>
          <div className={`status-pill ${backendStatus}`} role="status">
            <span className="status-dot" aria-hidden="true" />
            <span>{statusLabel}</span>
          </div>
        </header>

        <section className="content" aria-labelledby="current-view-title">
          {activeView === "Import" ? (
            <ScreenshotImportScreen />
          ) : activeView === "Routes" ? (
            <RouteWorkspace />
          ) : activeView === "Route History" ? (
            <RouteHistoryScreen />
          ) : activeView === "Dispatch" ? (
            <DispatchScreen />
          ) : activeView === "Stops" ? (
            <StopsScreen />
          ) : activeView === "Vehicles" ? (
            <VehiclesScreen />
          ) : activeView === "Settings" ? (
            <SettingsScreen />
          ) : (
            <div className="placeholder-panel">
              <h2 id="current-view-title">{activeView}</h2>
              <p>
                This section is part of the application shell. Full page
                workflows will be added when the corresponding feature is
                requested.
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function ScreenshotImportScreen() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [preview, setPreview] = useState<ScreenshotPreview | null>(null);
  const [screenshotFile, setScreenshotFile] = useState<File | null>(null);
  const [reviewRows, setReviewRows] = useState<ScreenshotReviewRow[]>([]);
  const [depots, setDepots] = useState<Depot[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [startingDepotId, setStartingDepotId] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [createdStops, setCreatedStops] = useState<Stop[]>([]);
  const [optimizationResult, setOptimizationResult] =
    useState<RouteOptimizationResult | null>(null);
  const [zoomRequest, setZoomRequest] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isGeocoding, setIsGeocoding] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedDepot =
    depots.find((depot) => depot.id === Number(startingDepotId)) ?? null;
  const optimizedStopMarkers = optimizationResult?.optimized_stop_order
    .map((stopId, index) => {
      const stop = createdStops.find((candidate) => candidate.id === stopId);
      return stop === undefined ? null : { stop, order: index + 1 };
    })
    .filter((marker): marker is MapStopMarker => marker !== null) ?? [];
  const canOptimizeFromStartingLocation =
    startingDepotId !== "" &&
    vehicleId !== "" &&
    reviewRows.length > 0 &&
    reviewRows.every(
      (row) =>
        row.validation_status === "confirmed" &&
        row.latitude !== null &&
        row.longitude !== null &&
        row.stop_type !== "unknown"
    );

  useEffect(() => {
    return () => {
      if (preview !== null) {
        URL.revokeObjectURL(preview.url);
      }
    };
  }, [preview]);

  useEffect(() => {
    async function loadStartingLocationInputs() {
      try {
        const [depotsResponse, vehiclesResponse] = await Promise.all([
          requestJson<Depot[]>("/api/depots"),
          requestJson<Vehicle[]>("/api/vehicles")
        ]);
        setDepots(depotsResponse.data);
        setVehicles(vehiclesResponse.data);
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to load starting locations."
        );
      }
    }

    loadStartingLocationInputs();
  }, []);

  function selectFile(file: File | null) {
    setMessage("");
    setError("");

    if (file === null) {
      return;
    }

    if (!isAcceptedScreenshot(file)) {
      setError("Use a PNG, JPG, JPEG, or WebP image.");
      return;
    }

    if (file.size > maxScreenshotBytes) {
      setError("Use an image smaller than 8 MB.");
      return;
    }

    const nextPreview = {
      url: URL.createObjectURL(file),
      name: file.name || "Clipboard image",
      type: file.type || "image",
      size: file.size
    };
    setScreenshotFile(file);
    setPreview(nextPreview);
    setReviewRows([]);
    setCreatedStops([]);
    setOptimizationResult(null);
    setMessage("Screenshot ready for review.");
  }

  function handleFileInput(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0] ?? null);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files[0] ?? null);
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setIsDragging(false);
    }
  }

  function handlePaste(event: ClipboardEvent<HTMLDivElement>) {
    const imageItem = Array.from(event.clipboardData.items).find((item) =>
      item.type.startsWith("image/")
    );

    if (imageItem === undefined) {
      setError("Clipboard does not contain a supported image.");
      setMessage("");
      return;
    }

    event.preventDefault();
    selectFile(imageItem.getAsFile());
  }

  function addReviewRow() {
    setReviewRows((current) => [...current, createEmptyReviewRow()]);
    setOptimizationResult(null);
    setMessage("");
    setError("");
  }

  function updateReviewRow(
    rowId: string,
    field: keyof ScreenshotReviewRow,
    value: string
  ) {
    setReviewRows((current) =>
      current.map((row) => (row.id === rowId ? { ...row, [field]: value } : row))
    );
    setOptimizationResult(null);
  }

  function removeReviewRow(rowId: string) {
    setReviewRows((current) => current.filter((row) => row.id !== rowId));
    setOptimizationResult(null);
  }

  async function extractScreenshot() {
    if (screenshotFile === null) {
      setError("Choose a screenshot before extracting stops.");
      return;
    }

    setIsExtracting(true);
    setError("");
    setMessage("");

    try {
      const response = await requestJson<VisionExtractionResult>("/api/vision/extract", {
        method: "POST",
        body: JSON.stringify({
          image_base64: await fileToBase64(screenshotFile),
          content_type: screenshotFile.type || null
        })
      });
      setReviewRows(response.data.stops.map(extractedStopToReviewRow));
      setCreatedStops([]);
      setOptimizationResult(null);
      setMessage(
        response.data.stops.length === 0
          ? "No stops were extracted. Add rows manually for review."
          : `${response.data.stops.length.toLocaleString()} stops extracted for review.`
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to extract stops."
      );
    } finally {
      setIsExtracting(false);
    }
  }

  async function confirmReviewRows() {
    setError("");
    setMessage("");

    const rowsWithAddresses = reviewRows.filter(
      (row) => row.address.trim() !== ""
    );
    if (rowsWithAddresses.length !== reviewRows.length) {
      setError("Every reviewed stop needs an address before geocoding.");
      return;
    }

    setIsGeocoding(true);
    try {
      const response = await requestJson<GeocodeReviewResult[]>(
        "/api/geocoding/review-stops",
        {
          method: "POST",
          body: JSON.stringify({
            stops: reviewRows.map((row) => ({
              row_id: row.id,
              customer: row.customer.trim() || null,
              address: row.address,
              stop_type: row.stop_type,
              weight_lbs:
                row.weight_lbs.trim() === "" ? null : Number(row.weight_lbs),
              time_window: row.time_window.trim() || null,
              confidence:
                row.confidence.trim() === "" ? null : Number(row.confidence)
            }))
          })
        }
      );
      const resultByRowId = new Map(
        response.data.map((result) => [result.row_id, result])
      );
      setReviewRows((current) =>
        current.map((row) => {
          const result = resultByRowId.get(row.id);
          if (result === undefined) {
            return row;
          }

          return {
            ...row,
            normalized_address: result.normalized_address ?? "",
            latitude: result.latitude,
            longitude: result.longitude,
            geocode_status: result.geocode_status,
            geocode_message: result.message ?? "",
            confidence: result.confidence.toFixed(2),
            validation_status: result.validation_status
          };
        })
      );

      const unresolvedCount = response.data.filter(
        (result) => result.validation_status !== "confirmed"
      ).length;
      setMessage(
        unresolvedCount === 0
          ? `${response.data.length.toLocaleString()} stops geocoded and confirmed.`
          : `${unresolvedCount.toLocaleString()} addresses need review before optimization.`
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to geocode stops.");
    } finally {
      setIsGeocoding(false);
    }
  }

  async function optimizeFromStartingLocation() {
    setError("");
    setMessage("");

    if (!canOptimizeFromStartingLocation) {
      setError(
        "Resolve every address and choose a known stop type, starting depot, and vehicle before optimizing."
      );
      return;
    }

    setIsOptimizing(true);
    try {
      const stopResponses = await Promise.all(
        reviewRows.map((row) =>
          requestJson<Stop>("/api/stops", {
            method: "POST",
            body: JSON.stringify(reviewRowToStopPayload(row))
          })
        )
      );
      const stopsForRoute = stopResponses.map((response) => response.data);
      const routeResponse = await requestJson<Route>("/api/routes", {
        method: "POST",
        body: JSON.stringify({
          name: `Imported Route ${new Date().toLocaleString()}`,
          depot_id: Number(startingDepotId),
          vehicle_id: Number(vehicleId),
          stop_ids: stopsForRoute.map((stop) => stop.id),
          active: true
        })
      });
      const optimizationResponse = await requestJson<RouteOptimizationResult>(
        `/api/routes/${routeResponse.data.id}/optimize`,
        { method: "POST" }
      );

      setCreatedStops(stopsForRoute);
      setOptimizationResult(optimizationResponse.data);
      setMessage(`Route optimized. Version ${optimizationResponse.data.version_number} saved.`);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to optimize from starting location."
      );
    } finally {
      setIsOptimizing(false);
    }
  }

  return (
    <div className="import-screen">
      <div className="screen-heading">
        <div>
          <h2 id="current-view-title">Import From Screenshot</h2>
          <p>Bring in a route screenshot for later processing.</p>
        </div>
      </div>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="notice error">{error}</p>}

      <div className="import-layout">
        <div
          className={`screenshot-dropzone ${isDragging ? "dragging" : ""}`}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onPaste={handlePaste}
          tabIndex={0}
        >
          <input
            accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
            className="visually-hidden"
            onChange={handleFileInput}
            ref={fileInputRef}
            type="file"
          />
          <div className="dropzone-content">
            <strong>Drop screenshot here</strong>
            <span>PNG, JPG, JPEG, or WebP</span>
            <button
              className="primary-button"
              onClick={() => fileInputRef.current?.click()}
              type="button"
            >
              Choose Image
            </button>
            <button
              className="text-button"
              disabled={screenshotFile === null || isExtracting}
              onClick={extractScreenshot}
              type="button"
            >
              {isExtracting ? "Extracting" : "Extract Stops"}
            </button>
          </div>
        </div>

        <div className="screenshot-preview-panel">
          <div className="table-toolbar">
            <h3>Preview</h3>
            {preview !== null && (
              <button
                className="text-button danger"
                onClick={() => {
                  setPreview(null);
                  setScreenshotFile(null);
                  setReviewRows([]);
                  setCreatedStops([]);
                  setOptimizationResult(null);
                  setMessage("");
                  setError("");
                }}
                type="button"
              >
                Clear
              </button>
            )}
          </div>

          {preview === null ? (
            <p className="muted">No screenshot selected.</p>
          ) : (
            <div className="screenshot-preview">
              <img alt={preview.name} src={preview.url} />
              <dl>
                <div>
                  <dt>Name</dt>
                  <dd>{preview.name}</dd>
                </div>
                <div>
                  <dt>Type</dt>
                  <dd>{preview.type}</dd>
                </div>
                <div>
                  <dt>Size</dt>
                  <dd>{formatFileSize(preview.size)}</dd>
                </div>
              </dl>
            </div>
          )}
        </div>
      </div>

      <ScreenshotReviewTable
        onAddRow={addReviewRow}
        onConfirm={confirmReviewRows}
        onRemoveRow={removeReviewRow}
        onUpdateRow={updateReviewRow}
        isGeocoding={isGeocoding}
        rows={reviewRows}
      />

      <div className="table-panel import-optimization-panel">
        <div className="table-toolbar">
          <h3>Starting Location</h3>
          <button
            className="primary-button optimize-start-button"
            disabled={!canOptimizeFromStartingLocation || isOptimizing}
            onClick={optimizeFromStartingLocation}
            type="button"
          >
            {isOptimizing ? "OPTIMIZING" : "OPTIMIZE FROM STARTING LOCATION"}
          </button>
        </div>

        <div className="import-start-controls">
          <label>
            Starting depot
            <select
              onChange={(event) => setStartingDepotId(event.target.value)}
              value={startingDepotId}
            >
              <option value="">Select depot</option>
              {depots
                .filter((depot) => depot.active)
                .map((depot) => (
                  <option key={depot.id} value={depot.id}>
                    {depot.name}
                  </option>
                ))}
            </select>
          </label>

          <label>
            Vehicle
            <select
              onChange={(event) => setVehicleId(event.target.value)}
              value={vehicleId}
            >
              <option value="">Select vehicle</option>
              {vehicles
                .filter((vehicle) => vehicle.active)
                .map((vehicle) => (
                  <option key={vehicle.id} value={vehicle.id}>
                    {vehicle.name}
                  </option>
                ))}
            </select>
          </label>
        </div>

        {!canOptimizeFromStartingLocation && reviewRows.length > 0 && (
          <p className="muted">
            Confirm all addresses, resolve ambiguous or missing locations, choose
            known stop types, and select a depot and vehicle before optimizing.
          </p>
        )}
      </div>

      {optimizationResult !== null && (
        <>
          <RouteSummaryCards metrics={optimizationResult.metrics} />
          <div className="map-panel import-map-panel">
            <div className="map-panel-header">
              <h3>Map</h3>
              <div className="map-actions">
                <span>Route #{optimizationResult.route_id}</span>
                <button
                  className="text-button"
                  onClick={() => setZoomRequest((current) => current + 1)}
                  type="button"
                >
                  Zoom to Route
                </button>
              </div>
            </div>
            <RouteMap
              depot={selectedDepot}
              geometry={optimizationResult.geometry}
              stops={optimizedStopMarkers}
              zoomRequest={zoomRequest}
            />
          </div>
        </>
      )}
    </div>
  );
}

function ScreenshotReviewTable({
  rows,
  onAddRow,
  onUpdateRow,
  onRemoveRow,
  onConfirm,
  isGeocoding
}: {
  rows: ScreenshotReviewRow[];
  onAddRow: () => void;
  onUpdateRow: (
    rowId: string,
    field: keyof ScreenshotReviewRow,
    value: string
  ) => void;
  onRemoveRow: (rowId: string) => void;
  onConfirm: () => void;
  isGeocoding: boolean;
}) {
  return (
    <div className="table-panel screenshot-review-panel">
      <div className="table-toolbar">
        <h3>Review Stops</h3>
        <div className="row-actions">
          <button className="text-button" onClick={onAddRow} type="button">
            Add Row
          </button>
          <button
            className="primary-button"
            disabled={rows.length === 0 || isGeocoding}
            onClick={onConfirm}
            type="button"
          >
            {isGeocoding ? "Geocoding" : "Confirm"}
          </button>
        </div>
      </div>

      {rows.length === 0 ? (
        <p className="muted">No extracted stops to review.</p>
      ) : (
        <div className="data-table-wrap">
          <table className="data-table screenshot-review-table">
            <thead>
              <tr>
                <th>Customer</th>
                <th>Address</th>
                <th>Normalized Address</th>
                <th>Type</th>
                <th>Weight</th>
                <th>Time Window</th>
                <th>Confidence</th>
                <th>Validation Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <input
                      aria-label="Customer"
                      onChange={(event) =>
                        onUpdateRow(row.id, "customer", event.target.value)
                      }
                      type="text"
                      value={row.customer}
                    />
                  </td>
                  <td>
                    <input
                      aria-label="Address"
                      onChange={(event) =>
                        onUpdateRow(row.id, "address", event.target.value)
                      }
                      type="text"
                      value={row.address}
                    />
                  </td>
                  <td>
                    <span className="review-secondary-text">
                      {row.normalized_address || row.geocode_message || "Not checked"}
                    </span>
                  </td>
                  <td>
                    <select
                      aria-label="Type"
                      onChange={(event) =>
                        onUpdateRow(row.id, "stop_type", event.target.value)
                      }
                      value={row.stop_type}
                    >
                      <option value="unknown">Unknown</option>
                      <option value="pickup">Pickup</option>
                      <option value="delivery">Delivery</option>
                      <option value="pickup_delivery">Pickup + Delivery</option>
                    </select>
                  </td>
                  <td>
                    <input
                      aria-label="Weight"
                      min="0"
                      onChange={(event) =>
                        onUpdateRow(row.id, "weight_lbs", event.target.value)
                      }
                      step="0.1"
                      type="number"
                      value={row.weight_lbs}
                    />
                  </td>
                  <td>
                    <input
                      aria-label="Time window"
                      onChange={(event) =>
                        onUpdateRow(row.id, "time_window", event.target.value)
                      }
                      type="text"
                      value={row.time_window}
                    />
                  </td>
                  <td>
                    <input
                      aria-label="Confidence"
                      max="1"
                      min="0"
                      onChange={(event) =>
                        onUpdateRow(row.id, "confidence", event.target.value)
                      }
                      step="0.01"
                      type="number"
                      value={row.confidence}
                    />
                  </td>
                  <td>
                    <select
                      aria-label="Validation status"
                      onChange={(event) =>
                        onUpdateRow(
                          row.id,
                          "validation_status",
                          event.target.value
                        )
                      }
                      value={row.validation_status}
                    >
                      {reviewStatuses.map((statusValue) => (
                        <option key={statusValue} value={statusValue}>
                          {formatReviewStatus(statusValue)}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <button
                      className="text-button danger"
                      onClick={() => onRemoveRow(row.id)}
                      type="button"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function DispatchScreen() {
  const [depots, setDepots] = useState<Depot[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [stops, setStops] = useState<Stop[]>([]);
  const [depotId, setDepotId] = useState("");
  const [selectedVehicleIds, setSelectedVehicleIds] = useState<number[]>([]);
  const [selectedStopIds, setSelectedStopIds] = useState<number[]>([]);
  const [dispatchResult, setDispatchResult] =
    useState<DispatchOptimizeResult | null>(null);
  const [zoomRequest, setZoomRequest] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const activeVehicles = useMemo(
    () => vehicles.filter((vehicle) => vehicle.active),
    [vehicles]
  );
  const activeStops = useMemo(
    () => stops.filter((stop) => stop.active),
    [stops]
  );
  const stopById = useMemo(
    () => new Map(stops.map((stop) => [stop.id, stop])),
    [stops]
  );
  const selectedDepot = depots.find((depot) => depot.id === Number(depotId)) ?? null;

  async function loadDispatchInputs() {
    setIsLoading(true);
    setError("");

    try {
      const [depotsResponse, vehiclesResponse, stopsResponse] = await Promise.all([
        requestJson<Depot[]>("/api/depots"),
        requestJson<Vehicle[]>("/api/vehicles"),
        requestJson<Stop[]>("/api/stops")
      ]);
      setDepots(depotsResponse.data);
      setVehicles(vehiclesResponse.data);
      setStops(stopsResponse.data);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load dispatch inputs."
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadDispatchInputs();
  }, []);

  function toggleVehicle(vehicleId: number) {
    setSelectedVehicleIds((current) =>
      current.includes(vehicleId)
        ? current.filter((id) => id !== vehicleId)
        : [...current, vehicleId]
    );
    setDispatchResult(null);
  }

  function toggleStop(stopId: number) {
    setSelectedStopIds((current) =>
      current.includes(stopId)
        ? current.filter((id) => id !== stopId)
        : [...current, stopId]
    );
    setDispatchResult(null);
  }

  async function optimizeDispatch() {
    setIsOptimizing(true);
    setError("");
    setMessage("");

    try {
      const response = await requestJson<DispatchOptimizeResult>(
        "/api/dispatch/optimize",
        {
          method: "POST",
          body: JSON.stringify({
            depot_id: Number(depotId),
            vehicle_ids: selectedVehicleIds,
            stop_ids: selectedStopIds
          })
        }
      );
      setDispatchResult(response.data);
      setMessage(
        response.data.solver_status === "optimal"
          ? "Dispatch route set optimized."
          : `Dispatch optimizer returned ${response.data.solver_status}.`
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to optimize dispatch."
      );
    } finally {
      setIsOptimizing(false);
    }
  }

  const canOptimize =
    depotId !== "" && selectedVehicleIds.length > 0 && selectedStopIds.length > 0;

  return (
    <div className="dispatch-screen">
      <div className="screen-heading">
        <div>
          <h2 id="current-view-title">Dispatch</h2>
          <p>Assign a route set across multiple vehicles.</p>
        </div>
        <button
          className="primary-button"
          disabled={!canOptimize || isOptimizing}
          onClick={optimizeDispatch}
          type="button"
        >
          {isOptimizing ? "Optimizing" : "Optimize Dispatch"}
        </button>
      </div>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="notice error">{error}</p>}

      <div className="dispatch-grid">
        <section className="entity-form dispatch-controls">
          <div className="form-heading">
            <h3>Route Set</h3>
            <button className="text-button" onClick={loadDispatchInputs} type="button">
              Refresh
            </button>
          </div>

          <label>
            Dispatch depot
            <select
              disabled={isLoading}
              onChange={(event) => {
                setDepotId(event.target.value);
                setDispatchResult(null);
              }}
              value={depotId}
            >
              <option value="">Select depot</option>
              {depots
                .filter((depot) => depot.active)
                .map((depot) => (
                  <option key={depot.id} value={depot.id}>
                    {depot.name}
                  </option>
                ))}
            </select>
          </label>

          <div className="dispatch-choice-group">
            <h4>Vehicles</h4>
            {activeVehicles.map((vehicle) => (
              <label className="checkbox-field" key={vehicle.id}>
                <input
                  checked={selectedVehicleIds.includes(vehicle.id)}
                  onChange={() => toggleVehicle(vehicle.id)}
                  type="checkbox"
                />
                <span>
                  {vehicle.name} · {formatPounds(vehicle.max_payload_lbs)}
                </span>
              </label>
            ))}
          </div>

          <div className="dispatch-choice-group">
            <h4>Stops</h4>
            {activeStops.map((stop) => (
              <label className="checkbox-field" key={stop.id}>
                <input
                  checked={selectedStopIds.includes(stop.id)}
                  onChange={() => toggleStop(stop.id)}
                  type="checkbox"
                />
                <span>
                  {stop.name} · {formatPounds(stop.weight_lbs)}
                </span>
              </label>
            ))}
          </div>
        </section>

        <section className="dispatch-results-panel">
          <div className="table-toolbar">
            <h3>Vehicle Routes</h3>
            <button
              className="text-button"
              disabled={dispatchResult === null}
              onClick={() => setZoomRequest((current) => current + 1)}
              type="button"
            >
              Zoom to Dispatch
            </button>
          </div>

          {dispatchResult === null ? (
            <p className="muted">Optimize a route set to see vehicle assignments.</p>
          ) : dispatchResult.routes.length === 0 ? (
            <p className="notice error">
              Solver status: {dispatchResult.solver_status}
            </p>
          ) : (
            <div className="dispatch-route-list">
              {dispatchResult.routes.map((route, index) => (
                <article className="dispatch-route-card" key={route.vehicle_id}>
                  <div className="dispatch-route-heading">
                    <span
                      className="dispatch-color-key"
                      style={{ background: dispatchRouteColor(index) }}
                    />
                    <h4>{route.vehicle_name}</h4>
                  </div>
                  <dl>
                    <div>
                      <dt>Stops</dt>
                      <dd>{route.optimized_stop_order.length.toLocaleString()}</dd>
                    </div>
                    <div>
                      <dt>Miles</dt>
                      <dd>{formatMiles(route.total_distance_miles)}</dd>
                    </div>
                    <div>
                      <dt>Drive</dt>
                      <dd>{formatMinutes(route.total_travel_duration_minutes)}</dd>
                    </div>
                    <div>
                      <dt>Payload</dt>
                      <dd>{formatPounds(route.payload_lbs)}</dd>
                    </div>
                  </dl>
                  <ol>
                    {route.optimized_stop_order.map((stopId) => {
                      const stop = stopById.get(stopId);
                      return (
                        <li key={stopId}>
                          {stop?.name ?? `Stop ${stopId}`}
                        </li>
                      );
                    })}
                  </ol>
                </article>
              ))}
            </div>
          )}
        </section>

        <div className="map-panel dispatch-map-panel">
          <div className="map-panel-header">
            <h3>Dispatch Map</h3>
            <span>
              {dispatchResult?.routes.length.toLocaleString() ?? "0"} vehicle routes
            </span>
          </div>
          <DispatchMap
            depot={selectedDepot}
            routes={dispatchResult?.routes ?? []}
            stopById={stopById}
            zoomRequest={zoomRequest}
          />
        </div>
      </div>
    </div>
  );
}

function RouteWorkspace() {
  const [depots, setDepots] = useState<Depot[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [stops, setStops] = useState<Stop[]>([]);
  const [form, setForm] = useState<RouteFormState>(emptyRouteForm);
  const [orderedStopIds, setOrderedStopIds] = useState<number[]>([]);
  const [createdRoute, setCreatedRoute] = useState<Route | null>(null);
  const [optimizationResult, setOptimizationResult] =
    useState<RouteOptimizationResult | null>(null);
  const [zoomRequest, setZoomRequest] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [aiCommand, setAiCommand] = useState("");
  const [isAskingAi, setIsAskingAi] = useState(false);
  const [isApplyingAi, setIsApplyingAi] = useState(false);
  const [aiProposal, setAiProposal] = useState<AIInstructionParseResult | null>(
    null
  );
  const [aiExplanation, setAiExplanation] =
    useState<AIRouteExplanationResponse | null>(null);
  const [aiMessage, setAiMessage] = useState("");
  const [aiError, setAiError] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const activeStops = useMemo(
    () => stops.filter((stop) => stop.active),
    [stops]
  );
  const stopById = useMemo(
    () => new Map(stops.map((stop) => [stop.id, stop])),
    [stops]
  );
  const assignedStopIds = new Set(orderedStopIds);
  const selectableStops = activeStops.filter((stop) => !assignedStopIds.has(stop.id));
  const selectedStops = orderedStopIds
    .map((stopId) => stopById.get(stopId))
    .filter((stop): stop is Stop => stop !== undefined);
  const selectedDepot = depots.find((depot) => depot.id === Number(form.depot_id));
  const optimizedStopMarkers = optimizationResult?.optimized_stop_order
    .map((stopId, index) => {
      const stop = stopById.get(stopId);
      return stop === undefined ? null : { stop, order: index + 1 };
    })
    .filter((marker): marker is MapStopMarker => marker !== null) ?? selectedStops.map(
    (stop, index) => ({ stop, order: index + 1 })
  );

  async function loadRouteInputs() {
    setIsLoading(true);
    setError("");

    try {
      const [depotsResponse, vehiclesResponse, stopsResponse] = await Promise.all([
        requestJson<Depot[]>("/api/depots"),
        requestJson<Vehicle[]>("/api/vehicles"),
        requestJson<Stop[]>("/api/stops")
      ]);
      setDepots(depotsResponse.data);
      setVehicles(vehiclesResponse.data);
      setStops(stopsResponse.data);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to load route inputs."
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadRouteInputs();
  }, []);

  function resetSavedRouteDraft() {
    setCreatedRoute(null);
    setOptimizationResult(null);
  }

  function addSelectedStop() {
    if (form.selected_stop_id === "") {
      return;
    }

    const stopId = Number(form.selected_stop_id);
    if (orderedStopIds.includes(stopId)) {
      return;
    }

    setOrderedStopIds((current) => [...current, stopId]);
    setForm((current) => ({ ...current, selected_stop_id: "" }));
    resetSavedRouteDraft();
  }

  function removeStop(stopId: number) {
    setOrderedStopIds((current) => current.filter((id) => id !== stopId));
    resetSavedRouteDraft();
  }

  function moveStop(stopId: number, direction: -1 | 1) {
    setOrderedStopIds((current) => {
      const index = current.indexOf(stopId);
      const nextIndex = index + direction;
      if (index < 0 || nextIndex < 0 || nextIndex >= current.length) {
        return current;
      }

      const next = [...current];
      [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
      return next;
    });
    resetSavedRouteDraft();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    setMessage("");

    try {
      const payload = {
        name: form.name.trim(),
        depot_id: form.depot_id === "" ? null : Number(form.depot_id),
        vehicle_id: form.vehicle_id === "" ? null : Number(form.vehicle_id),
        stop_ids: orderedStopIds,
        active: true
      };

      const response = await requestJson<Route>("/api/routes", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      setCreatedRoute(response.data);
      setOptimizationResult(null);
      setMessage("Route saved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save route.");
    } finally {
      setIsSaving(false);
    }
  }

  async function optimizeRoute() {
    if (createdRoute === null) {
      return;
    }

    setIsOptimizing(true);
    setError("");
    setMessage("");

    try {
      const response = await requestJson<RouteOptimizationResult>(
        `/api/routes/${createdRoute.id}/optimize`,
        { method: "POST" }
      );
      setOptimizationResult(response.data);
      setMessage(`Route optimized. Version ${response.data.version_number} saved.`);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to optimize route."
      );
    } finally {
      setIsOptimizing(false);
    }
  }

  async function askDispatchAi(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (aiCommand.trim() === "") {
      return;
    }

    setIsAskingAi(true);
    setAiError("");
    setAiMessage("");
    setAiProposal(null);
    setAiExplanation(null);

    try {
      if (isAiExplanationQuestion(aiCommand)) {
        if (createdRoute === null) {
          throw new Error("Save a route before asking route explanation questions.");
        }

        const versionPair = extractVersionPair(aiCommand);
        const response = await requestJson<AIRouteExplanationResponse>(
          "/api/ai/route-explanations",
          {
            method: "POST",
            body: JSON.stringify({
              question: aiCommand.trim(),
              route_id: createdRoute.id,
              route_version: optimizationResult?.version_number ?? null,
              base_version: versionPair?.base ?? null,
              comparison_version: versionPair?.comparison ?? null,
              shipment_weight_lbs: extractShipmentWeight(aiCommand)
            })
          }
        );
        setAiExplanation(response.data);
        setAiMessage("Explanation generated from RouteForge metrics.");
      } else {
        const response = await requestJson<AIInstructionParseResult>(
          "/api/ai/instructions/parse",
          {
            method: "POST",
            body: JSON.stringify({
              command: aiCommand.trim(),
              context: {
                route_id: createdRoute?.id ?? null,
                route_name: form.name,
                depot_id: form.depot_id === "" ? null : Number(form.depot_id),
                vehicle_id:
                  form.vehicle_id === "" ? null : Number(form.vehicle_id),
                selected_stop_ids: orderedStopIds,
                selected_stops: selectedStops.map((stop, index) => ({
                  id: stop.id,
                  order: index + 1,
                  name: stop.name,
                  earliest_time: stop.earliest_time,
                  latest_time: stop.latest_time,
                  priority: stop.priority,
                  service_minutes: stop.service_minutes
                }))
              }
            })
          }
        );
        setAiProposal(response.data);
        setAiMessage("Review proposed changes before applying.");
      }
    } catch (caught) {
      setAiError(
        caught instanceof Error
          ? caught.message
          : "Unable to ask Dispatch AI."
      );
    } finally {
      setIsAskingAi(false);
    }
  }

  function cancelAiProposal() {
    setAiProposal(null);
    setAiMessage("Proposed changes canceled.");
    setAiError("");
  }

  async function applyAiProposal() {
    if (aiProposal === null || !canApplyAiProposal(aiProposal)) {
      return;
    }

    setIsApplyingAi(true);
    setAiError("");
    setAiMessage("");

    try {
      for (const action of aiProposal.proposed_actions) {
        await applyAiAction(action);
      }
      await loadRouteInputs();
      setOptimizationResult(null);
      setAiProposal(null);
      setAiCommand("");
      setAiMessage("Proposed changes applied.");
    } catch (caught) {
      setAiError(
        caught instanceof Error
          ? caught.message
          : "Unable to apply proposed changes."
      );
    } finally {
      setIsApplyingAi(false);
    }
  }

  async function applyAiAction(action: AIInstructionAction) {
    if (action.action_type === "assign_vehicle") {
      const vehicleId = Number(action.fields.vehicle_id);
      if (createdRoute !== null) {
        const response = await requestJson<Route>(
          `/api/routes/${createdRoute.id}`,
          {
            method: "PUT",
            body: JSON.stringify({ vehicle_id: vehicleId })
          }
        );
        setCreatedRoute(response.data);
      }
      setForm((current) => ({ ...current, vehicle_id: String(vehicleId) }));
      return;
    }

    if (action.action_type === "assign_depot") {
      const depotId = Number(action.fields.depot_id);
      if (createdRoute !== null) {
        const response = await requestJson<Route>(
          `/api/routes/${createdRoute.id}`,
          {
            method: "PUT",
            body: JSON.stringify({ depot_id: depotId })
          }
        );
        setCreatedRoute(response.data);
      }
      setForm((current) => ({ ...current, depot_id: String(depotId) }));
      return;
    }

    if (action.target === "stop" && action.entity_id !== null) {
      await requestJson<Stop>(`/api/stops/${action.entity_id}`, {
        method: "PUT",
        body: JSON.stringify(stopActionPayload(action))
      });
      return;
    }

    throw new Error("This proposed change cannot be applied yet.");
  }

  function stopActionPayload(action: AIInstructionAction) {
    if (action.action_type === "set_stop_latest_arrival") {
      return { latest_time: action.fields.latest_time };
    }

    if (action.action_type === "set_stop_earliest_arrival") {
      return { earliest_time: action.fields.earliest_time };
    }

    if (action.action_type === "set_stop_priority") {
      return { priority: action.fields.priority };
    }

    if (action.action_type === "set_stop_service_minutes") {
      return { service_minutes: action.fields.service_minutes };
    }

    throw new Error("This stop change cannot be applied yet.");
  }

  function canApplyAiProposal(proposal: AIInstructionParseResult) {
    return proposal.proposed_actions.every(isAiActionApplicable);
  }

  function isAiActionApplicable(action: AIInstructionAction) {
    return [
      "set_stop_latest_arrival",
      "set_stop_earliest_arrival",
      "set_stop_priority",
      "set_stop_service_minutes",
      "assign_vehicle",
      "assign_depot"
    ].includes(action.action_type);
  }

  return (
    <div className="route-workspace">
      <div className="screen-heading">
        <div>
          <h2 id="current-view-title">Routes</h2>
          <p>Build a route plan from depots, vehicles, and selected stops.</p>
        </div>
        <button
          className="primary-button"
          disabled={createdRoute === null || isOptimizing}
          onClick={optimizeRoute}
          type="button"
        >
          {isOptimizing ? "Optimizing" : "Optimize Route"}
        </button>
      </div>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="notice error">{error}</p>}

      {optimizationResult !== null && (
        <RouteSummaryCards metrics={optimizationResult.metrics} />
      )}

      <div className="route-grid">
        <form className="entity-form route-form" onSubmit={handleSubmit}>
          <div className="form-heading">
            <h3>Route Setup</h3>
            <button className="text-button" onClick={loadRouteInputs} type="button">
              Refresh
            </button>
          </div>

          <label>
            Route name
            <input
              maxLength={120}
              onChange={(event) => {
                setForm((current) => ({ ...current, name: event.target.value }));
                resetSavedRouteDraft();
              }}
              required
              type="text"
              value={form.name}
            />
          </label>

          <label>
            Starting depot
            <select
              onChange={(event) => {
                setForm((current) => ({ ...current, depot_id: event.target.value }));
                resetSavedRouteDraft();
              }}
              value={form.depot_id}
            >
              <option value="">No depot selected</option>
              {depots
                .filter((depot) => depot.active)
                .map((depot) => (
                  <option key={depot.id} value={depot.id}>
                    {depot.name}
                  </option>
                ))}
            </select>
          </label>

          <label>
            Vehicle
            <select
              onChange={(event) => {
                setForm((current) => ({ ...current, vehicle_id: event.target.value }));
                resetSavedRouteDraft();
              }}
              value={form.vehicle_id}
            >
              <option value="">No vehicle selected</option>
              {vehicles
                .filter((vehicle) => vehicle.active)
                .map((vehicle) => (
                  <option key={vehicle.id} value={vehicle.id}>
                    {vehicle.name}
                  </option>
                ))}
            </select>
          </label>

          <label>
            Stop selection
            <select
              disabled={isLoading || selectableStops.length === 0}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  selected_stop_id: event.target.value
                }))
              }
              value={form.selected_stop_id}
            >
              <option value="">Select a stop</option>
              {selectableStops.map((stop) => (
                <option key={stop.id} value={stop.id}>
                  {stop.name}
                </option>
              ))}
            </select>
          </label>

          <button className="text-button" onClick={addSelectedStop} type="button">
            Add Stop
          </button>

          <button
            className="primary-button"
            disabled={isSaving || form.name.trim() === ""}
            type="submit"
          >
            {isSaving ? "Saving" : "Save Route"}
          </button>
        </form>

        <div className="table-panel route-stops-panel">
          <div className="table-toolbar">
            <h3>Ordered Stops</h3>
            <span className="muted">{selectedStops.length} selected</span>
          </div>

          {selectedStops.length === 0 ? (
            <p className="muted">No stops assigned.</p>
          ) : (
            <div className="data-table-wrap">
              <table className="data-table route-stops-table">
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Address</th>
                    <th>Weight</th>
                    <th>Service</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedStops.map((stop, index) => (
                    <tr key={stop.id}>
                      <td>{index + 1}</td>
                      <td>{stop.name}</td>
                      <td>{formatStopType(stop.stop_type)}</td>
                      <td>{stop.address}</td>
                      <td>{stop.weight_lbs.toLocaleString()} lb</td>
                      <td>{stop.service_minutes.toLocaleString()} min</td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="text-button"
                            disabled={index === 0}
                            onClick={() => moveStop(stop.id, -1)}
                            type="button"
                          >
                            Up
                          </button>
                          <button
                            className="text-button"
                            disabled={index === selectedStops.length - 1}
                            onClick={() => moveStop(stop.id, 1)}
                            type="button"
                          >
                            Down
                          </button>
                          <button
                            className="text-button danger"
                            onClick={() => removeStop(stop.id)}
                            type="button"
                          >
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="map-panel">
          <div className="map-panel-header">
            <h3>Map</h3>
            <div className="map-actions">
              {createdRoute && <span>Route #{createdRoute.id}</span>}
              <button
                className="text-button"
                onClick={() => setZoomRequest((current) => current + 1)}
                type="button"
              >
                Zoom to Route
              </button>
            </div>
          </div>
          <RouteMap
            depot={selectedDepot ?? null}
            geometry={optimizationResult?.geometry ?? null}
            stops={optimizedStopMarkers}
            zoomRequest={zoomRequest}
          />
        </div>

        <section className="ai-dispatch-panel" aria-label="Ask Dispatch AI">
          <div className="form-heading">
            <h3>ASK DISPATCH AI</h3>
          </div>

          <form className="ai-dispatch-form" onSubmit={askDispatchAi}>
            <label>
              Dispatch instruction
              <textarea
                onChange={(event) => setAiCommand(event.target.value)}
                placeholder="Make Stop 6 arrive before 11 and return by 4."
                rows={3}
                value={aiCommand}
              />
            </label>
            <button
              className="primary-button"
              disabled={isAskingAi || aiCommand.trim() === ""}
              type="submit"
            >
              {isAskingAi ? "Asking" : "Ask AI"}
            </button>
          </form>

          {aiMessage && <p className="notice success">{aiMessage}</p>}
          {aiError && <p className="notice error">{aiError}</p>}

          {aiProposal !== null && (
            <div className="proposed-changes-panel">
              <div className="table-toolbar">
                <h3>PROPOSED CHANGES</h3>
                <span className="muted">
                  {aiProposal.proposed_actions.length.toLocaleString()} proposed
                </span>
              </div>
              <p className="muted">{aiProposal.summary}</p>
              <div className="proposed-change-list">
                {aiProposal.proposed_actions.map((action, index) => (
                  <div className="proposed-change-item" key={`${action.action_type}-${index}`}>
                    <strong>{formatAiAction(action)}</strong>
                    <span>{formatAiFields(action.fields)}</span>
                    {action.rationale && <span>{action.rationale}</span>}
                    {!isAiActionApplicable(action) && (
                      <span className="ai-unsupported">
                        This change cannot be applied until the route model supports it.
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <div className="row-actions">
                <button
                  className="primary-button"
                  disabled={
                    isApplyingAi ||
                    !canApplyAiProposal(aiProposal) ||
                    !aiProposal.requires_user_confirmation
                  }
                  onClick={applyAiProposal}
                  type="button"
                >
                  {isApplyingAi ? "APPLYING" : "APPLY"}
                </button>
                <button
                  className="text-button"
                  disabled={isApplyingAi}
                  onClick={cancelAiProposal}
                  type="button"
                >
                  CANCEL
                </button>
              </div>
            </div>
          )}

          {aiExplanation !== null && (
            <div className="ai-explanation-panel">
              <div className="table-toolbar">
                <h3>AI EXPLANATION</h3>
                <span className="muted">{formatExplanationIntent(aiExplanation.intent)}</span>
              </div>
              <p>{aiExplanation.explanation.summary}</p>
              {aiExplanation.explanation.observations.length > 0 && (
                <ul className="ai-explanation-list">
                  {aiExplanation.explanation.observations.map((observation) => (
                    <li key={observation}>{observation}</li>
                  ))}
                </ul>
              )}
              {aiExplanation.explanation.caveats.length > 0 && (
                <div className="ai-fact-note">
                  {aiExplanation.explanation.caveats.map((caveat) => (
                    <span key={caveat}>{caveat}</span>
                  ))}
                </div>
              )}
              <div className="ai-fact-note">
                <strong>Application facts used</strong>
                <span>{Object.keys(aiExplanation.application_facts).join(", ")}</span>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function RouteHistoryScreen() {
  const [routes, setRoutes] = useState<Route[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState("");
  const [versions, setVersions] = useState<RouteVersion[]>([]);
  const [isLoadingRoutes, setIsLoadingRoutes] = useState(true);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadRoutes() {
    setIsLoadingRoutes(true);
    setError("");
    setMessage("");

    try {
      const response = await requestJson<Route[]>("/api/routes");
      setRoutes(response.data);
      setSelectedRouteId((current) => {
        if (current !== "" && response.data.some((route) => route.id === Number(current))) {
          return current;
        }

        return response.data[0] === undefined ? "" : String(response.data[0].id);
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load routes.");
    } finally {
      setIsLoadingRoutes(false);
    }
  }

  async function loadRouteVersions(routeId: string) {
    if (routeId === "") {
      setVersions([]);
      return;
    }

    setIsLoadingVersions(true);
    setError("");

    try {
      const response = await requestJson<RouteVersion[]>(
        `/api/routes/${routeId}/versions`
      );
      setVersions(response.data);
      setMessage(
        response.data.length === 0
          ? "No optimization versions have been saved for this route."
          : `${response.data.length.toLocaleString()} route versions loaded.`
      );
    } catch (caught) {
      setVersions([]);
      setError(
        caught instanceof Error ? caught.message : "Unable to load route versions."
      );
    } finally {
      setIsLoadingVersions(false);
    }
  }

  useEffect(() => {
    loadRoutes();
  }, []);

  useEffect(() => {
    loadRouteVersions(selectedRouteId);
  }, [selectedRouteId]);

  const selectedRoute =
    routes.find((route) => route.id === Number(selectedRouteId)) ?? null;

  return (
    <div className="route-history-screen">
      <div className="screen-heading">
        <div>
          <h2 id="current-view-title">Route History</h2>
          <p>Review saved optimization versions without changing route data.</p>
        </div>
        <button className="primary-button" onClick={loadRoutes} type="button">
          {isLoadingRoutes ? "Loading" : "Refresh"}
        </button>
      </div>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="notice error">{error}</p>}

      <div className="workspace-grid">
        <div className="table-panel">
          <div className="table-toolbar">
            <h3>Routes</h3>
            <span className="muted">{routes.length.toLocaleString()} total</span>
          </div>

          {routes.length === 0 ? (
            <p className="muted">No routes saved.</p>
          ) : (
            <div className="data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Stops</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {routes.map((route) => (
                    <tr key={route.id}>
                      <td>{route.name}</td>
                      <td>{route.stops.length.toLocaleString()}</td>
                      <td>
                        <span
                          className={`entity-status ${
                            route.active ? "active" : "inactive"
                          }`}
                        >
                          {route.active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td>
                        <button
                          className="text-button"
                          onClick={() => setSelectedRouteId(String(route.id))}
                          type="button"
                        >
                          View History
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="table-panel">
          <div className="table-toolbar">
            <h3>{selectedRoute === null ? "Versions" : selectedRoute.name}</h3>
            <span className="muted">
              {isLoadingVersions
                ? "Loading"
                : `${versions.length.toLocaleString()} versions`}
            </span>
          </div>

          {selectedRouteId === "" ? (
            <p className="muted">Select a route to view saved versions.</p>
          ) : versions.length === 0 ? (
            <p className="muted">No optimization versions saved.</p>
          ) : (
            <div className="data-table-wrap">
              <table className="data-table route-history-table">
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Status</th>
                    <th>Miles</th>
                    <th>Drive</th>
                    <th>Service</th>
                    <th>Route Time</th>
                    <th>Saved</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((version) => (
                    <tr key={version.id}>
                      <td>{version.version_number}</td>
                      <td>{formatSolverStatus(version.solver_status)}</td>
                      <td>{formatNullableMiles(version.total_distance_miles)}</td>
                      <td>
                        {formatNullableMinutes(
                          version.total_travel_duration_minutes
                        )}
                      </td>
                      <td>
                        {formatNullableMinutes(
                          version.total_service_duration_minutes
                        )}
                      </td>
                      <td>
                        {formatNullableMinutes(
                          version.total_route_duration_minutes
                        )}
                      </td>
                      <td>{formatDateTime(version.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RouteSummaryCards({
  metrics
}: {
  metrics: RouteOptimizationResult["metrics"];
}) {
  const cards = [
    {
      label: "Total Miles",
      value: formatMiles(metrics.total_distance_miles)
    },
    {
      label: "Drive Time",
      value: formatMinutes(metrics.total_travel_duration_minutes)
    },
    {
      label: "Service Time",
      value: formatMinutes(metrics.total_service_duration_minutes)
    },
    {
      label: "Route Duration",
      value: formatMinutes(metrics.total_route_duration_minutes)
    },
    {
      label: "Stops",
      value: metrics.number_of_stops.toLocaleString()
    },
    {
      label: "Payload",
      value: formatPounds(metrics.payload_lbs)
    },
    {
      label: "Remaining Capacity",
      value: formatPounds(metrics.remaining_capacity_lbs)
    }
  ];

  return (
    <div className="route-summary-grid" aria-label="Route summary">
      {cards.map((card) => (
        <div className="summary-card" key={card.label}>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
        </div>
      ))}
    </div>
  );
}

function RouteMap({
  depot,
  geometry,
  stops,
  zoomRequest
}: {
  depot: Depot | null;
  geometry: RouteGeometry | null;
  stops: MapStopMarker[];
  zoomRequest: number;
}) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const routeCoordinates = useMemo(
    () => routeLineCoordinatesFromGeometry(geometry),
    [geometry]
  );

  useEffect(() => {
    if (mapContainerRef.current === null || mapRef.current !== null) {
      return;
    }

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      center: [-82.4572, 27.9506],
      zoom: 11,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "OpenStreetMap contributors"
          }
        },
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm"
          }
        ]
      }
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => {
      map.addSource("optimized-route", emptyRouteSource());
      map.addLayer({
        id: "optimized-route-line",
        type: "line",
        source: "optimized-route",
        paint: {
          "line-color": "#1f7a8c",
          "line-width": 5,
          "line-opacity": 0.88
        },
        layout: {
          "line-cap": "round",
          "line-join": "round"
        }
      });
    });
    mapRef.current = map;

    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (map === null) {
      return;
    }

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    if (depot !== null) {
      markersRef.current.push(
        new maplibregl.Marker({ element: depotMarkerElement() })
          .setLngLat([depot.longitude, depot.latitude])
          .setPopup(popupForDepot(depot))
          .addTo(map)
      );
    }

    stops.forEach(({ stop, order }) => {
      markersRef.current.push(
        new maplibregl.Marker({ element: stopMarkerElement(order) })
          .setLngLat([stop.longitude, stop.latitude])
          .setPopup(popupForStop(stop, order))
          .addTo(map)
      );
    });
  }, [depot, stops]);

  useEffect(() => {
    const map = mapRef.current;
    if (map === null) {
      return;
    }
    const activeMap = map;

    function updateRouteLine() {
      const source = activeMap.getSource("optimized-route") as
        | GeoJSONSource
        | undefined;
      if (source === undefined) {
        return;
      }

      source.setData(routeLineData(routeCoordinates));
    }

    if (activeMap.isStyleLoaded()) {
      updateRouteLine();
      return;
    }

    activeMap.once("load", updateRouteLine);
  }, [routeCoordinates]);

  useEffect(() => {
    const map = mapRef.current;
    if (map === null || zoomRequest === 0) {
      return;
    }

    zoomToCoordinates(map, coordinatesForBounds(depot, stops, routeCoordinates));
  }, [depot, routeCoordinates, stops, zoomRequest]);

  return (
    <div className="map-wrap">
      <div className="route-map" ref={mapContainerRef} />
      {routeCoordinates.length === 0 && (
        <div className="map-empty-state">
          Save and optimize a route to draw its backend route geometry.
        </div>
      )}
    </div>
  );
}

function DispatchMap({
  depot,
  routes,
  stopById,
  zoomRequest
}: {
  depot: Depot | null;
  routes: DispatchVehicleRoute[];
  stopById: Map<number, Stop>;
  zoomRequest: number;
}) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const routeLines = useMemo(
    () =>
      routes.map((route, index) => ({
        color: dispatchRouteColor(index),
        coordinates: routeLineCoordinatesFromGeometry(route.geometry)
      })),
    [routes]
  );

  useEffect(() => {
    if (mapContainerRef.current === null || mapRef.current !== null) {
      return;
    }

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      center: [-82.4572, 27.9506],
      zoom: 11,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "OpenStreetMap contributors"
          }
        },
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm"
          }
        ]
      }
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => {
      map.addSource("dispatch-routes", emptyDispatchRouteSource());
      map.addLayer({
        id: "dispatch-route-lines",
        type: "line",
        source: "dispatch-routes",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 5,
          "line-opacity": 0.88
        },
        layout: {
          "line-cap": "round",
          "line-join": "round"
        }
      });
    });
    mapRef.current = map;

    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (map === null) {
      return;
    }

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    if (depot !== null) {
      markersRef.current.push(
        new maplibregl.Marker({ element: depotMarkerElement() })
          .setLngLat([depot.longitude, depot.latitude])
          .setPopup(popupForDepot(depot))
          .addTo(map)
      );
    }

    routes.forEach((route, routeIndex) => {
      route.optimized_stop_order.forEach((stopId, stopIndex) => {
        const stop = stopById.get(stopId);
        if (stop === undefined) {
          return;
        }
        markersRef.current.push(
          new maplibregl.Marker({ element: stopMarkerElement(stopIndex + 1) })
            .setLngLat([stop.longitude, stop.latitude])
            .setPopup(
              popupForDispatchStop(
                stop,
                route.vehicle_name,
                stopIndex + 1,
                dispatchRouteColor(routeIndex)
              )
            )
            .addTo(map)
        );
      });
    });
  }, [depot, routes, stopById]);

  useEffect(() => {
    const map = mapRef.current;
    if (map === null) {
      return;
    }
    const activeMap = map;

    function updateRouteLines() {
      const source = activeMap.getSource("dispatch-routes") as
        | GeoJSONSource
        | undefined;
      if (source === undefined) {
        return;
      }

      source.setData(dispatchRouteLineData(routeLines));
    }

    if (activeMap.isStyleLoaded()) {
      updateRouteLines();
      return;
    }

    activeMap.once("load", updateRouteLines);
  }, [routeLines]);

  useEffect(() => {
    const map = mapRef.current;
    if (map === null || zoomRequest === 0) {
      return;
    }

    zoomToCoordinates(map, coordinatesForDispatchBounds(depot, routes, routeLines));
  }, [depot, routeLines, routes, zoomRequest]);

  return (
    <div className="map-wrap">
      <div className="route-map" ref={mapContainerRef} />
      {routeLines.every((route) => route.coordinates.length === 0) && (
        <div className="map-empty-state">
          Optimize dispatch to draw backend vehicle route geometry.
        </div>
      )}
    </div>
  );
}

function StopsScreen() {
  const [stops, setStops] = useState<Stop[]>([]);
  const [form, setForm] = useState<StopFormState>(emptyStopForm);
  const [editingStopId, setEditingStopId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadStops() {
    setIsLoading(true);
    setError("");

    try {
      const response = await requestJson<Stop[]>("/api/stops");
      setStops(response.data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load stops.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadStops();
  }, []);

  function resetForm() {
    setForm(emptyStopForm);
    setEditingStopId(null);
    setMessage("");
  }

  function startEdit(stop: Stop) {
    setForm(stopToForm(stop));
    setEditingStopId(stop.id);
    setMessage("");
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    setMessage("");

    try {
      const payload = stopFormToPayload(form);
      const path = editingStopId === null ? "/api/stops" : `/api/stops/${editingStopId}`;
      const method = editingStopId === null ? "POST" : "PUT";

      await requestJson<Stop>(path, {
        method,
        body: JSON.stringify(payload)
      });

      setMessage(editingStopId === null ? "Stop created." : "Stop updated.");
      resetForm();
      await loadStops();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save stop.");
    } finally {
      setIsSaving(false);
    }
  }

  async function deactivateStop(stop: Stop) {
    setError("");
    setMessage("");

    try {
      await requestJson<Stop>(`/api/stops/${stop.id}`, {
        method: "DELETE"
      });
      setMessage(`${stop.name} deactivated.`);
      await loadStops();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to deactivate stop.");
    }
  }

  return (
    <div className="vehicles-screen">
      <div className="screen-heading">
        <div>
          <h2 id="current-view-title">Stops</h2>
          <p>Manage pickups, deliveries, service time, and address status.</p>
        </div>
      </div>

      <div className="workspace-grid">
        <form className="entity-form" onSubmit={handleSubmit}>
          <div className="form-heading">
            <h3>{editingStopId === null ? "New Stop" : "Edit Stop"}</h3>
            {editingStopId !== null && (
              <button className="text-button" onClick={resetForm} type="button">
                Cancel
              </button>
            )}
          </div>

          <label>
            Name
            <input
              maxLength={120}
              onChange={(event) =>
                setForm((current) => ({ ...current, name: event.target.value }))
              }
              required
              type="text"
              value={form.name}
            />
          </label>

          <label>
            Type
            <select
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  stop_type: event.target.value as StopType
                }))
              }
              value={form.stop_type}
            >
              <option value="delivery">Delivery</option>
              <option value="pickup">Pickup</option>
              <option value="pickup_delivery">Pickup + Delivery</option>
            </select>
          </label>

          <label>
            Address
            <input
              maxLength={300}
              onChange={(event) =>
                setForm((current) => ({ ...current, address: event.target.value }))
              }
              required
              type="text"
              value={form.address}
            />
          </label>

          <label>
            Normalized address
            <input
              maxLength={300}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  normalized_address: event.target.value
                }))
              }
              required
              type="text"
              value={form.normalized_address}
            />
          </label>

          <div className="form-row">
            <label>
              Latitude
              <input
                max="90"
                min="-90"
                onChange={(event) =>
                  setForm((current) => ({ ...current, latitude: event.target.value }))
                }
                required
                step="0.000001"
                type="number"
                value={form.latitude}
              />
            </label>
            <label>
              Longitude
              <input
                max="180"
                min="-180"
                onChange={(event) =>
                  setForm((current) => ({ ...current, longitude: event.target.value }))
                }
                required
                step="0.000001"
                type="number"
                value={form.longitude}
              />
            </label>
          </div>

          <div className="form-row">
            <label>
              Quantity
              <input
                min="0"
                onChange={(event) =>
                  setForm((current) => ({ ...current, quantity: event.target.value }))
                }
                required
                step="1"
                type="number"
                value={form.quantity}
              />
            </label>
            <label>
              Weight lbs
              <input
                min="0"
                onChange={(event) =>
                  setForm((current) => ({ ...current, weight_lbs: event.target.value }))
                }
                required
                step="0.1"
                type="number"
                value={form.weight_lbs}
              />
            </label>
          </div>

          <div className="form-row">
            <label>
              Service minutes
              <input
                min="0"
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    service_minutes: event.target.value
                  }))
                }
                required
                step="1"
                type="number"
                value={form.service_minutes}
              />
            </label>
            <label>
              Priority
              <input
                min="0"
                onChange={(event) =>
                  setForm((current) => ({ ...current, priority: event.target.value }))
                }
                required
                step="1"
                type="number"
                value={form.priority}
              />
            </label>
          </div>

          <div className="form-row">
            <label>
              Earliest time
              <input
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    earliest_time: event.target.value
                  }))
                }
                type="time"
                value={form.earliest_time}
              />
            </label>
            <label>
              Latest time
              <input
                onChange={(event) =>
                  setForm((current) => ({ ...current, latest_time: event.target.value }))
                }
                type="time"
                value={form.latest_time}
              />
            </label>
          </div>

          <label>
            Address status
            <input
              maxLength={40}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  address_status: event.target.value
                }))
              }
              required
              type="text"
              value={form.address_status}
            />
          </label>

          <label>
            Special instructions
            <textarea
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  special_instructions: event.target.value
                }))
              }
              rows={3}
              value={form.special_instructions}
            />
          </label>

          <label className="checkbox-field">
            <input
              checked={form.active}
              onChange={(event) =>
                setForm((current) => ({ ...current, active: event.target.checked }))
              }
              type="checkbox"
            />
            Active
          </label>

          <button className="primary-button" disabled={isSaving} type="submit">
            {isSaving
              ? "Saving"
              : editingStopId === null
                ? "Create Stop"
                : "Save Stop"}
          </button>
        </form>

        <div className="table-panel">
          <div className="table-toolbar">
            <h3>Stops</h3>
            <button className="text-button" onClick={loadStops} type="button">
              Refresh
            </button>
          </div>

          {message && <p className="notice success">{message}</p>}
          {error && <p className="notice error">{error}</p>}

          {isLoading ? (
            <p className="muted">Loading stops...</p>
          ) : stops.length === 0 ? (
            <p className="muted">No stops have been added.</p>
          ) : (
            <div className="data-table-wrap">
              <table className="data-table stops-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Address</th>
                    <th>Weight</th>
                    <th>Time Window</th>
                    <th>Service Time</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {stops.map((stop) => (
                    <tr key={stop.id}>
                      <td>{stop.name}</td>
                      <td>{formatStopType(stop.stop_type)}</td>
                      <td>{stop.address}</td>
                      <td>{stop.weight_lbs.toLocaleString()} lb</td>
                      <td>{formatTimeWindow(stop.earliest_time, stop.latest_time)}</td>
                      <td>{stop.service_minutes.toLocaleString()} min</td>
                      <td>{stop.priority}</td>
                      <td>
                        <span
                          className={`entity-status ${
                            stop.active ? "active" : "inactive"
                          }`}
                        >
                          {stop.active ? stop.address_status : "Inactive"}
                        </span>
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="text-button"
                            onClick={() => startEdit(stop)}
                            type="button"
                          >
                            Edit
                          </button>
                          <button
                            className="text-button danger"
                            disabled={!stop.active}
                            onClick={() => deactivateStop(stop)}
                            type="button"
                          >
                            Deactivate
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function VehiclesScreen() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [form, setForm] = useState<VehicleFormState>(emptyVehicleForm);
  const [editingVehicleId, setEditingVehicleId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadVehicles() {
    setIsLoading(true);
    setError("");

    try {
      const response = await requestJson<Vehicle[]>("/api/vehicles");
      setVehicles(response.data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load vehicles.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadVehicles();
  }, []);

  function resetForm() {
    setForm(emptyVehicleForm);
    setEditingVehicleId(null);
    setMessage("");
  }

  function startEdit(vehicle: Vehicle) {
    setForm(vehicleToForm(vehicle));
    setEditingVehicleId(vehicle.id);
    setMessage("");
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    setMessage("");

    try {
      const payload = vehicleFormToPayload(form);
      const path =
        editingVehicleId === null
          ? "/api/vehicles"
          : `/api/vehicles/${editingVehicleId}`;
      const method = editingVehicleId === null ? "POST" : "PUT";

      await requestJson<Vehicle>(path, {
        method,
        body: JSON.stringify(payload)
      });

      setMessage(editingVehicleId === null ? "Vehicle created." : "Vehicle updated.");
      resetForm();
      await loadVehicles();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save vehicle.");
    } finally {
      setIsSaving(false);
    }
  }

  async function deactivateVehicle(vehicle: Vehicle) {
    setError("");
    setMessage("");

    try {
      await requestJson<Vehicle>(`/api/vehicles/${vehicle.id}`, {
        method: "DELETE"
      });
      setMessage(`${vehicle.name} deactivated.`);
      await loadVehicles();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to deactivate vehicle."
      );
    }
  }

  return (
    <div className="vehicles-screen">
      <div className="screen-heading">
        <div>
          <h2 id="current-view-title">Vehicles</h2>
          <p>Manage fleet capacity and route limits.</p>
        </div>
      </div>

      <div className="workspace-grid">
        <form className="entity-form" onSubmit={handleSubmit}>
          <div className="form-heading">
            <h3>{editingVehicleId === null ? "New Vehicle" : "Edit Vehicle"}</h3>
            {editingVehicleId !== null && (
              <button className="text-button" onClick={resetForm} type="button">
                Cancel
              </button>
            )}
          </div>

          <label>
            Name
            <input
              maxLength={120}
              onChange={(event) =>
                setForm((current) => ({ ...current, name: event.target.value }))
              }
              required
              type="text"
              value={form.name}
            />
          </label>

          <label>
            Max payload lbs
            <input
              min="0"
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  max_payload_lbs: event.target.value
                }))
              }
              required
              step="0.1"
              type="number"
              value={form.max_payload_lbs}
            />
          </label>

          <label>
            Max volume cubic ft
            <input
              min="0"
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  max_volume_cubic_ft: event.target.value
                }))
              }
              step="0.1"
              type="number"
              value={form.max_volume_cubic_ft}
            />
          </label>

          <label>
            Max route miles
            <input
              min="0"
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  max_route_miles: event.target.value
                }))
              }
              step="0.1"
              type="number"
              value={form.max_route_miles}
            />
          </label>

          <label>
            Max route minutes
            <input
              min="0"
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  max_route_minutes: event.target.value
                }))
              }
              step="1"
              type="number"
              value={form.max_route_minutes}
            />
          </label>

          <label className="checkbox-field">
            <input
              checked={form.active}
              onChange={(event) =>
                setForm((current) => ({ ...current, active: event.target.checked }))
              }
              type="checkbox"
            />
            Active
          </label>

          <button className="primary-button" disabled={isSaving} type="submit">
            {isSaving
              ? "Saving"
              : editingVehicleId === null
                ? "Create Vehicle"
                : "Save Vehicle"}
          </button>
        </form>

        <div className="table-panel">
          <div className="table-toolbar">
            <h3>Fleet</h3>
            <button className="text-button" onClick={loadVehicles} type="button">
              Refresh
            </button>
          </div>

          {message && <p className="notice success">{message}</p>}
          {error && <p className="notice error">{error}</p>}

          {isLoading ? (
            <p className="muted">Loading vehicles...</p>
          ) : vehicles.length === 0 ? (
            <p className="muted">No vehicles have been added.</p>
          ) : (
            <div className="data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Payload</th>
                    <th>Volume</th>
                    <th>Route Limit</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {vehicles.map((vehicle) => (
                    <tr key={vehicle.id}>
                      <td>{vehicle.name}</td>
                      <td>{vehicle.max_payload_lbs.toLocaleString()} lb</td>
                      <td>{formatOptionalNumber(vehicle.max_volume_cubic_ft, "cu ft")}</td>
                      <td>
                        {formatRouteLimit(
                          vehicle.max_route_miles,
                          vehicle.max_route_minutes
                        )}
                      </td>
                      <td>
                        <span
                          className={`entity-status ${
                            vehicle.active ? "active" : "inactive"
                          }`}
                        >
                          {vehicle.active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="text-button"
                            onClick={() => startEdit(vehicle)}
                            type="button"
                          >
                            Edit
                          </button>
                          <button
                            className="text-button danger"
                            disabled={!vehicle.active}
                            onClick={() => deactivateVehicle(vehicle)}
                            type="button"
                          >
                            Deactivate
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SettingsScreen() {
  const [statusReport, setStatusReport] = useState<ProviderStatusReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadSystemHealth() {
    setIsLoading(true);
    setError("");

    try {
      const response = await requestJson<ProviderStatusReport>(
        "/api/status/providers"
      );
      setStatusReport(response.data);
    } catch (caught) {
      setStatusReport(null);
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load system health."
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadSystemHealth();
  }, []);

  const providerByName = useMemo(
    () =>
      new Map(
        (statusReport?.providers ?? []).map((provider) => [
          provider.name,
          provider
        ])
      ),
    [statusReport]
  );
  const rows = systemHealthDefinitions.map((definition) => ({
    ...definition,
    provider: providerByName.get(definition.providerName) ?? null
  }));

  return (
    <div className="settings-screen">
      <div className="screen-heading">
        <div>
          <h2 id="current-view-title">Settings</h2>
          <p>System health for local and external RouteForge providers.</p>
        </div>
        <button className="primary-button" onClick={loadSystemHealth} type="button">
          {isLoading ? "Checking" : "Refresh"}
        </button>
      </div>

      {error && <p className="notice error">{error}</p>}

      <section className="system-health-panel" aria-label="System health">
        <div className="table-toolbar">
          <h3>System Health</h3>
          <span className={`health-overall ${systemHealthStatusClass(statusReport?.overall_status ?? "unavailable")}`}>
            {formatSystemHealthStatus(statusReport?.overall_status ?? "unavailable", "backend")}
          </span>
        </div>

        <div className="system-health-grid">
          {rows.map((row) => {
            const displayStatus = formatSystemHealthStatus(
              row.provider?.status ?? "unavailable",
              row.providerName
            );
            return (
              <article className="system-health-card" key={row.providerName}>
                <div className="system-health-card-header">
                  <div>
                    <h4>{row.label}</h4>
                    <span className={`scope-badge ${row.scope.toLowerCase()}`}>
                      {row.scope}
                    </span>
                  </div>
                  <span
                    className={`health-status-badge ${displayStatus.toLowerCase()}`}
                  >
                    {displayStatus}
                  </span>
                </div>
                <p>{row.provider?.message ?? `${row.label} status is unavailable.`}</p>
                <dl>
                  {systemHealthDetails(row.provider).map(([key, value]) => (
                    <div key={key}>
                      <dt>{formatDetailLabel(key)}</dt>
                      <dd>{formatDetailValue(value)}</dd>
                    </div>
                  ))}
                </dl>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function routeLineCoordinatesFromGeometry(
  geometry: RouteGeometry | null
): [number, number][] {
  if (geometry === null) {
    return [];
  }

  if (geometry.coordinates.length > 0) {
    return geometry.coordinates.map((coordinate) => [
      coordinate.longitude,
      coordinate.latitude
    ]);
  }

  if (geometry.polyline !== null && geometry.polyline.trim() !== "") {
    return decodePolyline(geometry.polyline, 6);
  }

  return [];
}

function decodePolyline(polyline: string, precision: number): [number, number][] {
  let index = 0;
  let latitude = 0;
  let longitude = 0;
  const coordinates: [number, number][] = [];
  const factor = 10 ** precision;

  while (index < polyline.length) {
    const latitudeChange = decodePolylineValue(polyline, index);
    index = latitudeChange.nextIndex;
    const longitudeChange = decodePolylineValue(polyline, index);
    index = longitudeChange.nextIndex;

    latitude += latitudeChange.value;
    longitude += longitudeChange.value;
    coordinates.push([longitude / factor, latitude / factor]);
  }

  return coordinates;
}

function decodePolylineValue(polyline: string, startIndex: number) {
  let result = 0;
  let shift = 0;
  let index = startIndex;
  let byte = 0;

  do {
    byte = polyline.charCodeAt(index) - 63;
    result |= (byte & 0x1f) << shift;
    shift += 5;
    index += 1;
  } while (byte >= 0x20 && index <= polyline.length);

  return {
    value: result & 1 ? ~(result >> 1) : result >> 1,
    nextIndex: index
  };
}

function emptyRouteSource() {
  return {
    type: "geojson" as const,
    data: routeLineData([])
  };
}

function emptyDispatchRouteSource() {
  return {
    type: "geojson" as const,
    data: dispatchRouteLineData([])
  };
}

function routeLineData(coordinates: [number, number][]) {
  if (coordinates.length < 2) {
    return {
      type: "FeatureCollection" as const,
      features: []
    };
  }

  return {
    type: "FeatureCollection" as const,
    features: [
      {
        type: "Feature" as const,
        properties: {},
        geometry: {
          type: "LineString" as const,
          coordinates
        }
      }
    ]
  };
}

function dispatchRouteLineData(
  routes: { color: string; coordinates: [number, number][] }[]
) {
  return {
    type: "FeatureCollection" as const,
    features: routes
      .filter((route) => route.coordinates.length >= 2)
      .map((route) => ({
        type: "Feature" as const,
        properties: { color: route.color },
        geometry: {
          type: "LineString" as const,
          coordinates: route.coordinates
        }
      }))
  };
}

function dispatchRouteColor(index: number) {
  const colors = ["#1f7a8c", "#b35a2e", "#4f6f2f", "#7a4aa0", "#b42318"];
  return colors[index % colors.length];
}

function depotMarkerElement() {
  const element = document.createElement("div");
  element.className = "map-marker depot-marker";
  element.textContent = "D";
  return element;
}

function stopMarkerElement(order: number) {
  const element = document.createElement("div");
  element.className = "map-marker stop-marker";
  element.textContent = String(order);
  return element;
}

function popupForDepot(depot: Depot) {
  const content = document.createElement("div");
  content.className = "map-popup";

  const title = document.createElement("strong");
  title.textContent = depot.name;
  const address = document.createElement("span");
  address.textContent = depot.address;

  content.append(title, address);
  return new maplibregl.Popup({ offset: 18 }).setDOMContent(content);
}

function popupForDispatchStop(
  stop: Stop,
  vehicleName: string,
  order: number,
  color: string
) {
  const content = document.createElement("div");
  content.className = "map-popup";

  const title = document.createElement("strong");
  title.textContent = `${order}. ${stop.name}`;
  const vehicle = document.createElement("span");
  vehicle.textContent = vehicleName;
  vehicle.style.color = color;
  const details = document.createElement("span");
  details.textContent = `${formatStopType(stop.stop_type)} - ${stop.service_minutes.toLocaleString()} min - ${stop.weight_lbs.toLocaleString()} lb`;

  content.append(title, vehicle, details);
  return new maplibregl.Popup({ offset: 18 }).setDOMContent(content);
}

function popupForStop(stop: Stop, order: number) {
  const content = document.createElement("div");
  content.className = "map-popup";

  const title = document.createElement("strong");
  title.textContent = `${order}. ${stop.name}`;
  const address = document.createElement("span");
  address.textContent = stop.address;
  const details = document.createElement("span");
  details.textContent = `${formatStopType(stop.stop_type)} - ${stop.service_minutes.toLocaleString()} min - ${stop.weight_lbs.toLocaleString()} lb`;

  content.append(title, address, details);
  return new maplibregl.Popup({ offset: 18 }).setDOMContent(content);
}

function coordinatesForDispatchBounds(
  depot: Depot | null,
  routes: DispatchVehicleRoute[],
  routeLines: { coordinates: [number, number][] }[]
) {
  const lineCoordinates = routeLines.flatMap((route) => route.coordinates);
  if (lineCoordinates.length > 0) {
    return lineCoordinates;
  }

  const coordinates: [number, number][] = [];
  if (depot !== null) {
    coordinates.push([depot.longitude, depot.latitude]);
  }
  routes.forEach((route) => {
    route.coordinates.forEach((coordinate) => {
      coordinates.push([coordinate.longitude, coordinate.latitude]);
    });
  });
  return coordinates;
}

function coordinatesForBounds(
  depot: Depot | null,
  stops: MapStopMarker[],
  routeCoordinates: [number, number][]
) {
  if (routeCoordinates.length > 0) {
    return routeCoordinates;
  }

  const coordinates: [number, number][] = [];
  if (depot !== null) {
    coordinates.push([depot.longitude, depot.latitude]);
  }

  coordinates.push(
    ...stops.map(({ stop }) => [stop.longitude, stop.latitude] as [number, number])
  );
  return coordinates;
}

function zoomToCoordinates(
  map: maplibregl.Map,
  coordinates: [number, number][]
) {
  if (coordinates.length === 0) {
    return;
  }

  if (coordinates.length === 1) {
    map.flyTo({ center: coordinates[0], zoom: 13 });
    return;
  }

  const bounds = coordinates.reduce(
    (currentBounds, coordinate) => currentBounds.extend(coordinate),
    new maplibregl.LngLatBounds(coordinates[0], coordinates[0])
  );
  map.fitBounds(bounds as LngLatBoundsLike, {
    padding: 52,
    maxZoom: 15,
    duration: 500
  });
}

function formatMiles(value: number) {
  return `${value.toLocaleString(undefined, {
    maximumFractionDigits: 1
  })} mi`;
}

function formatMinutes(value: number) {
  return `${Math.round(value).toLocaleString()} min`;
}

function formatPounds(value: number) {
  return `${value.toLocaleString(undefined, {
    maximumFractionDigits: 1
  })} lb`;
}

function formatSystemHealthStatus(
  status: ProviderStatusState,
  providerName: string
): SystemHealthDisplayStatus {
  if (status === "ok") {
    return "ONLINE";
  }

  if (providerName === "map_data") {
    return "MISSING";
  }

  if (status === "warning") {
    return providerName === "geocoder" ? "OFFLINE" : "MISSING";
  }

  return "OFFLINE";
}

function systemHealthStatusClass(status: ProviderStatusState) {
  return formatSystemHealthStatus(status, "backend").toLowerCase();
}

function systemHealthDetails(provider: ProviderStatusItem | null) {
  if (provider === null) {
    return [["status", "No status report"]] as [string, unknown][];
  }

  const entries = Object.entries(provider.details);
  return entries.length === 0 ? [["status", provider.status]] : entries;
}

function formatDetailLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDetailValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "None";
  }

  if (Array.isArray(value)) {
    return value.length === 0 ? "None" : value.map(formatDetailValue).join(", ");
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function formatAiAction(action: AIInstructionAction) {
  const target =
    action.entity_id === null
      ? action.target
      : `${action.target} ${action.entity_id}`;
  return `${formatInstructionAction(action.action_type)} on ${target}`;
}

function formatInstructionAction(actionType: AIInstructionAction["action_type"]) {
  return actionType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatAiFields(fields: Record<string, unknown>) {
  const entries = Object.entries(fields);
  if (entries.length === 0) {
    return "No field changes.";
  }

  return entries
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(", ");
}

function isAiExplanationQuestion(value: string) {
  const normalized = value.toLowerCase();
  return (
    normalized.includes("?") ||
    normalized.startsWith("which ") ||
    normalized.startsWith("why ") ||
    normalized.startsWith("what ") ||
    normalized.startsWith("can ") ||
    normalized.includes("deadhead") ||
    normalized.includes("infeasible") ||
    normalized.includes("version") ||
    normalized.includes("shipment fit")
  );
}

function extractVersionPair(value: string) {
  const matches = [...value.matchAll(/version\s+(\d+)/gi)].map((match) =>
    Number(match[1])
  );
  if (matches.length < 2) {
    return null;
  }

  return {
    base: matches[0],
    comparison: matches[1]
  };
}

function extractShipmentWeight(value: string) {
  const match = value.match(/(\d+(?:\.\d+)?)\s*(?:lb|lbs|pounds)/i);
  return match === null ? null : Number(match[1]);
}

function formatExplanationIntent(intent: string) {
  return intent
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function createEmptyReviewRow(): ScreenshotReviewRow {
  return {
    id: crypto.randomUUID(),
    customer: "",
    address: "",
    normalized_address: "",
    latitude: null,
    longitude: null,
    geocode_status: "",
    geocode_message: "",
    stop_type: "unknown",
    quantity: "1",
    weight_lbs: "",
    time_window: "",
    notes: "",
    confidence: "",
    validation_status: "user_review_required"
  };
}

function extractedStopToReviewRow(stop: ExtractedStop): ScreenshotReviewRow {
  return {
    id: crypto.randomUUID(),
    customer: stop.customer ?? "",
    address: stop.address ?? "",
    normalized_address: "",
    latitude: null,
    longitude: null,
    geocode_status: "",
    geocode_message: "",
    stop_type: stop.stop_type,
    quantity: stop.quantity === null ? "1" : String(stop.quantity),
    weight_lbs: stop.weight_lbs === null ? "" : String(stop.weight_lbs),
    time_window: stop.time_window ?? "",
    notes: stop.notes ?? "",
    confidence: stop.confidence.toFixed(2),
    validation_status:
      stop.confidence >= 0.7 ? "user_review_required" : "low_confidence"
  };
}

function reviewRowToStopPayload(row: ScreenshotReviewRow) {
  const timeWindow = parseTimeWindow(row.time_window);
  return {
    name: row.customer.trim() || row.address.trim(),
    address: row.address.trim(),
    normalized_address: row.normalized_address.trim() || row.address.trim(),
    latitude: row.latitude,
    longitude: row.longitude,
    stop_type: row.stop_type,
    quantity: row.quantity.trim() === "" ? 1 : Number(row.quantity),
    weight_lbs: row.weight_lbs.trim() === "" ? 0 : Number(row.weight_lbs),
    service_minutes: 0,
    priority: 0,
    earliest_time: timeWindow.earliest_time,
    latest_time: timeWindow.latest_time,
    special_instructions: row.notes.trim() || null,
    address_status: "confirmed",
    active: true
  };
}

function parseTimeWindow(value: string) {
  const matches = value.match(/\b\d{1,2}:\d{2}\b/g);
  return {
    earliest_time: matches?.[0] ?? null,
    latest_time: matches?.[1] ?? null
  };
}

function fileToBase64(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("Unable to read image file."));
        return;
      }

      resolve(result.split(",")[1] ?? result);
    };
    reader.onerror = () => reject(new Error("Unable to read image file."));
    reader.readAsDataURL(file);
  });
}

function formatReviewStatus(statusValue: ReviewStatus) {
  return statusValue
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function isAcceptedScreenshot(file: File) {
  const lowerName = file.name.toLowerCase();
  return (
    acceptedScreenshotTypes.has(file.type) ||
    acceptedScreenshotExtensions.some((extension) => lowerName.endsWith(extension))
  );
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) {
    return `${bytes.toLocaleString()} B`;
  }

  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) {
    return `${kilobytes.toLocaleString(undefined, {
      maximumFractionDigits: 1
    })} KB`;
  }

  return `${(kilobytes / 1024).toLocaleString(undefined, {
    maximumFractionDigits: 1
  })} MB`;
}

function formatOptionalNumber(value: number | null, suffix: string) {
  return value === null ? "No limit" : `${value.toLocaleString()} ${suffix}`;
}

function formatRouteLimit(miles: number | null, minutes: number | null) {
  const parts = [];
  if (miles !== null) {
    parts.push(`${miles.toLocaleString()} mi`);
  }
  if (minutes !== null) {
    parts.push(`${minutes.toLocaleString()} min`);
  }

  return parts.length === 0 ? "No limit" : parts.join(" / ");
}

function formatStopType(stopType: StopType) {
  if (stopType === "pickup_delivery") {
    return "Pickup + Delivery";
  }

  return stopType.charAt(0).toUpperCase() + stopType.slice(1);
}

function formatTimeWindow(earliest: string | null, latest: string | null) {
  if (earliest === null && latest === null) {
    return "Open";
  }

  const start = earliest?.slice(0, 5) ?? "Any";
  const end = latest?.slice(0, 5) ?? "Any";
  return `${start} - ${end}`;
}

function formatNullableMiles(value: number | null) {
  return value === null ? "Not available" : formatMiles(value);
}

function formatNullableMinutes(value: number | null) {
  return value === null ? "Not available" : formatMinutes(value);
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString();
}

function formatSolverStatus(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default App;
