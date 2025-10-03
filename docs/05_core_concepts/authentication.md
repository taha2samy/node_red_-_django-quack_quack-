# Device Authentication

Ensuring that only authorized and trusted devices can connect to the Quack Quack platform is the first and most critical layer of security. The system employs a robust authentication mechanism based on **JSON Web Tokens (JWTs)** and **Asymmetric Cryptography** (also known as public-key cryptography).

This approach is significantly more secure than using simple API keys or static tokens, as it guarantees both the **identity** and the **integrity** of the connecting device.

## The Authentication Flow

The entire authentication process happens in a fraction of a second during the initial WebSocket connection handshake and is orchestrated by a dedicated authentication middleware.

![Device Authentication Flow](./../imgs/device_auth_flow.png)

Here is a step-by-step breakdown of the process illustrated in the diagram:

**1. Connection Initiation (Device Side):**
- Before attempting to connect, the device must generate a short-lived JWT.
- This token is signed using a **private key** that is stored securely on the device and should never be shared.
- The JWT's payload **must** contain an `id` claim, which corresponds to the device's unique UUID in the Quack Quack database.
- The device then initiates a WebSocket connection request, including the signed JWT in the `Authorization: Bearer <token>` header.

**2. Request Interception (Server Side):**
- The `AuthMiddlewareDevice` intercepts the incoming connection request before it reaches the main application logic (the consumer).

**3. Initial Token Decode:**
- The middleware performs a preliminary decoding of the JWT **without verifying the signature**.
- The sole purpose of this step is to safely extract the `device_id` from the token's payload.

**4. Public Key Lookup:**
- Using the extracted `device_id`, the middleware queries the `JWTPublicKey` table in the database to find the corresponding **public key** associated with that device.

**5. Existence Check (First Security Gate):**
- If no public key is found for the given `device_id` (either because the device ID is invalid or no key has been assigned), the authentication fails, and the connection is immediately rejected.

**6. Signature Verification (Core Security Step):**
- If a public key is found, the middleware now performs the crucial cryptographic verification.
- It uses the fetched public key to verify the signature of the original JWT. Since only the legitimate device possesses the matching private key, a valid signature proves that the token was indeed sent by that device and has not been tampered with.

**7. Validity Check (Second Security Gate):**
- If the signature is invalid (meaning the token was signed with the wrong key or was altered in transit), the authentication fails, and the connection is rejected.
- The middleware also checks other standard JWT claims, such as the expiration time (`exp`), to prevent replay attacks.

**8. Connection Accepted:**
- If the signature is valid and all checks pass, the authentication is successful.
- The middleware populates the connection's scope with the authenticated device's information and passes the connection along to the `NodeRedConsumer` to begin communication.

## Why this approach?

- **Non-repudiation:** A valid signature proves that the message could *only* have come from the device holding the private key.
- **No Shared Secrets on Server:** The server only needs to know the public key. The sensitive private key never leaves the device, minimizing the impact of a server-side breach.
- **Token-based Security:** Each connection is authenticated with a short-lived token, reducing the risk associated with long-lived credentials.
