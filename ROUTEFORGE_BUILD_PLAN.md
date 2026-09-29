1. Create the project control files
Create AGENTS.md, PROJECT_SPEC.md, TASKS.md, and CHANGELOG.md for RouteForge AI.  
AGENTS.md must instruct Codex to:
- inspect only files relevant to the current task
- preserve working code
- make the smallest complete change
- avoid unrelated refactors
- avoid fake/mock functionality unless explicitly requested
- run focused tests
- update TASKS.md after completing a task
- add a concise CHANGELOG.md entry
Architecture:
- React + TypeScript + Vite
- FastAPI
- SQLite
- SQLAlchemy
- OR-Tools
- Valhalla
- OpenStreetMap
- MapLibre
- Ollama
- local-first
- no required Google Maps APIs
Do not build application features yet.

2. Inspect the computer and environment
Read AGENTS.md.
Verify the development environment for RouteForge AI.
Check:
- Python version
- pip
- Node.js
- npm
- Git
- Ollama
- NVIDIA GPU availability
- Docker availability
- WSL2 availability
Do not install anything yet.
Create docs/environment-report.md showing what is installed, what is missing, and what is recommended.

3. Create the repository structure
Read AGENTS.md.
Create the RouteForge AI monorepo structure.
Required directories:
backend/
frontend/
tests/
docs/
fixtures/
scripts/
map-data/
routing-data/
Backend should have:
api
models
schemas
services
database
optimization
routing
geocoding
vision
ai
economics
providers
Do not implement business functionality yet.

FOUNDATION
4. Build the FastAPI backend shell
Read AGENTS.md.
Create the minimum FastAPI backend.
Requirements:
- application factory or clean startup structure
- /api/health
- structured JSON responses
- basic exception handling
- environment configuration
- CORS for local frontend development
- pytest setup
Add a health endpoint test.
Do not create business models yet.

5. Configure SQLite and SQLAlchemy
Read AGENTS.md.
Configure SQLite using SQLAlchemy.
Requirements:
- database session management
- declarative base
- configurable database URL
- application startup initialization
- test database support
Add focused tests for database connectivity.
Do not create application entities yet.

6. Build the React frontend shell
Read AGENTS.md.
Create the frontend with:
- React
- TypeScript
- Vite
Create the application shell with sidebar navigation:
Dashboard
Routes
Stops
Vehicles
Drivers
Customers
Route History
Costs
Settings
Do not implement full pages yet.
Connect the frontend to /api/health and show backend status.

CORE DATA
7. Create Depot model
Read AGENTS.md.
Implement the Depot database model and Pydantic schemas.
Include:
- id
- name
- address
- latitude
- longitude
- default start time
- active
- created_at
- updated_at
Add focused model/schema tests.
Do not build API endpoints yet.

8. Create Vehicle model
Implement the Vehicle model and schemas.
Fields:
- id
- name
- max_payload_lbs
- max_volume_cubic_ft optional
- max_route_miles optional
- max_route_minutes optional
- active
- created_at
- updated_at
Validate that capacities cannot be negative.
Add focused tests.

9. Create Customer model
Implement Customer model and schemas.
Fields:
- id
- name
- phone optional
- email optional
- notes optional
- active
- timestamps
Add focused tests.

10. Create Stop model
Implement Stop model and Pydantic schemas.
Fields:
- id
- customer_id optional
- name
- address
- normalized_address
- latitude
- longitude
- stop_type
- quantity
- weight_lbs
- service_minutes
- priority
- earliest_time
- latest_time
- special_instructions
- address_status
- active
- timestamps
Stop types:
- pickup
- delivery
- pickup_delivery
Add validation and tests.

11. Create Route models
Implement:
- Route
- RouteStop
- RouteVersion
- OptimizationRun
A route version must preserve previous optimization results rather than overwrite them.
Include fields needed for:
- stop order
- ETA
- departure time
- distance
- travel duration
- service duration
- solver status
- route metrics
Add focused tests.

CRUD
12. Build Depot API
Implement CRUD endpoints for Depots.
Add:
- GET
- POST
- PUT
- DELETE/deactivate
Add API tests.
Do not modify unrelated entities.

13. Build Vehicle API
Implement Vehicle CRUD endpoints.
Add tests.
Keep the change limited to vehicle functionality.

14. Build Stop API
Implement Stop CRUD endpoints.
Include:
- create
- list
- retrieve
- update
- deactivate/delete
Add validation errors that are understandable by the frontend.
Add tests.

15. Build route CRUD
Implement route creation, retrieval, update, and listing.
Allow stops to be assigned to a route.
Do not optimize routes yet.
Add tests.

FRONTEND CRUD
16. Build Vehicles screen
Create the Vehicles screen.
Support:
- list vehicles
- create
- edit
- deactivate
Connect to existing backend APIs.
Do not add new backend functionality unless required to fix an actual defect.

17. Build Stops screen
Create professional Stops management UI.
Columns:
- name
- type
- address
- weight
- time window
- service time
- priority
- status
- actions
Support create/edit/delete.
Do not implement optimization yet.

18. Build Route creation screen
Create the Route workspace.
Include:
- route name
- starting depot
- vehicle selection
- stop selection
- ordered stop table
- Optimize Route button disabled until optimization exists
Keep map area as an empty application panel, not a fake map.

ADDRESS SYSTEM
19. Create geocoding provider interface
Create a provider-based geocoding architecture.
Interface should support:
- geocode(address)
- normalize_address(address)
- confidence/status
Do not depend on Google.
Add a GeocodeResult schema.
Do not implement a live provider yet.

20. Implement first geocoder
Research and implement the most practical open geocoder for this local-first application.
Prefer an OpenStreetMap-compatible solution.
Requirements:
- provider abstraction must remain intact
- rate limiting
- caching
- timeout handling
- ambiguous result handling
- no silent address guessing
Add tests using mocked network responses where appropriate.

21. Add geocode cache
Implement GeocodeCache.
Cache:
- original address
- normalized address
- latitude
- longitude
- provider
- status
- timestamp
Avoid repeated lookups for identical normalized addresses.
Add tests.

ROUTING ENGINE
22. Create routing provider abstraction
Create RoutingProvider.
It must support:
- travel-time matrix
- distance matrix
- route geometry
- route legs
Do not connect OR-Tools yet.

23. Set up Valhalla
Integrate Valhalla as the first RoutingProvider.
Keep it isolated behind the routing provider interface.
Use Florida OpenStreetMap data initially.
Create:
- health check
- matrix request
- route request
Do not add route optimization yet.
Add integration tests that can skip cleanly if Valhalla is not running.

24. Create routing matrix service
Implement a service that accepts depot + stops and generates:
- travel-time matrix
- distance matrix
Use Valhalla.
Validate coordinates before requests.
Add caching where reasonable.
Add tests.

OR-TOOLS
25. Build basic optimizer
Implement a single-vehicle OR-Tools optimizer.
Input:
- travel-time matrix
- depot index
Output:
- optimized stop order
- solver status
Do not add capacity or time windows yet.
Add deterministic tests using known matrices.

26. Add vehicle payload constraints
Extend the OR-Tools optimizer to support:
- vehicle payload capacity
- stop shipment weights
A route exceeding capacity must be rejected or solved appropriately.
Add focused tests.

27. Add time windows
Extend optimization to support:
- earliest arrival
- latest arrival
- service duration
- route start time
- required end time
Return a clear NO FEASIBLE SOLUTION state when constraints cannot be satisfied.
Add tests.

28. Add pickup/delivery constraints
Add pickup-before-delivery relationships.
Ensure paired pickup/delivery jobs maintain correct sequence.
Add tests.

29. Add route optimization API
Implement:
POST /api/routes/{id}/optimize
Workflow:
1. validate route
2. validate coordinates
3. retrieve Valhalla matrix
4. run OR-Tools
5. request final route geometry
6. calculate metrics
7. save RouteVersion
8. return complete result
Add API tests.

MAP
30. Add MapLibre
Integrate MapLibre GL JS into the route screen.
Requirements:
- depot marker
- numbered stop markers
- route line
- zoom-to-route
- stop popups
Use the actual route geometry returned by the backend.
Do not fabricate route lines.

31. Display route metrics
Add Route Summary cards:
- total miles
- drive time
- service time
- route duration
- number of stops
- payload
- remaining capacity
Use backend-calculated results.

SCREENSHOT IMPORT
32. Build screenshot upload UI
Add IMPORT FROM SCREENSHOT.
Support:
- drag/drop
- file picker
- clipboard paste
- PNG
- JPG/JPEG
- WebP
Show image preview.
Do not implement image understanding yet.

33. Create vision provider architecture
Create VisionExtractionProvider.
Input:
image
Output:
structured list of ExtractedStop.
Fields:
- customer
- address
- type
- quantity
- weight
- time window
- notes
- confidence
Do not connect it to routing yet.

34. Add local screenshot extraction
Implement a local vision-based provider capable of extracting address lists from screenshots.
Prefer a local model compatible with the RTX 3060 Ti and Ollama or another practical local inference method.
Requirements:
- structured JSON
- schema validation
- confidence
- no invented addresses
- preserve uncertain text
Add fixture screenshots/tests where practical.

35. Build screenshot review screen
After extraction, display an editable review table.
Columns:
- customer
- address
- type
- weight
- time window
- confidence
- validation status
Statuses:
- confirmed
- low confidence
- ambiguous
- not found
- user review required
User can edit/remove/add rows before confirming.

36. Connect screenshot import to geocoding
After the user approves extracted stops:
- normalize addresses
- geocode them
- mark uncertain addresses
Do not optimize until invalid/ambiguous addresses are clearly handled.

37. Complete Screenshot → Route workflow
Connect:
Screenshot
→ extraction
→ review
→ address validation
→ starting location
→ optimization
→ map
Add a button:
OPTIMIZE FROM STARTING LOCATION
Test the complete workflow.

ROUTE HISTORY
38. Complete route versioning
Ensure every optimization creates a new RouteVersion.
Never overwrite previous versions.
Add API support to list and retrieve route versions.

39. Build route comparison
Allow two RouteVersions to be compared.
Compare:
- miles
- drive time
- route time
- stop order
- payload
Show differences clearly.

DEADHEAD
40. Add deadhead calculations
Implement:
- pre-pickup deadhead
- between-job repositioning
- post-delivery deadhead
- return-to-depot deadhead
- total unloaded mileage
- deadhead percentage
Keep calculation logic separate and tested.

ECONOMICS
41. Add CostProfile model
Implement CostProfile.
Fields should support:
- operating cost per mile
- driver hourly rate
- tolls
- parking
- route expenses
- default service charges
Add schemas and tests.

42. Build route economics engine
Calculate:
- revenue
- operating miles
- route cost
- driver cost
- contribution
- revenue per operating mile
- cost per operating mile
- contribution per operating mile
- margin
Do not label estimated contribution as accounting profit.
Add tests.

LOCAL AI
43. Create local AI provider interface
Create an AI provider abstraction.
First provider:
Ollama.
The AI must not calculate mileage or routes itself.
It may only:
- interpret commands
- explain results
- propose structured changes

44. Build structured AI instruction parser
Implement natural-language interpretation.
Example:
"Make Stop 6 arrive before 11 and return by 4."
Output structured proposed actions.
Validate every result with Pydantic.
Invalid AI output must be rejected safely.

45. Build AI Dispatcher UI
Add an ASK DISPATCH AI panel.
AI responses modifying route state must first show:
PROPOSED CHANGES
followed by:
APPLY
CANCEL
AI must never silently modify operational data.

46. Add AI route explanations
Allow questions like:
- Which stop creates the most deadhead?
- Why is this route infeasible?
- What changed from Version 1 to Version 2?
- Can this shipment fit?
The AI must derive its explanation from application-calculated metrics, not invent numbers.

MULTI-VEHICLE
47. Extend optimizer for multiple vehicles
Add OR-Tools multi-vehicle support.
Each vehicle may have:
- capacity
- starting depot
- ending depot
- maximum hours
- maximum mileage
Add tests before UI changes.

48. Build multi-vehicle dispatch UI
Allow the user to select multiple vehicles for a route set.
Show each optimized vehicle route separately on the dispatch screen and map.

SYSTEM HEALTH
49. Build provider status service
Create status checks for:
- backend
- database
- Ollama
- Valhalla
- geocoder
- map data
Return readable status information.

50. Build Settings/System Health screen
Display:
FastAPI
SQLite
Ollama
Valhalla
Geocoder
Map data
Statuses:
ONLINE
OFFLINE
MISSING
DISABLED
Also clearly identify which services are LOCAL versus EXTERNAL.

STARTUP
51. Create Windows startup script
Create start-routeforge.bat.
It should:
- verify backend dependencies
- check Ollama
- check Valhalla
- check database
- start backend
- start frontend
- open application in browser
Give readable errors rather than failing silently.

TESTING
52. Create full integration fixture
Create a Tampa Bay development fixture containing:
- one depot
- one cargo van
- ten stops
- one timed stop
- one priority stop
- one heavy delivery
- one pickup
- normal deliveries
Use a 3,400 lb vehicle payload limit.
Do not hard-code this fixture into production logic.

53. Run backend test audit
Review backend tests only.
Identify:
- untested core logic
- brittle tests
- duplicate tests
- missing failure cases
Add only high-value missing tests.
Do not refactor production code unless necessary to fix a verified problem.

54. Run frontend workflow audit
Test these workflows:
Manual route creation
Screenshot import
Address review
Route optimization
Route map
Route history
AI proposed changes
Fix actual defects only.

PERFORMANCE
55. Benchmark routing
Benchmark:
- 10 stops
- 25 stops
- 50 stops
- 100 stops
Record:
- matrix generation time
- solver time
- total request time
- memory usage
Save results to docs/performance.md.

56. Optimize only verified bottlenecks
Read docs/performance.md.
Optimize only measured bottlenecks.
Do not perform speculative refactoring.
Preserve behavior and tests.

FINAL AUDIT
57. Security/privacy audit
Audit RouteForge AI for privacy and security.
Identify:
- data sent externally
- exposed secrets
- unsafe file uploads
- injection risks
- dangerous AI tool access
- overly permissive APIs
Fix high-priority issues.
Do not add unnecessary enterprise complexity.

58. Dependency audit
Review all dependencies.
Remove:
- unused packages
- duplicates
- unnecessary heavyweight packages
Do not replace working libraries without a measurable reason.

59. Production-readiness audit
Review the complete application against PROJECT_SPEC.md.
Create:
docs/release-readiness.md
Classify each requirement as:
PASS
PARTIAL
FAIL
NOT YET REQUIRED
Do not modify code during this audit.

60. Fix release blockers
Read docs/release-readiness.md.
Fix only items classified as FAIL that block the Version 1 release.
Work one issue at a time.
Run relevant tests after every repair.

61. Final end-to-end test
Your last Codex instruction should be:
Perform the final RouteForge AI Version 1 end-to-end validation.
Validate this exact workflow:
1. Start application on Windows.
2. Import screenshot containing multiple addresses.
3. Extract stops locally.
4. Review and correct addresses.
5. Validate/geocode addresses.
6. Choose starting location.
7. Choose vehicle.
8. Optimize route.
9. Display route on map.
10. Display mileage and time.
11. Save route version.
12. Ask local AI to explain route.
13. Modify a constraint using AI.
14. Approve proposed change.
15. Re-optimize.
16. Compare route versions.
Do not add new features.
Fix only issues preventing this workflow from completing successfully.
Run all relevant tests.
Report:
- PASS/FAIL for each step
- tests run
- failures remaining
- files changed

One rule for every Codex session
Start each instruction with:
Read AGENTS.md. Work only on the task below. Inspect only relevant files. Preserve working code. Do not refactor unrelated code.

And end each with:
Run the narrowest relevant tests. Update TASKS.md and add one concise CHANGELOG.md entry when complete.

That structure will conserve your Codex allowance much better than giving it broad requests like “continue building the app.”