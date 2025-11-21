/* Tracking Refresh Functions */
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
            
            // Update last update times
            await updateLastUpdateTimes();
            
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

