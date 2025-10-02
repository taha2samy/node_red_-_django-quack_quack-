class SwitchButton {
    constructor(domId, elementId, details) {
        this.domId = domId;
        this.elementId = elementId;
        console.log(this.details);
        this.details = {
            title: "Switch",
            text_on: "ON",
            text_off: "OFF",
            ...details
        };
        console.log(this.details);
        this._permissions = null;

        this.inputElement = document.getElementById(`${this.domId}-input`);
        this.labelElement = document.getElementById(`${this.domId}-label`);
        this.connectionStatusEl = document.getElementById(`${this.domId}-connection-status`);
        this.subscriptionStatusEl = document.getElementById(`${this.domId}-subscription-status`);
        this.permissionsStatusEl = document.getElementById(`${this.domId}-permissions-status`);

        if (this.inputElement) {
            this.inputElement.addEventListener('change', this.action.bind(this));
        }

        this.setValue(0);
        this.setStatus('disconnected');
        this.setSubscriptionStatus(false);
        this.setPermissions(null);
    }

    action() {
        if (!window.websocketController) {
            console.error("WebSocket Controller is not available.");
            return;
        }
        window.websocketController.sendMessage({
            type: 'message_element',
            element_id: this.elementId,
            message: { value: this.inputElement.checked ? 1 : 0 }
        });
    }

    setValue(value) {
        if (!this.inputElement || !this.labelElement) return;
        
        const isChecked = value === 1 || value === true || String(value).toLowerCase() === 'on';
        
        this.inputElement.checked = isChecked;
        this.labelElement.textContent = isChecked ? this.details.text_on : this.details.text_off;
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
        if (this.permissionsStatusEl) {
            const statusText = this.permissionsStatusEl.querySelector('.status-text');
            this.permissionsStatusEl.classList.remove('permissions-rc', 'permissions-r');

            if (permValue === 'RC') {
                this.permissionsStatusEl.classList.add('permissions-rc');
                statusText.textContent = 'Read/Write';
            } else if (permValue === 'R') {
                this.permissionsStatusEl.classList.add('permissions-r');
                statusText.textContent = 'Read-Only';
            } else {
                statusText.textContent = 'None';
            }
        }

        if (this.inputElement) {
            this.inputElement.disabled = (permValue !== 'RC');
        }
    }
}