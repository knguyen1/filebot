- Implemented provider scaffolding and ran a Java-side scan to mirror FileBot’s architecture: `MovieIdentificationService` (TMDb/OMDb) and `EpisodeListProvider` (TheTVDB/AniDB/TVMaze/TMDb TV). I created Python protocols and a registry.

- Next, here's a concise multi-phase plan to ship quickly, starting with metadata connections and culminating in basic renaming.

### Phase 0 — Foundations (done here)
- Scaffold provider protocols and models to follow SOLID and IOC:
  - Datasource protocols: `MovieIdentificationService`, `EpisodeListProvider`.
  - Models: `SearchResult`, `Movie`, `SeriesInfo`, `Episode`.
  - Config loader: `FILEBOT_API_TMDB`, `FILEBOT_API_TVDB`.
  - Registry that wires providers from config.
- Provider stubs:
  - `TMDbClient` stub for movies.
  - `TheTVDBClient` stub for episodes.
- Expose `provider_registry` via `filebot.core`.

### Phase 1 — Connect to real metadata providers (MVP)
- Add minimal HTTP client layer using stdlib `urllib.request` or `httpx` (if allowed).
- TMDb (movies):
  - Implement `search_movie(query, locale)`: call `/search/movie`, parse results.
  - Implement `get_movie_descriptor(movie, locale)`: call `/movie/{id}` or by IMDb id.
  - Add rate limiting and simple in-memory caching.
- TheTVDB (series/episodes):
  - Implement `search(query, locale)`: `/search/series`.
  - Implement `get_series_info(series|id, locale)`: `/series/{id}`.
  - Implement `get_episode_list(series|id, order, locale)`: `/series/{id}/episodes?...` with pagination and sort order mapping.
  - Implement token flow for TheTVDB v2: `/login` with API key and token refresh.

Deliverable: Given API keys, we can search movies/series and fetch episodes.

### Phase 2 — UI integration and provider selection
- In `ui/views/rename_panel.py`:
  - Inject `provider_registry` into the view.
  - Add combo box to select datasource: movie vs series (identical to Java’s `PresetEditor` logic).
  - Wire search box to provider search; display select list; fetch details.
- In `ui/components/file_list.py`:
  - Add ability to attach fetched metadata to file list items for preview.

Deliverable: Perform a search from UI, preview selected title, and loaded episode list.

### Phase 3 — Filename parsing and matchers
- Implement simple movie matcher:
  - Extract title and optional year from filename.
  - Use TMDb search, choose best candidate by string similarity and year proximity.
- Implement simple episode matcher:
  - Parse SxxEyy and absolute numbers.
  - Use TheTVDB search to resolve series; fetch episode list; map parsed numbers to episodes respecting sort order.

Deliverable: For a directory of files, resolve target names for the preview.

### Phase 4 — Formatting and preview
- Implement naming templates similar to FileBot basics:
  - Movies: `{n} ({y})` → and extension.
  - Series: `{n} - {s00e00} - {t}`.
- Show a two-column preview (current → new).
- Add conflict detection and minimal sanitization.

Deliverable: Preview accurate target names for common cases.

### Phase 5 — Apply renames (basic)
- Implement dry-run and execute rename operations with conflict policy (skip/overwrite/unique suffix).
- Add undo stack for the last operation (in-memory session).

Deliverable: Perform batch renames safely.

### Phase 6 — Enhancements and parity steps
- Add locale selection; map to provider language codes.
- Add simple caches to reduce API calls; basic backoff on provider rate limits.
- Add TMDb TV as alternative TV provider; plugin-like registry for extensibility.
- Add tests:
  - Unit tests for providers with recorded fixtures.
  - Matching and formatting tests for known examples.

### Phase 7 — Config, observability, and robustness
- Config file support (`~/.filebot.toml`) + env; merge strategy.
- Structured logging with context (provider, request id).
- Clear error surfaces in UI (auth, rate-limit, network).

### What we learned from Java FileBot
- Uses `WebServices` as an IOC container for clients; we mirrored via `ProviderRegistry`.
- Interfaces: `MovieIdentificationService` and `EpisodeListProvider`.
- TMDb: movie search/info; TheTVDB: series/episodes; both have localization and images.
- Local index + remote search; we can add local fuzzy search later for perf.

If you want, I can proceed with Phase 1 by implementing real HTTP calls for TMDb and TheTVDB (using stdlib, or adding `httpx` if allowed).

- Files added:
  - `src/filebot/core/models.py`
  - `src/filebot/core/providers/base.py`
  - `src/filebot/core/providers/tmdb.py`
  - `src/filebot/core/providers/tvdb.py`
  - `src/filebot/core/providers/__init__.py`
  - `src/filebot/core/config.py`
  - `src/filebot/core/registry.py`
  - `src/filebot/core/__init__.py`

- Notes:
  - Ruff flagged docstring/copyright/import-style items. I can fix them next.
  - Set environment variables `FILEBOT_API_TMDB` and `FILEBOT_API_TVDB` for live connections.
