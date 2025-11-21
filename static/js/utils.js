/* Utility Functions */
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

function updateTotalOrdersCount() {
    const totalCountElement = document.getElementById('totalOrdersCount');
    if (totalCountElement) {
        totalCountElement.textContent = allOrders.length;
    }
}

function handleImageError(img) {
    // Prevent infinite loop - only try fallback once
    if (img.dataset.fallbackTried === 'true') {
        return;
    }
    
    img.dataset.fallbackTried = 'true';
    const originalSrc = img.dataset.originalSrc || img.src || '';
    img.src = originalSrc;
    img.style.opacity = '1.0'; // Make it clear it's a placeholder
}

function formatLastUpdateTime(dateString) {
    if (!dateString) return 'Never';
    
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return 'Invalid date';
        
        const now = new Date();
        const diffMs = now - date;
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMinutes = Math.floor(diffSeconds / 60);
        const diffHours = Math.floor(diffMinutes / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffSeconds < 60) {
            return 'Just now';
        } else if (diffMinutes < 60) {
            return `${diffMinutes} min ago`;
        } else if (diffHours < 24) {
            return `${diffHours}h ${diffMinutes % 60}m ago`;
        } else if (diffDays < 7) {
            return `${diffDays}d ${diffHours % 24}h ago`;
        } else {
            // Show full date and time for older updates
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    } catch (e) {
        return 'Error';
    }
}

async function updateLastUpdateTimes() {
    const cainiaoElement = document.getElementById('cainiaoLastUpdate');
    const doarElement = document.getElementById('doarLastUpdate');
    
    if (!cainiaoElement || !doarElement) return;
    
    try {
        const response = await fetch('/api/auto-update/last-updates');
        const data = await response.json();
        
        if (data.success) {
            if (data.cainiao_last_update) {
                const formatted = formatLastUpdateTime(data.cainiao_last_update);
                cainiaoElement.textContent = formatted;
                cainiaoElement.title = new Date(data.cainiao_last_update).toLocaleString();
            } else {
                cainiaoElement.textContent = 'Never';
                cainiaoElement.title = 'No update has been performed yet';
            }
            
            if (data.doar_last_update) {
                const formatted = formatLastUpdateTime(data.doar_last_update);
                doarElement.textContent = formatted;
                doarElement.title = new Date(data.doar_last_update).toLocaleString();
            } else {
                doarElement.textContent = 'Never';
                doarElement.title = 'No update has been performed yet';
            }
        } else {
            cainiaoElement.textContent = 'Error';
            doarElement.textContent = 'Error';
        }
    } catch (error) {
        console.error('Error fetching last update times:', error);
        cainiaoElement.textContent = 'Error';
        doarElement.textContent = 'Error';
    }
}

// Update the time display every minute
let updateTimeInterval = null;
function startUpdateTimeInterval() {
    if (updateTimeInterval) {
        clearInterval(updateTimeInterval);
    }
    updateLastUpdateTimes(); // Initial update
    updateTimeInterval = setInterval(updateLastUpdateTimes, 6000000); // Update every minute
}

