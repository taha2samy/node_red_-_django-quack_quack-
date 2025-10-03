# Device WebSocket API

This document provides a detailed reference for the WebSocket API used by hardware or programmatic clients (referred to as "Devices") to connect and stream data to the Quack Quack platform.

## Connection

- **Endpoint:** `ws://<your_domain>/device/node_red/`
- **Authentication:** Requires a JSON Web Token (JWT) signed by the device's private key. The token must be sent in the `Authorization` header of the initial WebSocket connection request.

**Header Example:**
```
Authorization: Bearer <your_signed_jwt>
```

### JWT Payload Requirements

The JWT payload **must** contain the following claim:
- `id` (string): The UUID of the device as registered in the Quack Quack database. This ID is used by the server to look up the corresponding public key for signature verification.

**Example Payload:**
```json
{
  "id": "f53b2639-b17e-5604-8767-17254ebaa351",
  "iat": 1653091200,
  "exp": 1653094800
}
```

The server will use the `id` from this payload to fetch the device's public key and verify the token's signature. If the signature is invalid, or if the device has no public key assigned, the connection will be rejected.

![Device Authentication Flow](./../imgs/device_auth_flow.png)

---

## Messages Sent by the Client (Device -> Server)

This is the primary message format for a device to send data to the server.

### `message_element`

Sends a data point from one of the device's elements to the server. The server will then cache this data and broadcast it to all subscribed browser clients.

- **This message does not have a `type` field.** The device consumer is designed to directly process this specific JSON structure.
- **Payload**:
  - `element_id` (string, required): The UUID of the element this data belongs to. The device must be the parent of this element, otherwise the message will be ignored.
  - `message` (object, required): The data payload. The structure of this object should match what the frontend components expect (e.g., `{ "value": 42.5 }`).
  - `auth` (object, optional): If you want to specify the sender. If omitted, the server will use the device's identity.
  - `last_edit_at` (string, optional): An ISO 8601 timestamp. If omitted, the server will generate a timestamp upon receipt.

**Example (from a sensor):**
```json
{
  "element_id": "98994c94-71b8-53b0-85f3-d1c6483978de",
  "message": {
    "value": 22.7
  },
  "last_edit_at": "2024-05-21T11:00:05.456Z"
}
```

---

## Messages Received by the Client (Server -> Device)

This is the format for messages (commands) sent from the server to the device, typically originating from a user's action on the dashboard.

### `message_element`

Forwards a command to a specific element on the device.

- **This message also does not have a `type` field.**
- **Payload**:
  - `element_id` (string): The UUID of the target element.
  - `message` (object): The command payload from the browser (e.g., `{ "value": 1 }` to turn on a switch).
  - `auth` (object): Information about the user who sent the command.
    - `user_id` (number): The ID of the user.
    - `username` (string): The name of the user.
  - `last_edit_at` (string): ISO 8601 timestamp of when the command was sent.

**Example (command to turn on a switch):**
```json
{
  "element_id": "e5b1cb93-114e-5609-9dcf-2b7360375e5a",
  "message": {
    "value": 1
  },
  "auth": {
    "user_id": 5,
    "username": "taha.samy"
  },
  "last_edit_at": "2024-05-21T11:05:10.890Z"
}
```

The device is responsible for listening for these messages, parsing the `element_id`, and routing the `message` payload to the appropriate physical component or logic.
