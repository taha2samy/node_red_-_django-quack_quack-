class SensorChart {
    constructor(canvasId, details) {
        this.canvasId = canvasId;
        this.details = {
            title: "Chart",
            unit: "",
            maxPoints: 30,
            chartType: 'line',
            datasetOptions: {
                label: (details && details.title) ? details.title : "Sensor Data",
                borderColor: 'rgba(0, 123, 255, 1)',
                backgroundColor: 'rgba(0, 123, 255, 0.2)',
                borderWidth: 2,
                fill: true,
                tension: 0.1
            },
            chartOptions: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        display: true,
                        title: { display: false, text: 'Time' }
                    },
                    y: {
                        beginAtZero: true,
                        title: { display: false, text: 'Value' }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            },
            ...details
        };

        this._permissions = null;

        this.connectionStatusEl = document.getElementById(`${this.canvasId}-connection-status`);
        this.subscriptionStatusEl = document.getElementById(`${this.canvasId}-subscription-status`);
        this.permissionsStatusEl = document.getElementById(`${this.canvasId}-permissions-status`);
        this.valueEl = document.getElementById(`${this.canvasId}-value`);
        this.lastEditAtEl = document.getElementById(`${this.canvasId}-last-edit-at`);
        this.lastEditByEl = document.getElementById(`${this.canvasId}-last-edit-by`);

        const chartConfig = {
            type: this.details.chartType,
            data: {
                labels: [],
                datasets: [{
                    ...this.details.datasetOptions,
                    data: []
                }]
            },
            options: this.details.chartOptions
        };

        const ctx = document.getElementById(this.canvasId).getContext('2d');
        this.chart = new Chart(ctx, chartConfig);

        this.setStatus('disconnected');
        this.setSubscriptionStatus(false);
        this.setPermissions(null);
    }

    addPoint(point) {
        const xValue = point.x || new Date().toLocaleTimeString();
        const yValue = point.y;

        if (typeof yValue === 'undefined') return;

        this.chart.data.labels.push(xValue);
        this.chart.data.datasets[0].data.push(yValue);

        while (this.chart.data.labels.length > this.details.maxPoints) {
            this.chart.data.labels.shift();
            this.chart.data.datasets[0].data.shift();
        }
        
        if (this.valueEl) {
            this.valueEl.textContent = yValue;
        }

        this.chart.update('none');
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
    setValue(message) {
        this.addPoint(message);
    }

    loadHistory(messages) {
        this.chart.data.labels = [];
        this.chart.data.datasets[0].data = [];
        
        messages.forEach(msg => this.addPoint(msg));

        this.chart.update();
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