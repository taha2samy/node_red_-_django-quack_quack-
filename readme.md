<p align="center">
  <img src="docs/imgs/logo.svg" alt="Quack Quack Project Logo" width="150"/>
</p>

<h1 align="center">Quack Quack</h1>

<p align="center">
  A real-time IoT dashboard and control system built with Django Channels.
  <br />
  <a href="docs/README.md"><strong>Explore the docs »</strong></a>
  <br />
  <br />
  <a href="#key-features">Key Features</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#architecture-overview">Architecture</a>
</p>
<p align="center">
  <a href="https://codespaces.new/taha2samy/node_red_-_django-quack_quack-"><img src="https://github.com/codespaces/badge.svg" alt="Open in GitHub Codespaces"></a>
  <a href="https://github.com/taha2samy/node_red_-_django-quack_quack-/network/updates"><img src="https://img.shields.io/badge/dependabot-enabled-brightgreen.svg" alt="Dependabot"></a>
  <br>
  <img src="https://img.shields.io/badge/Python-3.12-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Django-5.2-green.svg" alt="Django Version">
  <img src="https://img.shields.io/badge/Channels-4.3-red.svg" alt="Channels Version">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
  <img src="https://img.shields.io/github/stars/taha2samy/node_red_-_django-quack_quack-?style=social" alt="GitHub Stars">
</p>


---

## About The Project

**Quack Quack** is a powerful, scalable, and secure platform for monitoring and controlling IoT devices in real-time. It provides a web-based dashboard where users can visualize data from sensors (gauges, charts) and send commands to actuators (switches, sliders), all governed by a flexible role-based access control system.

The backend is built on the robust Django framework, supercharged with Django Channels for handling thousands of persistent WebSocket connections. This makes it ideal for applications requiring low-latency, bidirectional communication between devices, servers, and user interfaces.

### Key Features

*   ⚡️ **Real-Time Communication:** Bidirectional data flow using WebSockets for instant UI updates.
*   🛡️ **Secure Device Authentication:** JWT-based authentication ensures that only authorized devices can connect.
*   🔐 **Granular Permissions:** Attribute-Based Access Control (ABAC) for users and groups at the individual element level.
*   🏗️ **Scalable Architecture:** A decoupled, event-driven architecture powered by Redis as a message broker.
*   📊 **Dynamic Frontend:** A component-based frontend built with Vanilla JS, allowing for easy extension.
*   🐳 **Dockerized:** Comes with a Docker setup for easy development and deployment.

---

## Architecture Overview

The system is designed with a clear separation of concerns, utilizing an Event-Driven Architecture. Devices and Browsers act as clients, communicating with a central Django backend through dedicated WebSocket consumers. Django Signals ensure that any state change in the database is instantly reflected across all connected clients.

<p align="center">
  <a href="docs/02_architecture.md">
    <img src="docs/imgs/system_overview.png" alt="System Architecture Diagram" width="800">
  </a>
  <br>
  <em>Click to explore the detailed architecture documentation.</em>
</p>

---

## Quick Start

Get the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Docker & Docker Compose

### Installation (Docker)

  **Clone the repository:**
    ```sh
    git clone https://github.com/taha2samy/node_red_-_django-quack_quack-.git
    cd node_red_-_django-quack_quack-
    ```
    use buildin tasks to run dockercompose


---

## Documentation

For a deep dive into the system's architecture, API reference, core concepts, and setup guides, please refer to our **[Full Documentation](docs/README.md)**.

Here are some key sections:
*   [**System Architecture**](docs/02_architecture.md)
*   [**API Reference**](docs/04_api_reference/README.md)
*   [**Device Authentication Flow**](docs/05_core_concepts/authentication.md)
*   [**Database Schema**](docs/06_database/schema.md)

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
