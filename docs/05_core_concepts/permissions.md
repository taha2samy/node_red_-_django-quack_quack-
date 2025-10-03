# Permissions & Onboarding

Quack Quack implements a powerful and granular access control system to ensure that users can only view and interact with the data they are authorized to access. This section explains the permission model and provides a step-by-step guide for onboarding new devices and users.

## The Permission Model: Role-Based Access Control (RBAC)

The system is built on a **Role-Based Access Control (RBAC)** model, with an added layer for user-specific overrides. This provides a balance between ease of management and the flexibility to handle exceptions.

### Core Components of the Model

- **Users:** Standard Django `User` accounts.
- **Groups:** Standard Django `Group` models, which function as **Roles** (e.g., "Engineers", "Operators", "Viewers").
- **Elements:** The individual data points or control widgets (e.g., "Main Temperature Sensor", "Boiler Switch"). These are the **Resources** being protected.
- **Permissions:** The level of access. There are two levels:
    - `R` (**Read-Only**): The user can view the element's data but cannot send commands to it.
    - `RC` (**Read/Write**): The user can both view data and send commands (e.g., change a slider's value or flip a switch).

### How Permissions are Evaluated

When a user tries to subscribe to or interact with an element, the system evaluates their permissions in the following order of precedence:

1.  **Direct User Permission:** Does the user have a direct permission assigned specifically to them for this element? If so, this permission is used.
2.  **Group Permissions:** If no direct permission exists, the system checks all the groups the user belongs to. It finds the **highest permission level** granted by any of those groups for the element.
3.  **No Access:** If neither the user nor any of their groups has a permission entry for the element, access is denied.

> **Example:** If a user is in a "Viewers" group (Read-Only) but has a direct "Read/Write" permission for a specific critical sensor, they will have Read/Write access to that sensor, and Read-Only access to other elements granted by their group.

---

## Onboarding Workflow: A Step-by-Step Guide

Onboarding a new device and granting a user access to its data involves a clear, sequential process managed through the Django Admin panel.

![Device & User Onboarding Flow](./../imgs/onboarding_flow.png)

This workflow ensures that all components are correctly configured and linked before the system goes live.

### Phase 1: User & Security Setup

1.  **Create User:** In the Django Admin, navigate to `Users` and create a new user account (e.g., `operator-A`).
2.  **Create Public Key:** Navigate to `JWTPublicKeys` and create a new key record. Paste the device's **public PEM key** into the form. This key will be used to verify the device's identity.

### Phase 2: Device & Element Configuration

3.  **Create Device:** Navigate to `Devices` and create a new device record (e.g., "Factory Floor Sensor Rig").
4.  **Assign Public Key:** In the new device form, select the `JWTPublicKey` you created in Step 2 from the dropdown menu. This links the device to its cryptographic identity.
5.  **Create Elements:** Navigate to `Elements` and create the data elements associated with this device (e.g., "Temperature Sensor 1", "Pressure Valve"). Make sure to select the correct parent `Device` for each element.

### Phase 3: Granting Permissions

This is the final step that connects the user to the device's data.

6.  **Create Permission Record:** Navigate to `ElementPermissionsUsers` (for a direct permission) or `ElementPermissionsGroups` (for a role-based permission).
7.  **Link Everything Together:** In the new permission form, select:
    - The **User** (or Group) you want to grant access to.
    - The **Element** you want them to access.
    - The desired **Permission Level** (`R` or `RC`).

### Phase 4: Completion

Once saved, the onboarding process is complete. The device can now authenticate using its private key, and the user can log in to the dashboard and access the element's data according to the permissions you have just defined.
