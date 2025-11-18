let currentEditId = null;
let isLoadingOrders = false;
let allOrders = []; // Store all orders for filtering/sorting

// Load orders on page load
window.onload = function() {
    loadOrders();
};

async function loadOrders() {
    // Prevent multiple simultaneous loads
    if (isLoadingOrders) {
        return;
    }
    
    isLoadingOrders = true;
    try {
        const response = await fetch('/api/orders');
        const data = await response.json();
        allOrders = data.orders; // Store all orders
        updateTotalOrdersCount(); // Update total counter
        applyFilters(); // Apply current filters
    } catch (error) {
        console.error('Error loading orders:', error);
    } finally {
        isLoadingOrders = false;
    }
}

function updateTotalOrdersCount() {
    const totalCountElement = document.getElementById('totalOrdersCount');
    if (totalCountElement) {
        totalCountElement.textContent = allOrders.length;
    }
}

function parsePrice(priceString) {
    if (!priceString) return null;
    
    // Extract numeric value from price string
    // Handles formats like: "US $42.57", "$42.57", "42.57", "US $42|42|57", etc.
    const match = priceString.match(/[\d,]+\.?\d*/);
    if (match) {
        // Remove commas and convert to number
        return parseFloat(match[0].replace(/,/g, ''));
    }
    return null;
}

function comparePrices(priceA, priceB, ascending) {
    const numA = parsePrice(priceA);
    const numB = parsePrice(priceB);
    
    // Put orders without prices at the end
    if (numA === null && numB === null) return 0;
    if (numA === null) return 1;
    if (numB === null) return -1;
    
    // Compare numeric values
    const diff = numA - numB;
    return ascending ? diff : -diff;
}

function formatOrderDate(orderDate, addedDate) {
    if (orderDate) {
        // If it's already in a readable format like "Nov 11, 2025", use it as-is
        if (orderDate.includes(',') || orderDate.match(/[A-Za-z]{3}/)) {
            return orderDate;
        }
        // If it's in ISO format or date-only format, format it nicely
        try {
            const date = new Date(orderDate);
            if (!isNaN(date.getTime())) {
                return date.toLocaleDateString('en-US', { 
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric' 
                });
            }
        } catch (e) {
            // If parsing fails, return as-is
            return orderDate;
        }
        return orderDate;
    }
    
    // Fallback to added_date
    if (addedDate) {
        try {
            const date = new Date(addedDate);
            if (!isNaN(date.getTime())) {
                return date.toLocaleDateString('en-US', { 
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric' 
                });
            }
        } catch (e) {
            // If parsing fails, try to extract date part
            if (addedDate.includes('T')) {
                return addedDate.split('T')[0];
            }
            return addedDate;
        }
    }
    
    return 'N/A';
}

function applyFilters() {
    let filtered = [...allOrders];
    
    // Filter by status
    const statusFilter = document.getElementById('statusFilter').value;
    if (statusFilter) {
        filtered = filtered.filter(order => {
            const trackingInfo = order.tracking_info || {};
            const status = trackingInfo.status || order.status || 'Pending';
            return status.toLowerCase() === statusFilter.toLowerCase();
        });
    }
    
    // Filter by search text
    const searchText = document.getElementById('searchFilter').value.toLowerCase().trim();
    if (searchText) {
        filtered = filtered.filter(order => {
            const productTitle = (order.product_title || '').toLowerCase();
            const trackingNumber = (order.tracking_number || '').toLowerCase();
            const productId = (order.product_id || '').toLowerCase();
            return productTitle.includes(searchText) || 
                   trackingNumber.includes(searchText) || 
                   productId.includes(searchText);
        });
    }
    
    // Sort orders
    const sortBy = document.getElementById('sortBy').value;
    filtered.sort((a, b) => {
        switch(sortBy) {
            case 'added_date_desc':
                return new Date(b.added_date || 0) - new Date(a.added_date || 0);
            case 'added_date_asc':
                return new Date(a.added_date || 0) - new Date(b.added_date || 0);
            case 'order_date_desc':
                const aOrderDate = a.order_date || a.added_date || '';
                const bOrderDate = b.order_date || b.added_date || '';
                return new Date(bOrderDate) - new Date(aOrderDate);
            case 'order_date_asc':
                const aOrderDateAsc = a.order_date || a.added_date || '';
                const bOrderDateAsc = b.order_date || b.added_date || '';
                return new Date(aOrderDateAsc) - new Date(bOrderDateAsc);
            case 'last_update_desc':
                const aLastUpdate = (a.tracking_info || {}).last_update_date || '';
                const bLastUpdate = (b.tracking_info || {}).last_update_date || '';
                if (!aLastUpdate && !bLastUpdate) return 0;
                if (!aLastUpdate) return 1;
                if (!bLastUpdate) return -1;
                return new Date(bLastUpdate) - new Date(aLastUpdate);
            case 'last_update_asc':
                const aLastUpdateAsc = (a.tracking_info || {}).last_update_date || '';
                const bLastUpdateAsc = (b.tracking_info || {}).last_update_date || '';
                if (!aLastUpdateAsc && !bLastUpdateAsc) return 0;
                if (!aLastUpdateAsc) return 1;
                if (!bLastUpdateAsc) return -1;
                return new Date(aLastUpdateAsc) - new Date(bLastUpdateAsc);
            case 'product_title_asc':
                return (a.product_title || '').localeCompare(b.product_title || '');
            case 'product_title_desc':
                return (b.product_title || '').localeCompare(a.product_title || '');
            case 'tracking_number_asc':
                const aTracking = (a.tracking_number || '').toLowerCase();
                const bTracking = (b.tracking_number || '').toLowerCase();
                // Put orders without tracking numbers at the end
                if (!aTracking && !bTracking) return 0;
                if (!aTracking) return 1;
                if (!bTracking) return -1;
                return aTracking.localeCompare(bTracking);
            case 'tracking_number_desc':
                const aTrackingDesc = (a.tracking_number || '').toLowerCase();
                const bTrackingDesc = (b.tracking_number || '').toLowerCase();
                // Put orders without tracking numbers at the end
                if (!aTrackingDesc && !bTrackingDesc) return 0;
                if (!aTrackingDesc) return 1;
                if (!bTrackingDesc) return -1;
                return bTrackingDesc.localeCompare(aTrackingDesc);
            case 'price_asc':
                return comparePrices(a.price, b.price, true);
            case 'price_desc':
                return comparePrices(a.price, b.price, false);
            case 'status_asc':
                const aStatus = ((a.tracking_info || {}).status || a.status || 'Pending').toLowerCase();
                const bStatus = ((b.tracking_info || {}).status || b.status || 'Pending').toLowerCase();
                return aStatus.localeCompare(bStatus);
            case 'doar_status_asc':
                const aDoarStatus = ((a.doar_tracking_info || {}).status || 'N/A').toLowerCase();
                const bDoarStatus = ((b.doar_tracking_info || {}).status || 'N/A').toLowerCase();
                // Put N/A at the end
                if (aDoarStatus === 'n/a' && bDoarStatus === 'n/a') return 0;
                if (aDoarStatus === 'n/a') return 1;
                if (bDoarStatus === 'n/a') return -1;
                return aDoarStatus.localeCompare(bDoarStatus);
            case 'doar_status_desc':
                const aDoarStatusDesc = ((a.doar_tracking_info || {}).status || 'N/A').toLowerCase();
                const bDoarStatusDesc = ((b.doar_tracking_info || {}).status || 'N/A').toLowerCase();
                // Put N/A at the end
                if (aDoarStatusDesc === 'n/a' && bDoarStatusDesc === 'n/a') return 0;
                if (aDoarStatusDesc === 'n/a') return 1;
                if (bDoarStatusDesc === 'n/a') return -1;
                return bDoarStatusDesc.localeCompare(aDoarStatusDesc);
            default:
                return 0;
        }
    });
    
    // Update filter count
    const filterCount = document.getElementById('filterCount');
    if (filtered.length === allOrders.length) {
        filterCount.textContent = `Showing all ${allOrders.length} orders`;
    } else {
        filterCount.textContent = `Showing ${filtered.length} of ${allOrders.length} orders`;
    }
    
    displayOrders(filtered);
}

function clearFilters() {
    document.getElementById('statusFilter').value = '';
    document.getElementById('sortBy').value = 'added_date_desc';
    document.getElementById('searchFilter').value = '';
    applyFilters();
}

function displayOrders(orders) {
    const tbody = document.getElementById('ordersTableBody');
    
    // Use requestAnimationFrame to batch DOM updates and reduce flicker
    requestAnimationFrame(() => {
        if (orders.length === 0) {
            // Check if filters are active
            const hasActiveFilters = document.getElementById('statusFilter').value || 
                                    document.getElementById('searchFilter').value.trim();
            const emptyMessage = hasActiveFilters 
                ? 'No orders match your filters. Try adjusting your search criteria.'
                : 'No orders yet. Add an order to get started!';
            
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="empty-state">
                        <div>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                                <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
                            </svg>
                            <p>${emptyMessage}</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        const newHTML = orders.map(order => {
            const trackingInfo = order.tracking_info || {};
            const trackingStatus = trackingInfo.status || order.status || 'Pending';
            const trackingEvents = trackingInfo.events || [];
            const hasTracking = order.tracking_number && order.tracking_number.trim() !== '';
            const latestStanderdDesc = trackingInfo.latest_standerd_desc || '';
            
            // Doar Israel tracking info
            const doarTrackingInfo = order.doar_tracking_info || {};
            const doarStatus = doarTrackingInfo.status || 'N/A';
            const doarStatusField = doarTrackingInfo.status_field || '';
            const doarEvents = doarTrackingInfo.events || [];
            const doarDeliveryType = doarTrackingInfo.delivery_type || '';
            
            // Use placeholder if no image or if image URL looks invalid
            const imageUrl = order.product_image || '';
            const hasValidImage = imageUrl && (
                imageUrl.includes('.jpg') || 
                imageUrl.includes('.jpeg') || 
                imageUrl.includes('.png') || 
                imageUrl.includes('.webp') ||
                imageUrl.includes('.avif') ||
                imageUrl.includes('alicdn.com') ||
                imageUrl.includes('aliexpress-media.com') ||
                imageUrl.startsWith('/static/images/products/')
            );
            
            // Use local image if available, otherwise use proxy for AliExpress images
            let displayImage = hasValidImage ? imageUrl : 'https://via.placeholder.com/80';
            
            // If it's already a local path, use it directly
            if (imageUrl && imageUrl.startsWith('/static/images/products/')) {
                displayImage = imageUrl;
            }
            // If it's an AliExpress CDN image, use proxy endpoint (which will also save it locally)
            else if (imageUrl && (imageUrl.includes('alicdn.com') || imageUrl.includes('aliexpress-media.com'))) {
                // Use optimized jpg format (more reliable, avif might be blocked by CORS)
                if (imageUrl.includes('_220x220q75.jpg') && !imageUrl.includes('.avif')) {
                    // Use the optimized jpg through proxy
                    displayImage = '/api/image-proxy?url=' + encodeURIComponent(imageUrl) + (order.product_id ? '&product_id=' + encodeURIComponent(order.product_id) : '');
                } else if (imageUrl.endsWith('.jpg') && !imageUrl.includes('_')) {
                    // Convert plain jpg to optimized format and use proxy
                    const optimizedUrl = imageUrl.replace('.jpg', '_220x220q75.jpg');
                    displayImage = '/api/image-proxy?url=' + encodeURIComponent(optimizedUrl) + (order.product_id ? '&product_id=' + encodeURIComponent(order.product_id) : '');
                } else {
                    // Use proxy for any other AliExpress image (including .avif)
                    displayImage = '/api/image-proxy?url=' + encodeURIComponent(imageUrl) + (order.product_id ? '&product_id=' + encodeURIComponent(order.product_id) : '');
                }
            }
            
            return `
            <tr>
                <td>
                    <img src="${displayImage}" 
                         alt="${order.product_title}" 
                         class="product-image"
                         data-original-src="${imageUrl || ''}"
                         onerror="handleImageError(this)">
                </td>
                <td>
                    <div class="product-info">
                        <div>
                            <div class="product-title">
                                <a href="${order.product_url}" target="_blank">${order.product_title}</a>
                                ${order.sub_items && order.sub_items.length > 0 ? `
                                    <button onclick="showSubItems(${order.id})" class="btn-sub-items" title="View ${order.sub_items.length} item(s) in this order">
                                        📦 ${order.sub_items.length} item${order.sub_items.length > 1 ? 's' : ''}
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </td>
                <td>
                    <div class="order-date-cell">
                        ${formatOrderDate(order.order_date, order.added_date)}
                    </div>
                </td>
                <td>
                    <div class="price-cell">
                        ${order.price ? `<span class="price-text">${order.price}</span>` : '<span class="no-price">N/A</span>'}
                    </div>
                </td>
                <td>
                    <div class="tracking-cell">
                        ${hasTracking ? `
                            <span class="tracking-number">${order.tracking_number}</span>
                            ${trackingInfo.carrier ? `<small class="carrier-name">${trackingInfo.carrier}</small>` : ''}
                        ` : '<span class="tracking-number">N/A</span>'}
                    </div>
                </td>
                <td>
                    <div class="status-cell">
                        <span class="status-badge status-${trackingStatus.toLowerCase().replace(/\s+/g, '-')}">${trackingStatus}</span>
                    </div>
                </td>
                <td>
                    <div class="latest-update-cell">
                        ${latestStanderdDesc ? `
                            <span class="latest-update-text" title="${latestStanderdDesc}">${latestStanderdDesc.length > 50 ? latestStanderdDesc.substring(0, 50) + '...' : latestStanderdDesc}</span>
                        ` : '<span class="no-update">No update</span>'}
                        ${hasTracking ? `
                            <div style="display: flex; gap: 4px; margin-top: 4px; flex-wrap: wrap;">
                                ${trackingEvents.length > 0 ? `<button class="btn-small btn-events" onclick="showEvents(${order.id})" title="View all events" style="font-size: 10px; padding: 2px 6px;">📦 Events</button>` : ''}
                                <button class="btn-small btn-tracking" onclick="refreshTracking(${order.id}, event)" title="Refresh tracking" style="font-size: 10px; padding: 2px 6px;">🔄 Update</button>
                            </div>
                        ` : ''}
                    </div>
                </td>
                <td>
                    <div class="doar-status-cell">
                        ${doarStatus !== 'N/A' ? `
                            <span class="status-badge status-${doarStatus.toLowerCase().replace(/\s+/g, '-')}" title="${doarDeliveryType ? 'Delivery: ' + doarDeliveryType : ''}">${doarStatus}</span>
                            ${doarStatusField ? `<div style="font-size: 11px; color: #666; margin-top: 4px;">${doarStatusField}</div>` : ''}
                        ` : '<span class="no-update">N/A</span>'}
                        ${hasTracking ? `
                            <div style="display: flex; gap: 4px; margin-top: 4px; flex-wrap: wrap;">
                                ${doarEvents.length > 0 ? `<button class="btn-small btn-events" onclick="showDoarEvents(${order.id})" title="View Doar Israel tracking history" style="font-size: 10px; padding: 2px 6px;">📦 Events</button>` : ''}
                                <button class="btn-small btn-tracking" onclick="refreshDoarTracking(${order.id}, event)" title="Refresh Doar Israel tracking" style="font-size: 10px; padding: 2px 6px;">🔄 Update</button>
                            </div>
                        ` : ''}
                    </div>
                </td>
                <td>
                    <div class="last-update-cell">
                        ${trackingInfo.last_update_date ? `
                            <span class="last-update-date" title="${trackingInfo.last_update_date}">${trackingInfo.last_update_date}</span>
                        ` : '<span class="no-update">N/A</span>'}
                    </div>
                </td>
                <td>
                    <div class="action-buttons">
                        ${hasTracking ? `<button class="btn-small btn-doar" onclick="openDoarTracking('${(order.tracking_number || '').replace(/'/g, "\\'")}')" title="Open in Doar Israel"><img src="/static/images/Doar_logo_170x92.png" alt="Doar Israel" class="btn-doar-img"></button>` : ''}
                        <button class="btn-small" onclick="editOrder(${order.id})">Edit</button>
                        <button class="btn-small btn-delete" onclick="deleteOrder(${order.id})">Delete</button>
                    </div>
                </td>
            </tr>
            `;
        }).join('');
        
        // Update DOM in one operation to reduce flicker
        tbody.innerHTML = newHTML;
    });
}

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

async function addOrder() {
    const url = document.getElementById('productUrl').value.trim();
    const trackingNumber = document.getElementById('trackingNumber').value.trim();
    const addButton = document.querySelector('button[onclick="addOrder()"]');
    const alertDiv = document.getElementById('addOrderAlert');

    if (!url) {
        alertDiv.innerHTML = '<div class="alert alert-error">Please enter an AliExpress URL</div>';
        return;
    }

    // Disable button and show loading state
    if (addButton) {
        addButton.disabled = true;
        const originalText = addButton.textContent;
        addButton.textContent = 'Adding...';
        alertDiv.innerHTML = '<div class="alert alert-info">Adding order, please wait...</div>';
        
        try {
            const response = await fetch('/api/orders', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    tracking_number: trackingNumber
                })
            });

            const data = await response.json();
            
                   if (response.ok) {
                       alertDiv.innerHTML = '<div class="alert alert-success">Order added successfully!</div>';
                       // Wait a bit before reloading to ensure server has saved
                       await new Promise(resolve => setTimeout(resolve, 500));
                       await loadOrders();
                       // Clear filters after adding new order
                       clearFilters();
                       // Close modal after short delay
                       setTimeout(() => {
                           closeAddOrderModal();
                       }, 1000);
                   } else {
                alertDiv.innerHTML = '<div class="alert alert-error">Error: ' + (data.error || 'Failed to add order') + '</div>';
            }
        } catch (error) {
            console.error('Error adding order:', error);
            alertDiv.innerHTML = '<div class="alert alert-error">Error adding order. Please try again.</div>';
        } finally {
            // Re-enable button
            if (addButton) {
                addButton.disabled = false;
                addButton.textContent = originalText;
            }
        }
    }
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

async function saveOrder() {
    if (!currentEditId) return;

    const productTitle = document.getElementById('editProductTitle').value.trim();
    const trackingNumber = document.getElementById('editTrackingNumber').value.trim();
    const productImage = document.getElementById('editProductImage').value.trim();

    try {
        const response = await fetch(`/api/orders/${currentEditId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                product_title: productTitle,
                tracking_number: trackingNumber,
                product_image: productImage
            })
        });

        const data = await response.json();
        
               if (response.ok) {
                   document.getElementById('modalAlert').innerHTML = 
                       '<div class="alert alert-success">Order updated successfully!</div>';
                   setTimeout(async () => {
                       closeModal();
                       await loadOrders();
                       applyFilters(); // Reapply filters after update
                   }, 1000);
               } else {
            document.getElementById('modalAlert').innerHTML = 
                '<div class="alert alert-error">Error: ' + (data.error || 'Failed to update order') + '</div>';
        }
    } catch (error) {
        console.error('Error updating order:', error);
        document.getElementById('modalAlert').innerHTML = 
            '<div class="alert alert-error">Error updating order. Please try again.</div>';
    }
}

async function deleteOrder(orderId) {
    if (!confirm('Are you sure you want to delete this order?')) {
        return;
    }

    try {
        const response = await fetch(`/api/orders/${orderId}`, {
            method: 'DELETE'
        });

           if (response.ok) {
                   await loadOrders();
                   applyFilters(); // Reapply filters after delete
               } else {
            alert('Error deleting order');
        }
    } catch (error) {
        console.error('Error deleting order:', error);
        alert('Error deleting order. Please try again.');
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

async function refreshTracking(orderId, event) {
    const button = event ? event.target : null;
    const originalText = button ? button.textContent : '';
    
    if (button) {
        button.disabled = true;
        button.textContent = '⏳ Updating...';
    }
    
    try {
        const response = await fetch(`/api/orders/${orderId}/tracking`, {
            method: 'POST'
        });

        const data = await response.json();
        
               if (response.ok && data.success) {
                   await loadOrders();
                   applyFilters(); // Reapply filters after refresh
                   // Show a brief success message
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
            alert('Error refreshing tracking: ' + (data.error || 'Failed to fetch tracking information'));
        }
    } catch (error) {
        console.error('Error refreshing tracking:', error);
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }
        alert('Error refreshing tracking. Please try again.');
    }
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

function showSubItems(orderId) {
    // Load current order data
    fetch('/api/orders')
        .then(res => res.json())
        .then(data => {
            const order = data.orders.find(o => o.id === orderId);
            if (order && order.sub_items && order.sub_items.length > 0) {
                const subItems = order.sub_items;
                const modal = document.getElementById('subItemsModal');
                const content = document.getElementById('subItemsContent');
                
                content.innerHTML = `
                    <div style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                        <p style="margin: 5px 0;"><strong>Order ID:</strong> ${order.order_id || 'N/A'}</p>
                        <p style="margin: 5px 0;"><strong>Order Date:</strong> ${formatOrderDate(order.order_date, order.added_date)}</p>
                        <p style="margin: 5px 0;"><strong>Total Items:</strong> ${subItems.length}</p>
                        ${order.price ? `<p style="margin: 5px 0;"><strong>Total Price:</strong> ${order.price}</p>` : ''}
                    </div>
                    <div class="sub-items-grid">
                        ${subItems.map((item, index) => {
                            // Get image URL (use proxy if needed)
                            let itemImage = item.product_image || 'https://via.placeholder.com/120';
                            // If it's already a local path, use it directly
                            if (itemImage && itemImage.startsWith('/static/images/products/')) {
                                // Use local image as-is
                            } else if (itemImage && (itemImage.includes('alicdn.com') || itemImage.includes('aliexpress-media.com'))) {
                                // Use proxy for AliExpress CDN images
                                itemImage = '/api/image-proxy?url=' + encodeURIComponent(itemImage) + (item.product_id ? '&product_id=' + encodeURIComponent(item.product_id) : '');
                            } else if (itemImage && !itemImage.startsWith('http') && !itemImage.startsWith('/static')) {
                                itemImage = 'https://via.placeholder.com/120';
                            }
                            
                            return `
                                <div class="sub-item-card">
                                    <div class="sub-item-image">
                                        <img src="${itemImage}" 
                                             alt="${item.product_title}" 
                                             onerror="this.src='https://via.placeholder.com/120'">
                                    </div>
                                    <div class="sub-item-info">
                                        <h4><a href="${item.product_url}" target="_blank">${item.product_title}</a></h4>
                                        <p class="sub-item-price">${item.price || 'N/A'}</p>
                                        <p class="sub-item-id">Product ID: ${item.product_id}</p>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
                
                modal.style.display = 'flex';
            } else {
                alert('No sub-items found for this order');
            }
        })
        .catch(error => {
            console.error('Error loading sub-items:', error);
            alert('Error loading sub-items');
        });
}

function closeSubItemsModal() {
    document.getElementById('subItemsModal').style.display = 'none';
}

function handleImageError(img) {
    // Prevent infinite loop - only try fallback once
    if (img.dataset.fallbackTried === 'true') {
        return;
    }
    
    img.dataset.fallbackTried = 'true';
    const originalSrc = img.dataset.originalSrc || img.src || '';
    // add "_220x220q75.jpg_.avif"
    // const avifSrc = originalSrc.replace('.jpg', '.jpg_220x220q75.jpg_.avif');
    img.src = originalSrc;
    // Final fallback to placeholder
    // img.src = 'https://via.placeholder.com/80';
    img.style.opacity = '1.0'; // Make it clear it's a placeholder
}

async function refreshAllTracking() {
    const button = document.getElementById('refreshAllBtn');
    const statusSpan = document.getElementById('refreshAllStatus');
    const originalText = button.textContent;
    
    // Disable button and show loading state
    button.disabled = true;
    button.textContent = '⏳ Updating...';
    statusSpan.textContent = 'Please wait...';
    statusSpan.style.color = '#666';
    
    try {
        const response = await fetch('/api/orders/refresh-all', {
            method: 'POST'
        });

        const data = await response.json();
        
        if (response.ok && data.success) {
            // Show success message
            statusSpan.textContent = `✓ ${data.message}`;
            statusSpan.style.color = '#28a745';
            
                   // Reload orders to show updated data
                   await loadOrders();
                   applyFilters(); // Reapply filters after bulk refresh
            
            // Reset button after 3 seconds
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
                statusSpan.textContent = '';
            }, 3000);
        } else {
            // Show error message
            statusSpan.textContent = `✗ Error: ${data.error || 'Failed to update orders'}`;
            statusSpan.style.color = '#dc3545';
            button.textContent = originalText;
            button.disabled = false;
            
            // Clear error message after 5 seconds
            setTimeout(() => {
                statusSpan.textContent = '';
            }, 5000);
        }
    } catch (error) {
        console.error('Error refreshing all tracking:', error);
        statusSpan.textContent = '✗ Error: Failed to update orders';
        statusSpan.style.color = '#dc3545';
        button.textContent = originalText;
        button.disabled = false;
        
        // Clear error message after 5 seconds
        setTimeout(() => {
            statusSpan.textContent = '';
        }, 5000);
    }
}

function exportOrders() {
    // Get current filtered/sorted orders
    const statusFilter = document.getElementById('statusFilter').value;
    const searchText = document.getElementById('searchFilter').value.toLowerCase().trim();
    
    let ordersToExport = [...allOrders];
    
    // Apply same filters as displayed
    if (statusFilter) {
        ordersToExport = ordersToExport.filter(order => {
            const trackingInfo = order.tracking_info || {};
            const status = trackingInfo.status || order.status || 'Pending';
            return status.toLowerCase() === statusFilter.toLowerCase();
        });
    }
    
    if (searchText) {
        ordersToExport = ordersToExport.filter(order => {
            const productTitle = (order.product_title || '').toLowerCase();
            const trackingNumber = (order.tracking_number || '').toLowerCase();
            const productId = (order.product_id || '').toLowerCase();
            return productTitle.includes(searchText) || 
                   trackingNumber.includes(searchText) || 
                   productId.includes(searchText);
        });
    }
    
    // Convert to CSV
    const headers = [
        'ID',
        'Product Title',
        'Product URL',
        'Product ID',
        'Tracking Number',
        'Status',
        'Latest Update',
        'Order Date',
        'Last Update Date',
        'Added Date',
        'Carrier'
    ];
    
    const csvRows = [headers.join(',')];
    
    ordersToExport.forEach(order => {
        const trackingInfo = order.tracking_info || {};
        const status = trackingInfo.status || order.status || 'Pending';
        const latestUpdate = trackingInfo.latest_standerd_desc || '';
        const carrier = trackingInfo.carrier || '';
        const lastUpdateDate = trackingInfo.last_update_date || '';
        
        const row = [
            order.id || '',
            `"${(order.product_title || '').replace(/"/g, '""')}"`,
            order.product_url || '',
            order.product_id || '',
            order.tracking_number || '',
            status,
            `"${latestUpdate.replace(/"/g, '""')}"`,
            order.order_date || order.added_date || '',
            lastUpdateDate,
            order.added_date || '',
            carrier
        ];
        
        csvRows.push(row.join(','));
    });
    
    // Create CSV content
    const csvContent = csvRows.join('\n');
    
    // Create blob and download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `aliexpress_orders_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Show success message
    const statusSpan = document.getElementById('refreshAllStatus');
    statusSpan.textContent = `✓ Exported ${ordersToExport.length} orders`;
    statusSpan.style.color = '#28a745';
    setTimeout(() => {
        statusSpan.textContent = '';
    }, 3000);
}

async function importOrders() {
    const curlCommand = document.getElementById('curlCommand').value.trim();
    const importBtn = document.getElementById('importBtn');
    const alertContainer = document.getElementById('importAlert');
    const resultsSection = document.getElementById('importResults');
    const resultsContent = document.getElementById('importResultsContent');

    if (!curlCommand) {
        alertContainer.innerHTML = '<div class="alert alert-error">Please paste a cURL command</div>';
        return;
    }

    // Disable button and show loading
    importBtn.disabled = true;
    importBtn.textContent = 'Importing...';
    resultsSection.style.display = 'none';
    alertContainer.innerHTML = '';

    try {
        const response = await fetch('/api/import/orders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ curl_command: curlCommand })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to import orders');
        }

        if (data.success) {
            alertContainer.innerHTML = `<div class="alert alert-success">Successfully imported ${data.imported} order(s)!</div>`;
            
            if (data.orders && data.orders.length > 0) {
                resultsSection.style.display = 'block';
                resultsContent.innerHTML = '<h4>Imported Orders:</h4>';
                data.orders.forEach(order => {
                    const orderDiv = document.createElement('div');
                    orderDiv.className = 'order-preview';
                    orderDiv.style.cssText = 'background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 3px solid #007bff;';
                    orderDiv.innerHTML = `
                        <h4 style="margin: 0 0 10px 0; color: #333;">${order.product_title || 'Unknown Product'}</h4>
                        <p style="margin: 5px 0; color: #666; font-size: 14px;"><strong>Product ID:</strong> ${order.product_id || 'N/A'}</p>
                        <p style="margin: 5px 0; color: #666; font-size: 14px;"><strong>Order Date:</strong> ${order.order_date || 'N/A'}</p>
                        <p style="margin: 5px 0; color: #666; font-size: 14px;"><strong>Price:</strong> ${order.price || 'N/A'}</p>
                    `;
                    resultsContent.appendChild(orderDiv);
                });
            }

            // Reload orders and close modal after 2 seconds
            setTimeout(async () => {
                await loadOrders();
                closeImportModal();
            }, 2000);
        } else {
            alertContainer.innerHTML = `<div class="alert alert-info">${data.message || 'No orders were imported'}</div>`;
        }
    } catch (error) {
        console.error('Import error:', error);
        alertContainer.innerHTML = `<div class="alert alert-error">Error: ${error.message}</div>`;
    } finally {
        importBtn.disabled = false;
        importBtn.textContent = 'Import Orders';
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const addOrderModal = document.getElementById('addOrderModal');
    const editModal = document.getElementById('editModal');
    const eventsModal = document.getElementById('eventsModal');
    const importModal = document.getElementById('importModal');
    const doarApiKeyModal = document.getElementById('doarApiKeyModal');
    const doarEventsModal = document.getElementById('doarEventsModal');
    if (event.target === addOrderModal) {
        closeAddOrderModal();
    }
    if (event.target === editModal) {
        closeModal();
    }
    if (event.target === eventsModal) {
        closeEventsModal();
    }
    const subItemsModal = document.getElementById('subItemsModal');
    if (event.target === subItemsModal) {
        closeSubItemsModal();
    }
    if (event.target === importModal) {
        closeImportModal();
    }
    if (event.target === doarApiKeyModal) {
        closeDoarApiKeyModal();
    }
    if (event.target === doarEventsModal) {
        closeDoarEventsModal();
    }
}

// Allow Enter key to submit
document.addEventListener('DOMContentLoaded', function() {
    const productUrlInput = document.getElementById('productUrl');
    const trackingNumberInput = document.getElementById('trackingNumber');
    
    if (productUrlInput) {
        productUrlInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addOrder();
            }
        });
    }
    
    if (trackingNumberInput) {
        trackingNumberInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addOrder();
            }
        });
    }
});

// Doar Israel API Key Modal Functions
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

// Doar Israel Tracking Functions
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

