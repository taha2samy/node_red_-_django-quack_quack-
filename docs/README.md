<p align="center">
  <img src="./imgs/logo.svg" alt="Quack Quack Project Logo" width="150"/>
</p>

# Welcome to the Quack Quack Documentation

Welcome to the official documentation for **Quack Quack**, a real-time IoT dashboard and control system. This documentation provides a comprehensive guide to understanding, setting up, using, and extending the project.

---

## What is Quack Quack?

Quack Quack is a full-stack platform designed to bridge the gap between physical IoT devices and a dynamic web interface. It allows you to:
- **Monitor** real-time data from sensors through interactive dashboard widgets like gauges and charts.
- **Control** actuators and devices remotely using elements like switches and sliders.
- **Secure** access to your data and controls with a powerful, granular permissions system.

The entire system is built on a scalable, event-driven architecture using Django Channels, making it suitable for both small-scale hobbyist projects and larger, more demanding IoT applications.

## Who is this for?

This documentation is intended for several audiences:
- **Developers:** Who want to understand the codebase, extend its functionality, or integrate it with their own systems.
- **System Administrators:** Who are responsible for deploying, managing, and maintaining the platform.
- **End-Users:** Who need to understand how to use the dashboard and its features.

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