"""
Blueprints Package

This package contains the Flask Blueprint modules that define the web layer
of the application (auth, review, stats).

What is a Blueprint?
In Flask, a Blueprint is a modular grouping of related routes (endpoints).
Each blueprint defines a set of URL paths and HTTP methods, and is later
registered with the main Flask application in the app factory.

Blueprints are responsible for:
- Reading request data (form fields, JSON bodies, query params).
- Managing Flask user/session state.
- Opening and closing database Sessions via app.db.
- Calling service-layer functions to perform business logic.
- Returning rendered templates or JSON responses.

During development, blueprints may call temporary stub implementations
in the services layer to unblock frontend integration. However, business
logic must remain in services and should not be implemented directly
inside route handlers.

Blueprints must NOT:
- Contain business logic.
- Mutate models directly outside of services.
- Create database engines or define database configuration.

All database configuration lives in app.db.
All domain logic lives in services.
This package contains only web-facing route definitions.
"""
