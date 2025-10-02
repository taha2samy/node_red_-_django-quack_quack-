class SensorGauge {
    constructor(canvasId, details) {
        this.canvasId = canvasId;
        this.details = details || {};
        this._permissions = null;

        // Cache DOM element references
        this.connectionStatusEl = document.getElementById(`${this.canvasId}-connection-status`);
        this.subscriptionStatusEl = document.getElementById(`${this.canvasId}-subscription-status`);
        this.permissionsStatusEl = document.getElementById(`${this.canvasId}-permissions-status`);
        this.valueEl = document.getElementById(`${this.canvasId}-value`);

        // --- The Robust Core Logic ---
        // 1. Start with the flexible details object from the database.
        const gaugeOptions = { ...this.details };

        // 2. Now, guarantee that essential properties exist with valid defaults
        //    if they weren't provided in the details object.
        gaugeOptions.renderTo = this.canvasId;
        gaugeOptions.width = this.details.width || 200;
        gaugeOptions.height = this.details.height || 200;
        gaugeOptions.minValue = this.details.minValue || 0;
        gaugeOptions.maxValue = this.details.maxValue || 100;
        gaugeOptions.units = this.details.units || "Value";

        // 3. Initialize the gauge with the safe and complete options.
        this.gauge = new RadialGauge(gaugeOptions).draw();

        // Set initial UI state
        this.setStatus('disconnected');
        this.setSubscriptionStatus(false);
        this.setPermissions(null);
    }

    setValue(value) {
        
        const numericValue = Number(value);
        if (isNaN(numericValue)) {
            return;
        }

        const decimals = this.details.valueDecimals === 0 ? 0 : (this.details.valueDecimals || 2);

        this.gauge.value = numericValue;
        
        if (this.valueEl) {
            this.valueEl.textContent = numericValue.toFixed(decimals);
        }
    }
    
    setStatus(status) {
        if (!this.connectionStatusEl) return;
        const statusText = this.connectionStatusEl.querySelector('.status-text');
        this.connectionStatusEl.classList.remove('status-active', 'status-inactive');

        if (status === 'connected') {
            this.connectionStatusEl.classList.add('status-active');
            statusText.textContent = "Online";
        } else {
            this.connectionStatusEl.classList.add('status-inactive');
            statusText.textContent = "Offline";
        }
    }

    setSubscriptionStatus(isSubscribed) {
        if (!this.subscriptionStatusEl) return;
        const icon = this.subscriptionStatusEl.querySelector('i');
        const statusText = this.subscriptionStatusEl.querySelector('.status-text');
        
        this.subscriptionStatusEl.classList.toggle('subscribed', isSubscribed);
        icon.className = isSubscribed ? 'fas fa-bell' : 'far fa-bell-slash';
        statusText.textContent = isSubscribed ? 'Subscribed' : 'Unsubscribed';

        if (!isSubscribed) {
            this.setPermissions(null);
        }
    }

    get permissions() {
        return this._permissions;
    }
    
    set permissions(value) {
        this._permissions = value;
        this.setPermissions(value);
    }
    
    setPermissions(permValue) {
        if (!this.permissionsStatusEl) return;
        const statusText = this.permissionsStatusEl.querySelector('.status-text');
        
        this.permissionsStatusEl.classList.remove('permissions-rc', 'permissions-r');

        if (permValue === 'RC') {
            this.permissionsStatusEl.classList.add('permissions-rc');
            statusText.textContent = 'Read/Write';
        } else if (permValue === 'R') {
            this.permissionsStatusEl.classList.add('permissions-r');
            statusText.textContent = 'Read-Only';
        } else {
            this.permissionsStatusEl.classList.add('permissions-r');
            statusText.textContent = 'None';
        }
    }
}