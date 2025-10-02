(function() {
    if (window.websocketControllerInitialized) return;
    window.websocketControllerInitialized = true;

    console.log("Initializing WebSocket Controller...");

    if (typeof window.Elements === 'undefined') {
        window.Elements = {};
    }

    const socketUrl = `ws://${window.location.host}/browser/simple/`;
    let socket;

    function connect() {
        socket = new WebSocket(socketUrl);

        socket.onopen = function(event) {
            console.log('WebSocket connection established. Subscribing to all registered elements...');
            setTimeout(() => {
                for (const elementId in window.Elements) {
                    console.log(`- Sending subscription request for element: ${elementId}`);
                    sendMessage({ type: 'subscribe', element_id: elementId });
                }
            }, 100);
        };

        socket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log("Received data from server:", data);

                const elementId = data.element_id;
                const componentInstances = window.Elements[elementId];

                if (!componentInstances) {
                    console.warn(`Received message for an unregistered element_id: ${elementId}`);
                    return;
                }

                componentInstances.forEach(instance => {
                    routeMessageToComponent(instance, data);
                });

            } catch (error) {
                console.error("Failed to parse incoming message or route it:", error, event.data);
            }
        };

        socket.onclose = function(event) {
            console.warn('WebSocket closed. Attempting to reconnect in 5 seconds...');
            for (const elementId in window.Elements) {
                window.Elements[elementId].forEach(instance => {
                    if (typeof instance.setStatus === 'function') {
                        instance.setStatus('disconnected');
                    }
                     if (typeof instance.setSubscriptionStatus === 'function') {
                        instance.setSubscriptionStatus(false);
                    }
                });
            }
            setTimeout(connect, 5000);
        };

        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
            socket.close();
        };
    }

    function routeMessageToComponent(instance, data) {
        switch (data.type) {
            case 'subscribe':
                if (typeof instance.setSubscriptionStatus === 'function') instance.setSubscriptionStatus(data.subscribed);
                if (typeof instance.setPermissions === 'function') instance.permissions = data.permissions;
                if (typeof instance.setStatus === 'function') instance.setStatus(data.connected ? 'connected' : 'disconnected');
                break;
            
            case 'unsubscribe':
                if (typeof instance.setSubscriptionStatus === 'function') instance.setSubscriptionStatus(false);
                break;
                
            case 'permissions_update':
                if (typeof instance.setPermissions === 'function') instance.permissions = data.permissions;
                break;

            case 'element_connection_status':
                if (typeof instance.setStatus === 'function') instance.setStatus(data.status);
                break;

            case 'message_element':
                if (typeof instance.setValue !== 'function' || !data.message) break;

                // Handles simple format for Gauges/Switches: { "value": ... }
                if (typeof data.message.value !== 'undefined') {
                    instance.setValue(data.message.value);
                } 
                // Handles complex format for Charts: { "x": ..., "y": ... }
                else {
                    instance.setValue(data.message);
                }
                break;
            
            case 'message_element_history':
                if (data.messages && typeof instance.loadHistory === 'function') {
                    instance.loadHistory(data.messages);
                }
                break;
            
            case 'error':
                console.error(`Server error for element ${data.element_id}:`, data.description);
                if (typeof instance.showError === 'function') instance.showError(data.description);
                break;

            default:
                 console.warn(`Unknown message type received: ${data.type}`);
        }
    }
    
    function sendMessage(message) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(message));
        } else {
            console.error('WebSocket is not open. Cannot send message:', message);
        }
    }

    window.websocketController = {
        sendMessage: sendMessage
    };

    connect();

})();