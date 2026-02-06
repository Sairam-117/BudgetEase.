// DOM Elements
const claimForm = document.getElementById('claimForm');
const budgetStats = document.getElementById('budgetStats');
const claimsTableBody = document.getElementById('claimsTableBody');
const noClaimsMsg = document.getElementById('noClaimsMsg');
const notification = document.getElementById('notification');

// Notification Helper
function showNotification(message, type = 'success') {
    notification.textContent = message;
    notification.style.display = 'block';
    notification.style.borderColor = type === 'success' ? '#10b981' : '#ef4444';
    notification.style.color = type === 'success' ? '#065f46' : '#991b1b';
    notification.style.backgroundColor = type === 'success' ? '#dcfce7' : '#fee2e2';

    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// 1. Handle Claim Submission (Member Portal)
if (claimForm) {
    claimForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = claimForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Submitting...';
        submitBtn.disabled = true;

        const formData = new FormData(claimForm);

        try {
            const response = await fetch('/api/claim', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            if (result.success) {
                // Show extended message with amount
                showNotification(result.message, 'success');
                claimForm.reset();
            } else {
                showNotification(result.message, 'error');
            }
        } catch (error) {
            showNotification('Network error occurred.', 'error');
            console.error(error);
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    });
}

// 2. Dashboard Logic (Admin Page)
async function loadDashboardData() {
    if (!budgetStats) return; // Not on dashboard page

    try {
        const response = await fetch('/api/data');
        const data = await response.json();

        renderBudgets(data.budgets);
        renderClaims(data.claims);
        renderAlerts(data.alerts);

    } catch (error) {
        console.error('Error fetching data:', error);
        budgetStats.innerHTML = '<div class="stat-card" style="color: red;">Error loading data. Is server running?</div>';
    }
}

function renderBudgets(budgets) {
    budgetStats.innerHTML = '';

    for (const [eventName, budget] of Object.entries(budgets)) {
        const remaining = budget.total - budget.used;
        const percentUsed = (budget.used / budget.total) * 100;

        const card = document.createElement('div');
        card.className = 'stat-card';
        card.innerHTML = `
            <h3>${eventName}</h3>
            <div class="value">₹${remaining.toLocaleString()}</div>
            <div style="font-size: 0.875rem; color: var(--text-muted); margin-top: 0.25rem;">
                Used: ₹${budget.used.toLocaleString()} / ₹${budget.total.toLocaleString()}
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${percentUsed}%"></div>
            </div>
        `;
        budgetStats.appendChild(card);
    }
}

function renderAlerts(alerts) {
    const container = document.getElementById('alertsContainer');
    const panel = document.getElementById('alertPanel');

    if (!container || !panel) return;

    if (!alerts || alerts.length === 0) {
        panel.style.display = 'none';
        return;
    }

    panel.style.display = 'block';
    container.innerHTML = '';

    alerts.forEach(alert => {
        const div = document.createElement('div');
        div.className = `alert-item alert-${alert.severity}`;
        div.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 0.25rem;">${alert.message}</div>
            <div style="font-size: 0.8rem; opacity: 0.8;">${alert.timestamp}</div>
        `;
        container.appendChild(div);
    });
}

function renderClaims(claims) {
    claimsTableBody.innerHTML = '';

    if (claims.length === 0) {
        noClaimsMsg.style.display = 'block';
        return;
    }
    noClaimsMsg.style.display = 'none';

    // Sort claims: Pending first, then by timestamp (implicit in list order)
    claims.reverse().forEach(claim => {
        const row = document.createElement('tr');

        let statusClass = '';
        switch (claim.status) {
            case 'Approved': statusClass = 'status-approved'; break;
            case 'Rejected': statusClass = 'status-rejected'; break;
            default: statusClass = 'status-pending';
        }

        // Check for extraction warning
        let warningBadge = '';
        if (claim.needs_review) {
            warningBadge = ' <span style="color: #ea580c; font-size: 0.8em; font-weight: bold; margin-left: 5px;" title="Amount extraction failed or low confidence">⚠️ Needs Review</span>';
        }

        const actions = claim.status === 'Pending'
            ? `
                <button class="action-btn btn-approve" onclick="updateClaim('${claim.id}', 'approve')">Approve</button>
                <button class="action-btn btn-reject" onclick="updateClaim('${claim.id}', 'reject')">Reject</button>
              `
            : `<span style="color: var(--text-muted); font-size: 0.9em;">No actions</span>`;

        const billLink = claim.bill_filename
            ? `<a href="/uploads/${claim.bill_filename}" target="_blank" class="view-btn">View</a>`
            : '<span style="color:var(--text-muted)">No Bill</span>';

        row.innerHTML = `
            <td><strong>${claim.event}</strong></td>
            <td>${claim.category}</td>
            <td>${claim.description}</td>
            <td>${billLink}</td>
            <td>₹${claim.amount.toLocaleString()}${warningBadge}</td>
            <td><span class="status-badge ${statusClass}">${claim.status}</span></td>
            <td>${actions}</td>
        `;
        claimsTableBody.appendChild(row);
    });
}

async function updateClaim(claimId, action) {
    let bodyData = {};

    if (action === 'approve') {
        const amountStr = prompt("Please enter the verified amount from the bill (₹):");
        if (amountStr === null) return; // User cancelled

        const amount = parseFloat(amountStr);
        if (isNaN(amount) || amount <= 0) {
            alert("Invalid amount. PLease enter a valid number.");
            return;
        }
        bodyData = { amount: amount };
    } else {
        if (!confirm(`Are you sure you want to reject this claim?`)) return;
    }

    try {
        const response = await fetch(`/api/${action}/${claimId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(bodyData)
        });
        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
            loadDashboardData(); // Refresh UI
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('Error updating claim', 'error');
    }
}

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
});
