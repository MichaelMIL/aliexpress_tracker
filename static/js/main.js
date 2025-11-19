/* Main Initialization and Event Listeners */
// Load orders on page load
window.onload = function() {
    loadOrders();
};

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

    checkAppVersion();
});

async function checkAppVersion() {
    const badge = document.querySelector('.version-badge');
    if (!badge) {
        return;
    }

    const currentVersion = (badge.dataset.currentVersion || '').trim();
    if (!currentVersion) {
        return;
    }

    const versionUrl = `https://raw.githubusercontent.com/MichaelMIL/aliexpress_tracker/main/VERSION?cache-bust=${Date.now()}`;

    try {
        const response = await fetch(versionUrl, { cache: 'no-store' });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const latestVersion = (await response.text()).trim();
        if (latestVersion && latestVersion !== currentVersion) {
            badge.classList.add('version-outdated');
            badge.title = `New version available (${latestVersion})`;
        }
    } catch (error) {
        console.warn('Unable to check latest version:', error);
    }
}
