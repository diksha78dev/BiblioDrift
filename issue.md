# BiblioDrift Issue Tracker

----
- * where *: `backend/app.py`
- * issue *: Missing rate limiting on authentication endpoints
- * fix *: Implement Flask-Limiter and apply decorators to `/login` and `/register` routes
- * why * : Prevents brute-force attacks and credential stuffing against user accounts
----

----
- * where *: `backend/models.py`
- * issue *: Lack of indexes on foreign key columns in core database models
- * fix *: Add `index=True` to SQLAlchemy column definitions for frequently queried relational fields
- * why * : Improves database query performance during complex joins and lookups
----

----
- * where *: `frontend/js/library-3d.js`
- * issue *: Three.js scene memory leak on component unmount
- * fix *: Implement proper disposal of geometries, materials, and textures when destroying the 3D scene
- * why * : Prevents browser tab crashing and severe lag after prolonged use or navigation
----

----
- * where *: `backend/cache_service.py`
- * issue *: Redis connection not handling timeouts gracefully
- * fix *: Wrap cache operations in try-except blocks and configure appropriate timeout values
- * why * : Prevents the entire application from hanging if the caching server goes offline
----

----
- * where *: `backend/config.py`
- * issue *: Database URI constructed insecurely via string concatenation
- * fix *: Use a secure URL builder or standard environment variable string parsing (e.g., `os.getenv`)
- * why * : Avoids potential injection vulnerabilities and ensures safe handling of database credentials
----

----
- * where *: `frontend/pages/auth.html`
- * issue *: Passwords input missing `autocomplete="new-password"`
- * fix *: Update the HTML input attributes to explicitly define autocomplete behavior
- * why * : Helps password managers correctly identify and save user credentials securely
----

----
- * where *: `backend/app.py`
- * issue *: CORS policy is too permissive (`*`)
- * fix *: Restrict CORS origins to only the specific frontend domain in production settings
- * why * : Mitigates Cross-Origin Resource Sharing attacks from malicious third-party sites
----

----
- * where *: `backend/models.py`
- * issue *: Timestamps not using timezone-aware datetime objects
- * fix *: Update `datetime.utcnow()` to use timezone-aware objects (e.g., `datetime.now(timezone.utc)`)
- * why * : Prevents subtle bugs when formatting dates for users in different geographical regions
----

----
- * where *: `frontend/js/library-3d.js`
- * issue *: Large 3D models loading synchronously, blocking the main thread
- * fix *: Implement Web Workers or asynchronous loading mechanisms with loading spinners
- * why * : Keeps the user interface responsive and prevents the browser from freezing during heavy asset loading
----

----
- * where *: `backend/cache_service.py`
- * issue *: Cache eviction policy not defined, leading to potential Out Of Memory (OOM) errors
- * fix *: Configure Redis with an LRU (Least Recently Used) eviction policy and set a max memory limit
- * why * : Ensures system stability by preventing the cache from consuming all available server RAM
----

----
- * where *: `frontend/pages/auth.html`
- * issue *: CSRF token missing in login form submission
- * fix *: Integrate Flask-WTF or custom CSRF tokens into the HTML form and validate on backend
- * why * : Protects users from Cross-Site Request Forgery attacks that could hijack their sessions
----

----
- * where *: `backend/config.py`
- * issue *: Hardcoded API keys for external services (e.g., email provider, storage)
- * fix *: Move all sensitive keys to a `.env` file and use `python-dotenv` for loading
- * why * : Prevents accidental leakage of secrets into source control repositories
----

----
- * where *: `backend/app.py`
- * issue *: Global error handler returning raw stack traces in 500 HTTP responses
- * fix *: Catch unhandled exceptions and return a generic, user-friendly JSON error message in production
- * why * : Prevents exposing internal application logic, directory structures, and potential vulnerabilities to attackers
----

----
- * where *: `frontend/js/library-3d.js`
- * issue *: Missing fallback UI for WebGL-disabled or unsupported browsers
- * fix *: Detect WebGL support on initialization and display a graceful error message or 2D fallback
- * why * : Improves user experience by informing users why the 3D features are not functioning instead of showing a blank screen
----

----
- * where *: `backend/models.py`
- * issue *: N+1 query problem when fetching books and their associated authors
- * fix *: Use SQLAlchemy's `joinedload` or `subqueryload` to eagerly load related entities
- * why * : Drastically reduces the number of database queries and improves API response times
----

----
- * where *: `backend/cache_service.py`
- * issue *: Lack of retry mechanism for transient cache connection failures
- * fix *: Implement exponential backoff retries using a library like `tenacity` for cache operations
- * why * : Increases system resilience against brief network hiccups between the app and the cache server
----

----
- * where *: `backend/app.py`
- * issue *: Missing request input validation for incoming JSON payloads
- * fix *: Implement a schema validation library like Pydantic or Marshmallow for all POST/PUT routes
- * why * : Prevents malformed data from crashing the application or corrupting database records
----

----
- * where *: `frontend/pages/auth.html`
- * issue *: No client-side password strength validation during registration
- * fix *: Add JavaScript to enforce minimum length, special characters, and numbers before form submission
- * why * : Provides immediate feedback to the user and reduces unnecessary API calls for weak passwords
----

----
- * where *: `frontend/js/library-3d.js`
- * issue *: Inefficient rendering loop updating static 3D objects every frame
- * fix *: Separate static and dynamic objects, and only update matrices/geometries for moving entities
- * why * : Reduces CPU/GPU overhead, improves frame rates, and saves battery life on mobile devices
----

----
- * where *: `backend/models.py`
- * issue *: Soft delete not implemented, leading to permanent data loss on accidental deletion
- * fix *: Add an `is_deleted` boolean flag and update query logic to filter out deleted records
- * why * : Allows for data recovery and maintains referential integrity for auditing purposes
----

----
- * where *: `backend/config.py`
- * issue *: Missing different configurations for Testing, Development, and Production environments
- * fix *: Create a base config class and inherit it for specific environments (e.g., `TestingConfig`, `ProductionConfig`)
- * why * : Ensures that tests don't accidentally drop the production database or use real API credits
----

----
- * where *: `backend/app.py`
- * issue *: File upload endpoint missing MIME type and extension validation
- * fix *: Validate the `Content-Type` header and verify file magic numbers using a library like `python-magic`
- * why * : Prevents malicious users from uploading executable scripts disguised as images or documents
----

----
- * where *: `frontend/js/library-3d.js`
- * issue *: 3D assets not utilizing browser caching via Cache-Control headers
- * fix *: Configure the backend or CDN to serve `.gltf`/`.obj`/`.png` files with long-lived max-age headers
- * why * : Significantly reduces load times for returning users by loading heavy assets from local disk cache
----

----
- * where *: `backend/cache_service.py`
- * issue *: Cache key collisions possible due to lack of distinct namespacing
- * fix *: Implement a prefixing system for cache keys (e.g., `user:123:profile`, `book:45:metadata`)
- * why * : Prevents different parts of the application from accidentally overwriting each other's cached data
----

----
- * where *: `frontend/pages/auth.html`
- * issue *: Login button not disabled while the authentication request is pending
- * fix *: Add JS to disable the submit button and show a loading state upon form submission
- * why * : Prevents users from clicking multiple times and sending duplicate authentication requests to the server
----
