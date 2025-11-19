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

