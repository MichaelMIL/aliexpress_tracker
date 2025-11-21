/* Filtering and Sorting Functions */
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
    
    // Filter out delivered orders if checkbox is checked
    const hideDelivered = document.getElementById('hideDelivered').checked;
    if (hideDelivered) {
        filtered = filtered.filter(order => {
            const trackingInfo = order.tracking_info || {};
            const status = trackingInfo.status || order.status || 'Pending';
            return status.toLowerCase() !== 'delivered';
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
    document.getElementById('hideDelivered').checked = true;
    applyFilters();
}

function escapeCsv(value) {
    if (value === null || value === undefined) {
        return '';
    }
    const stringValue = String(value);
    if (/[",\n]/.test(stringValue)) {
        return `"${stringValue.replace(/"/g, '""')}"`;
    }
    return stringValue;
}

function exportOrders() {
    // Get current filtered/sorted orders
    const statusFilter = document.getElementById('statusFilter').value;
    const searchText = document.getElementById('searchFilter').value.toLowerCase().trim();
    const hideDelivered = document.getElementById('hideDelivered').checked;
    
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
    
    // Filter out delivered orders if checkbox is checked
    if (hideDelivered) {
        ordersToExport = ordersToExport.filter(order => {
            const trackingInfo = order.tracking_info || {};
            const status = trackingInfo.status || order.status || 'Pending';
            return status.toLowerCase() !== 'delivered';
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
        'Carrier',
        'Doar Israel Status',
        'Doar Israel Status Field',
        'Doar Israel Delivery Type',
        'Doar Israel Last Event'
    ];
    
    const csvRows = [headers.join(',')];
    
    ordersToExport.forEach(order => {
        const trackingInfo = order.tracking_info || {};
        const status = trackingInfo.status || order.status || 'Pending';
        const latestUpdate = trackingInfo.latest_standerd_desc || '';
        const carrier = trackingInfo.carrier || '';
        const lastUpdateDate = trackingInfo.last_update_date || '';
        
        const doarInfo = order.doar_tracking_info || {};
        const lastDoarEvent = (doarInfo.events && doarInfo.events.length > 0)
            ? `${doarInfo.events[0].date || ''} - ${doarInfo.events[0].description || ''}`.trim()
            : '';

        const row = [
            escapeCsv(order.id || ''),
            escapeCsv(order.product_title || ''),
            escapeCsv(order.product_url || ''),
            escapeCsv(order.product_id || ''),
            escapeCsv(order.tracking_number || ''),
            escapeCsv(status),
            escapeCsv(latestUpdate),
            escapeCsv(order.order_date || order.added_date || ''),
            escapeCsv(lastUpdateDate),
            escapeCsv(order.added_date || ''),
            escapeCsv(carrier),
            escapeCsv(doarInfo.status || ''),
            escapeCsv(doarInfo.status_field || ''),
            escapeCsv(doarInfo.delivery_type || ''),
            escapeCsv(lastDoarEvent)
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

