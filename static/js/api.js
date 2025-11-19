/* API Functions */
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

