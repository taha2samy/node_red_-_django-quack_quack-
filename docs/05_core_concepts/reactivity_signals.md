# Reactivity with Django Signals

A key feature of Quack Quack is its ability to react instantly to changes in its own state. For instance, if an administrator revokes a user's permissions, that user's dashboard will reflect this change immediately without requiring a page refresh. This dynamic, real-time behavior is achieved through the **Django Signals** framework.

## What are Django Signals?

Signals are a core feature of Django that allow certain senders to notify a set of receivers that some action has taken place. It's a form of the **Observer design pattern**, which helps decouple different parts of an application.

In Quack Quack, we use signals to monitor changes (creations, updates, deletions) in our database models. When a change occurs, a signal is "fired", and a corresponding "handler" function is executed.

## The Reactivity Flow

The handler function's primary job is to translate a database event into a real-time WebSocket message that can be understood by connected clients.

![Signals Flow Diagram](./../imgs/signals_flow.png)

Here is a breakdown of the process, using a permission change as an example:

**1. The Trigger: An Admin Action**
- An administrator navigates to the Django Admin panel and modifies an `ElementPermissionsUser` record. For example, they change a user's permission from `Read/Write` to `Read-Only`.

**2. The Database Event: `post_save` Signal**
- When the administrator saves the change, Django's ORM calls the `.save()` method on the model instance.
- Immediately after the data is successfully saved to the database, Django's signal dispatcher fires a `post_save` signal. This signal includes crucial information, most importantly a reference to the `instance` that was just saved.

**3. The Receiver: The Signal Handler**
- A handler function, such as `on_permission_save`, has been registered to "listen" for `post_save` signals from the `ElementPermissionsUser` model.
- Django invokes this handler, passing the saved `instance` to it.

**4. The Logic: Translating the Event**
- Inside the handler, we have access to the specific permission object that was changed. The logic then performs a critical translation:
  - It constructs a unique **channel group name** based on the primary key of the permission instance (e.g., `f'perm_{instance.id}'`).
  - It creates a JSON payload containing the updated permission data.

**5. The Broadcast: Sending to the Channel Layer**
- The handler calls `channel_layer.group_send()` with the constructed group name and payload.
- This publishes a message to a specific "topic" on the Redis message broker.

**6. The Delivery: Reaching the Consumer**
- Any `BrowserConsumer` that had previously subscribed to an element affected by this permission change would have also been added to this specific `perm_{id}` group.
- These consumers receive the message from the channel layer.

**7. The Final Action: Updating the Client**
- The consumer's `permissions_updates` method is executed.
- It sends a formatted WebSocket message down to the specific user's browser, informing it of the new permission level. The browser's JavaScript then updates the UI accordingly (e.g., by disabling a slider).

## Why is this powerful?

This signal-based reactivity ensures that the application's state is always synchronized across all layers. It decouples the database logic from the real-time communication logic, leading to a cleaner, more maintainable, and highly responsive system.