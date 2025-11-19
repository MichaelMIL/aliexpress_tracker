/* UI Display Functions */
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
                    <div class="doar-delivery-cell">
                        ${doarDeliveryType ? `<span class="doar-delivery-text delivery-type-${doarDeliveryType.replace(/\s+/g, '-')}">${doarDeliveryType}</span>` : '<span class="no-update">N/A</span>'}
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

