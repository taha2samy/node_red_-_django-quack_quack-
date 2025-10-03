class SwitchButton {
    constructor(domId, elementId, details) {
        this.domId = domId;
        this.elementId = elementId;
        this.details = {
            title: "Switch",
            text_on: "ON",
            text_off: "OFF",
            ...details
        };
        this._permissions = null;

        this.inputElement = document.getElementById(`${this.domId}-input`);
        this.labelElement = document.getElementById(`${this.domId}-label`);
        this.connectionStatusEl = document.getElementById(`${this.domId}-connection-status`);
        this.subscriptionStatusEl = document.getElementById(`${this.domId}-subscription-status`);
        this.permissionsStatusEl = document.getElementById(`${this.domId}-permissions-status`);
        this.lastEditAtEl = document.getElementById(`${this.domId}-last-edit-at`);
        this.lastEditByEl = document.getElementById(`${this.domId}-last-edit-by`);

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
    setLastEditAt(date) {
        if (!this.lastEditAtEl) return;

        this.lastEditAtEl.querySelector('.status-text').textContent = date || 'None';

        const { iconColor, backgroundColor } = this.getRandomCoordinatedColors();

        const iconEl = this.lastEditAtEl.querySelector('.fas.fa-clock');

        if (iconEl) {
            iconEl.style.color = iconColor;
        }

        this.lastEditAtEl.style.backgroundColor = backgroundColor;
        this.lastEditAtEl.style.padding = '2px 8px';
        this.lastEditAtEl.style.borderRadius = '12px';
        this.lastEditAtEl.style.transition = 'background-color 0.3s ease'

    }

    getRandomCoordinatedColors() {
        const hue = Math.floor(Math.random() * 360);
        const iconColor = `hsl(${hue}, 90%, 55%)`;
        const backgroundColor = `hsl(${hue}, 100%, 95%)`;
        return { iconColor, backgroundColor };
    }

    setLastEditBy(user) {
        if (!this.lastEditByEl) return;
        if (this.lastEditByEl.querySelector('.status-text').textContent === user) return;
        this.lastEditByEl.querySelector('.status-text').textContent = user || 'None';

        const { iconColor, backgroundColor } = this.getRandomCoordinatedColors();

        const iconEl = this.lastEditByEl.querySelector('.fas.fa-pencil-alt');

        if (iconEl) {
            iconEl.style.color = iconColor;
        }

        this.lastEditByEl.style.backgroundColor = backgroundColor;
        this.lastEditByEl.style.padding = '2px 8px';
        this.lastEditByEl.style.borderRadius = '12px';
        this.lastEditAtEl.style.transition = 'background-color 0.3s ease'
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