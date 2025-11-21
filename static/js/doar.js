/* Doar Israel Tracking Functions */
async function refreshDoarTracking(orderId, event) {
    const button = event ? event.target : null;
    const originalText = button ? button.textContent : '';
    
    if (button) {
        button.disabled = true;
        button.textContent = '⏳ Updating...';
    }
    
    try {
        const response = await fetch(`/api/orders/${orderId}/doar-tracking`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            await loadOrders();
            applyFilters();
            if (button) {
                button.textContent = '✓';
                button.style.color = '#28a745';
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.color = '';
                    button.disabled = false;
                }, 2000);
            }
        } else {
            if (button) {
                button.textContent = originalText;
                button.disabled = false;
            }
            alert('Error refreshing Doar Israel tracking: ' + (data.error || 'Failed to fetch tracking information'));
        }
    } catch (error) {
        console.error('Error refreshing Doar Israel tracking:', error);
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }
        alert('Error refreshing Doar Israel tracking. Please try again.');
    }
}

async function refreshAllDoarTracking() {
    const button = document.getElementById('refreshAllDoarBtn');
    const statusSpan = document.getElementById('refreshAllStatus');
    const originalText = button.textContent;
    
    button.disabled = true;
    button.textContent = '⏳ Updating...';
    statusSpan.textContent = 'Please wait...';
    statusSpan.style.color = '#666';
    
    try {
        const response = await fetch('/api/orders/refresh-all-doar', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            statusSpan.textContent = `✓ ${data.message}`;
            statusSpan.style.color = '#28a745';
            
            await loadOrders();
            applyFilters();
            
            // Update last update times
            await updateLastUpdateTimes();
            
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
                statusSpan.textContent = '';
            }, 3000);
        } else {
            statusSpan.textContent = `✗ Error: ${data.error || 'Failed to update orders'}`;
            statusSpan.style.color = '#dc3545';
            button.textContent = originalText;
            button.disabled = false;
            
            setTimeout(() => {
                statusSpan.textContent = '';
            }, 5000);
        }
    } catch (error) {
        console.error('Error refreshing all Doar Israel tracking:', error);
        statusSpan.textContent = '✗ Error: Failed to update orders';
        statusSpan.style.color = '#dc3545';
        button.textContent = originalText;
        button.disabled = false;
        
        setTimeout(() => {
            statusSpan.textContent = '';
        }, 5000);
    }
}

function showDoarEvents(orderId) {
    fetch('/api/orders')
        .then(res => res.json())
        .then(data => {
            const order = data.orders.find(o => o.id === orderId);
            if (order && order.doar_tracking_info && order.doar_tracking_info.events) {
                const events = order.doar_tracking_info.events;
                const modal = document.getElementById('doarEventsModal');
                const content = document.getElementById('doarEventsContent');
                
                if (events.length === 0) {
                    content.innerHTML = '<p>No Doar Israel tracking events available.</p>';
                } else {
                    const deliveryType = order.doar_tracking_info.delivery_type || '';
                    content.innerHTML = `
                        <div class="events-header">
                            <p><strong>Tracking Number:</strong> ${order.tracking_number}</p>
                            <p><strong>Delivery Type:</strong> ${deliveryType || 'N/A'}</p>
                            <p><strong>Total Events:</strong> ${events.length}</p>
                        </div>
                        <div class="events-timeline">
                            ${events.map((event, index) => `
                                <div class="event-item">
                                    <div class="event-date">${event.date || 'Date not available'}</div>
                                    <div class="event-content">
                                        ${event.category ? `<div class="event-status">${event.category}</div>` : ''}
                                        ${event.branch ? `<div class="event-branch">${event.branch}${event.city ? ', ' + event.city : ''}</div>` : ''}
                                        <div class="event-description">${event.description}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
                
                modal.style.display = 'flex';
            } else {
                alert('No Doar Israel tracking information available for this order');
            }
        })
        .catch(error => {
            console.error('Error loading Doar Israel events:', error);
            alert('Error loading Doar Israel tracking events');
        });
}

function closeDoarEventsModal() {
    document.getElementById('doarEventsModal').style.display = 'none';
}

