# Architecture Overview

This document provides an overview of the current application architecture, explaining how it aligns with clean architecture principles such as domain-driven package structure, service and repository layers, and API/UI separation.

## 1. Domain-Driven Package Structure

The application's core logic is organized into domain-specific packages located under the `src/modules` directory. The primary domain in this project is the **scheduler**.

-   **`src/modules/scheduler/`**: This package encapsulates all logic related to job scheduling. It is designed to be a self-contained component, containing its own models, services, API routes, and data schemas. This modular approach allows developers to focus on a single functional area without needing to navigate the entire codebase.

## 2. Core Architectural Layers

The application employs a layered architecture to separate concerns, making the codebase more maintainable, testable, and scalable. The main layers are the Service Layer, the Repository Pattern, and the Schema/Data Validation layer.

### 2.1. Service Layer (`service.py`)

-   **Location**: `src/modules/scheduler/service.py`
-   **Responsibility**: This layer contains the application's business logic. It encapsulates business use cases (e.g., "Get Dashboard Summary") and orchestrates the necessary operations. The API layer calls these service functions to perform tasks, keeping the business logic separate from the web/API framework.

### 2.2. Repository Pattern (`crud.py`)

-   **Location**: `src/core/crud.py`
-   **Responsibility**: This layer abstracts all data access logic. It uses the Repository Pattern to provide a generic, reusable set of methods for interacting with the database (Create, Read, Update, Delete).
-   **Implementation**: The `CRUDBase` class provides generic CRUD functionality. The `job_definition_service` in `service.py` inherits from `CRUDBase` to create a specific repository for the `JobDefinition` model. This design decouples the service layer from the specifics of the ORM (SQLAlchemy), making it easier to test and potentially switch data sources in the future.

### 2.3. Schema / Data Validation (`schemas.py`)

-   **Location**: `src/modules/scheduler/schemas.py`
-   **Responsibility**: This layer is responsible for defining the data contracts for the API. It uses Pydantic models to handle:
    -   **Input Validation**: Validating the structure and types of incoming API request data.
    -   **Data Serialization**: Shaping the data sent in API responses.
-   **Benefit**: This keeps validation logic out of the API view/routing layer and provides a clear, self-documenting definition of the API's data structures.

## 3. Decoupled API and Web UI

The application maintains a strict separation between the backend API and the frontend Web UI.

### 3.1. Separate Routing

-   **API Routing**: Handled by FastAPI. The API routes are defined in `src/modules/scheduler/router.py` and are prefixed with `/api`.
-   **Web UI Routing**: Handled by Flask. The web page routes are defined in `src/webgui/app.py`.

This clear separation allows the API and UI to evolve independently.

### 3.2. Separation of Responsibilities

-   **API Layer (`router.py`)**: The API endpoints are "thin". Their primary responsibility is to handle HTTP-specific tasks: parsing JSON requests, calling the appropriate service/repository method to execute the business logic, and returning a JSON response with the correct HTTP status code.
-   **Web UI Layer (`webgui/app.py`)**: The Web UI acts as a client to the backend API. It makes HTTP requests to the `/api` endpoints to fetch and manipulate data, and then renders this data into HTML templates for the user's browser.

This architecture ensures that business logic is not duplicated. Both the Web UI and any other potential clients (e.g., a mobile app, a third-party service) consume the same, single source of truth: the backend API.
