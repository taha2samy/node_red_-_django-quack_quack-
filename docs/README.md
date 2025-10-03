<p align="center">
  <img src="./imgs/logo.svg" alt="Quack Quack Project Logo" width="150"/>
</p>

# Welcome to the Quack Quack Documentation

Welcome to the official documentation for **Quack Quack**, a real-time IoT integration platform. This documentation provides a comprehensive guide to understanding, setting up, using, and extending the project's powerful backend capabilities.

---

## What is Quack Quack?

Quack Quack is a **backend-focused integration platform** designed to be the robust core for real-time IoT applications. It provides the essential infrastructure to:
- **Ingest** real-time data from IoT devices and hardware (like Node-RED) via secure WebSockets.
- **Broadcast** this data efficiently to multiple connected clients (such as web dashboards, mobile apps, or other services).
- **Secure** data access with a powerful, granular permissions system (RBAC).
- **Process** commands sent from clients and forward them back to the appropriate devices.

While this project includes a sample frontend for demonstration, its primary focus is on providing a scalable, event-driven backend that you can integrate with any user interface or system.

## Who is this for?

This documentation is primarily intended for:
- **Backend & IoT Developers:** Who need a solid foundation to build real-time applications without reinventing the wheel.
- **System Integrators:** Who want to connect various hardware and software components through a centralized, real-time hub.
- **System Administrators:** Who are responsible for deploying and managing the core infrastructure of an IoT system.

## How to Navigate these Docs

This documentation is organized into several key sections. Use the table of contents below to jump to the section that interests you most.

### Table of Contents

| Section                                     | Description                                                                                                   |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **[1. Project Overview](./01_overview.md)**       | A detailed introduction to the project's goals, key features, and the technology stack it's built on.         |
| **[2. System Architecture](./02_architecture.md)**| A deep dive into the system's architecture, data flows, and the design patterns used.                         |
| **[3. Getting Started](./03_getting_started.md)** | A complete guide to setting up your development environment and running the project for the first time.       |
| **[4. WebSocket API Reference](./04_api_reference/README.md)** | Detailed documentation for the WebSocket APIs used for communication between clients and the server.        |
| **[5. Core Concepts](./05_core_concepts/README.md)**       | Explanations of the fundamental concepts that power Quack Quack, such as authentication, permissions, and reactivity. |
| **[6. Database Schema](./06_database/schema.md)**   | A visual guide and explanation of the database structure and relationships.                                   |

---

We recommend starting with the **[Project Overview](./01_overview.md)** to get a feel for the project, followed by the **[Getting Started](./03_getting_started.md)** guide to get your own instance running.