# 4. WebSocket API Reference

Quack Quack's real-time functionality is powered by a WebSocket-based API. This API allows for persistent, low-latency, bidirectional communication between the server and connected clients (both devices and browsers).

## Core Concepts

- **Endpoints:** The system exposes different WebSocket endpoints for different types of clients (devices vs. browsers). Each endpoint has its own authentication mechanism and expected message format.
- **JSON-based Messaging:** All communication over the WebSocket connection is done using JSON-formatted text messages.
- **Message Structure:** A typical message has a `type` field that indicates the action to be performed, along with a `payload` containing the necessary data.

## API Sections

This reference is divided into two main sections, one for each type of client. Please refer to the section relevant to your use case:

- **[Browser API](./browser_api.md):**
  This section details the WebSocket API for frontend clients, such as web dashboards. It covers messages for subscribing to data, sending commands, and receiving real-time updates.

- **[Device API](./device_api.md):**
  This section details the WebSocket API for hardware clients, such as a Node-RED instance. It covers the secure authentication process and the format for sending sensor data.

---

## General Message Flow

The diagram below illustrates the high-level interaction between the clients and the server's WebSocket consumers.

![System Architecture Overview](./../imgs/system_overview.png)

_While the Browser and Device APIs are distinct, they both interact with the central Django Channels backend, which orchestrates the flow of data between them._