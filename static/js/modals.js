/* Modal Management Functions */
function openAddOrderModal() {
    const modal = document.getElementById('addOrderModal');
    modal.style.display = 'flex';
    // Clear previous values
    document.getElementById('productUrl').value = '';
    document.getElementById('trackingNumber').value = '';
    document.getElementById('addOrderAlert').innerHTML = '';
    // Focus on URL input
    setTimeout(() => document.getElementById('productUrl').focus(), 100);
}

function closeAddOrderModal() {
    document.getElementById('addOrderModal').style.display = 'none';
    document.getElementById('addOrderAlert').innerHTML = '';
}

function openImportModal() {
    const modal = document.getElementById('importModal');
    modal.style.display = 'flex';
    // Clear previous values
    document.getElementById('curlCommand').value = '';
    document.getElementById('importAlert').innerHTML = '';
    document.getElementById('importResults').style.display = 'none';
    // Focus on textarea
    setTimeout(() => document.getElementById('curlCommand').focus(), 100);
}

function closeImportModal() {
    document.getElementById('importModal').style.display = 'none';
    document.getElementById('importAlert').innerHTML = '';
    document.getElementById('importResults').style.display = 'none';
}

function editOrder(orderId) {
    currentEditId = orderId;
    const modal = document.getElementById('editModal');
    modal.style.display = 'flex';
    
    // Load current order data
    fetch('/api/orders')
        .then(res => res.json())
        .then(data => {
            const order = data.orders.find(o => o.id === orderId);
            if (order) {
                document.getElementById('editProductTitle').value = order.product_title || '';
                document.getElementById('editTrackingNumber').value = order.tracking_number || '';
                document.getElementById('editProductImage').value = order.product_image || '';
            }
        });
}

function closeModal() {
    document.getElementById('editModal').style.display = 'none';
    document.getElementById('modalAlert').innerHTML = '';
    currentEditId = null;
}

function showEvents(orderId) {
    // Load current order data
    fetch('/api/orders')
        .then(res => res.json())
        .then(data => {
            const order = data.orders.find(o => o.id === orderId);
            if (order && order.tracking_info && order.tracking_info.events) {
                const events = order.tracking_info.events;
                const modal = document.getElementById('eventsModal');
                const content = document.getElementById('eventsContent');
                
                if (events.length === 0) {
                    content.innerHTML = '<p>No tracking events available.</p>';
                } else {
                    content.innerHTML = `
                        <div class="events-header">
                            <p><strong>Tracking Number:</strong> ${order.tracking_number}</p>
                            <p><strong>Total Events:</strong> ${events.length}</p>
                        </div>
                        <div class="events-timeline">
                            ${events.map((event, index) => `
                                <div class="event-item">
                                    <div class="event-date">${event.date || 'Date not available'}</div>
                                    <div class="event-content">
                                        ${event.nodeDesc ? `<div class="event-status">${event.nodeDesc}</div>` : ''}
                                        <div class="event-description">${event.description}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
                
                modal.style.display = 'flex';
            }
        })
        .catch(error => {
            console.error('Error loading events:', error);
            alert('Error loading tracking events');
        });
}

function closeEventsModal() {
    document.getElementById('eventsModal').style.display = 'none';
}

function closeSubItemsModal() {
    document.getElementById('subItemsModal').style.display = 'none';
}

function openDoarApiKeyModal() {
    const modal = document.getElementById('doarApiKeyModal');
    modal.style.display = 'flex';
    document.getElementById('doarApiKey').value = '';
    document.getElementById('doarApiKeyAlert').innerHTML = '';
    
    // Load current API key status
    fetch('/api/config/doar-api-key')
        .then(res => res.json())
        .then(data => {
            const currentKeyInfo = document.getElementById('currentApiKeyInfo');
            const currentKeyMasked = document.getElementById('currentApiKeyMasked');
            if (data.api_key_set) {
                currentKeyInfo.style.display = 'block';
                currentKeyMasked.textContent = data.masked_key;
            } else {
                currentKeyInfo.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error loading API key status:', error);
        });
    
    setTimeout(() => document.getElementById('doarApiKey').focus(), 100);
}

function closeDoarApiKeyModal() {
    document.getElementById('doarApiKeyModal').style.display = 'none';
    document.getElementById('doarApiKeyAlert').innerHTML = '';
}

async function saveDoarApiKey() {
    const apiKey = document.getElementById('doarApiKey').value.trim();
    const saveBtn = document.getElementById('saveDoarApiKeyBtn');
    const alertDiv = document.getElementById('doarApiKeyAlert');
    
    if (!apiKey) {
        alertDiv.innerHTML = '<div class="alert alert-error">Please enter an API key</div>';
        return;
    }
    
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    alertDiv.innerHTML = '<div class="alert alert-info">Saving API key...</div>';
    
    try {
        const response = await fetch('/api/config/doar-api-key', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ api_key: apiKey })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alertDiv.innerHTML = '<div class="alert alert-success">API key saved successfully!</div>';
            setTimeout(() => {
                closeDoarApiKeyModal();
            }, 1500);
        } else {
            alertDiv.innerHTML = '<div class="alert alert-error">Error: ' + (data.error || 'Failed to save API key') + '</div>';
        }
    } catch (error) {
        console.error('Error saving API key:', error);
        alertDiv.innerHTML = '<div class="alert alert-error">Error saving API key. Please try again.</div>';
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save API Key';
    }
}

function openDoarTracking(trackingNumber) {
    if (!trackingNumber) {
        alert('Tracking number not available for this order.');
        return;
    }
    
    const trimmedTracking = trackingNumber.trim();
    if (!trimmedTracking) {
        alert('Tracking number not available for this order.');
        return;
    }
    
    const url = `https://doar.israelpost.co.il/deliverytracking?itemcode=${encodeURIComponent(trimmedTracking)}`;
    window.open(url, '_blank', 'noopener');
}

