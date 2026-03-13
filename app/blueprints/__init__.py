"""
Blueprints Package

Flask Blueprint modules that define the web layer of the application.

Each blueprint groups related routes (URL endpoints) and is registered
with the main Flask app in app.py. Current blueprints:

    auth   — login, logout, profile creation and deletion
    review — card display, rating submission, simulated time controls
    stats  — progress metrics and summary views
    themes — theme listing and selection API

Blueprints are responsible for reading request data, managing session
state, calling service-layer functions, and returning rendered templates
or JSON responses.

Blueprints SHOULD NOT:
- Contain business logic (services handle that).
- Mutate models directly outside of services.
- Create database engines or define database configuration.

All database configuration lives in app.db.
All domain logic lives in services.
"""
