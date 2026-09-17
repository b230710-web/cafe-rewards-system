/**
 * Aurora Café Rewards & Multi-View Terminal - Client Controller
 * Pure Vanilla JavaScript (ES6+). Zero Node.js / Zero npm.
 */

const state = {
    activeMember: null,
    rewardsCatalog: [],
    authToken: localStorage.getItem("cafe_admin_token") || null,
    currentUser: null,
    searchDebounceTimer: null,
    searchSelectedIndex: -1,
    searchResults: []
};

// ===================================================================
// Initialization
// ===================================================================

document.addEventListener("DOMContentLoaded", () => {
    initKeyboardShortcuts();
    initSearchEvents();
    initPurchaseInputEvents();
    loadRewardsCatalog();
    loadQuickDemoMembers();
    checkAuthSession();
});

function initKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
        if (e.key === "/" && document.activeElement.tagName !== "INPUT") {
            e.preventDefault();
            switchSlide("pos");
            const searchInput = document.getElementById("phoneSearchInput");
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        if (e.key === "Escape") {
            closeSearchDropdown();
            closeModal("registerModal");
        }
    });

    const openRegBtn = document.getElementById("openRegisterBtn");
    if (openRegBtn) openRegBtn.addEventListener("click", () => openModal("registerModal"));

    const verifyBtn = document.getElementById("verifyAuditBtn");
    if (verifyBtn) verifyBtn.addEventListener("click", () => verifyActiveMemberAudit());

    const clearBtn = document.getElementById("clearSearchBtn");
    if (clearBtn) clearBtn.addEventListener("click", () => clearSearch());
}

// ===================================================================
// Slide / View Navigation
// ===================================================================

function switchSlide(slideId) {
    // Hide all slides
    document.querySelectorAll(".slide-view").forEach(s => s.classList.remove("active"));
    document.querySelectorAll(".slide-tab").forEach(t => t.classList.remove("active"));

    if (slideId === "customer") {
        document.getElementById("slideCustomer").classList.add("active");
        document.getElementById("tabNavCustomer").classList.add("active");
    } else if (slideId === "pos") {
        document.getElementById("slidePos").classList.add("active");
        document.getElementById("tabNavPos").classList.add("active");
        setTimeout(() => {
            const input = document.getElementById("phoneSearchInput");
            if (input && !state.activeMember) input.focus();
        }, 100);
    } else if (slideId === "admin") {
        document.getElementById("slideAdmin").classList.add("active");
        document.getElementById("tabNavAdmin").classList.add("active");
        if (state.currentUser) {
            loadAdminMembers();
            loadAdminAnalytics();
        }
    }
}

function scrollToWidget() {
    const card = document.getElementById("customerLookupCard");
    if (card) {
        card.scrollIntoView({ behavior: "smooth", block: "center" });
        const input = document.getElementById("customerPhoneInput");
        if (input) input.focus();
    }
}

// ===================================================================
// SLIDE 1: Customer Rewards Experience & Self-Lookup
// ===================================================================

async function handleCustomerLookup() {
    const input = document.getElementById("customerPhoneInput");
    const phone = input.value.trim();
    const panel = document.getElementById("customerResultPanel");

    if (!phone) {
        showToast("Please enter your 10-digit phone number.", "error");
        return;
    }

    try {
        const res = await fetch(`/api/customer/lookup?phone=${encodeURIComponent(phone)}`);
        const data = await res.json();

        if (data.success && data.member) {
            const m = data.member;
            document.getElementById("custResultName").textContent = m.name;
            const tierEl = document.getElementById("custResultTier");
            tierEl.textContent = `${m.tier_name} Tier (${m.points_multiplier}x)`;
            tierEl.className = `result-tier-tag ${m.tier_name.toLowerCase()}`;

            document.getElementById("custResultBalance").textContent = m.current_balance;

            const noteEl = document.getElementById("custResultNote");
            if (m.next_tier) {
                noteEl.textContent = `🎯 You are only ${m.next_tier.points_needed} points away from ${m.next_tier.name} Tier!`;
            } else {
                noteEl.textContent = `🏆 You have achieved our highest VIP ${m.tier_name} Tier! Enjoy 1.50x points on everything.`;
            }

            panel.style.display = "block";
            showToast(`Welcome back, ${m.name}!`, "success");
        } else {
            showToast(data.error || "No loyalty member found with that phone number.", "error");
            panel.style.display = "none";
        }
    } catch (err) {
        showToast("Error checking balance. Please try again.", "error");
    }
}

function renderCustomerShowcase(catalog) {
    const container = document.getElementById("customerRewardsCards");
    if (!container || !catalog) return;

    // Display first 4 sweet desserts/treats
    const showcaseItems = catalog.slice(0, 4);
    container.innerHTML = showcaseItems.map(item => `
        <div class="dessert-card">
            <div class="dessert-img-icon">${item.icon || '🥐'}</div>
            <h4>${escapeHtml(item.item_name)}</h4>
            <p style="font-size: 12px; color: #7A5B46;">${escapeHtml(item.description || item.category)}</p>
            <span class="dessert-pts-pill">Redeem: ${item.points_cost} PTS</span>
        </div>
    `).join("");
}

// ===================================================================
// SLIDE 2: Counter Staff POS Terminal (Search, Earn, Redeem, Ledger)
// ===================================================================

function initSearchEvents() {
    const input = document.getElementById("phoneSearchInput");
    const dropdown = document.getElementById("searchResultsDropdown");
    const clearBtn = document.getElementById("clearSearchBtn");

    if (!input) return;

    input.addEventListener("input", (e) => {
        const query = e.target.value.trim();
        if (clearBtn) clearBtn.style.display = query ? "block" : "none";

        if (state.searchDebounceTimer) clearTimeout(state.searchDebounceTimer);
        if (!query) {
            closeSearchDropdown();
            return;
        }

        state.searchDebounceTimer = setTimeout(() => {
            performPhoneSearch(query);
        }, 180);
    });

    input.addEventListener("keydown", (e) => {
        const items = dropdown.querySelectorAll(".search-result-item");
        if (!items.length) return;

        if (e.key === "ArrowDown") {
            e.preventDefault();
            state.searchSelectedIndex = Math.min(state.searchSelectedIndex + 1, items.length - 1);
            updateSelectedDropdownItem(items);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            state.searchSelectedIndex = Math.max(state.searchSelectedIndex - 1, 0);
            updateSelectedDropdownItem(items);
        } else if (e.key === "Enter") {
            e.preventDefault();
            if (state.searchSelectedIndex >= 0 && state.searchResults[state.searchSelectedIndex]) {
                selectMember(state.searchResults[state.searchSelectedIndex]);
                closeSearchDropdown();
            } else if (state.searchResults.length > 0) {
                selectMember(state.searchResults[0]);
                closeSearchDropdown();
            }
        }
    });

    document.addEventListener("click", (e) => {
        if (!e.target.closest(".pos-search-box")) {
            closeSearchDropdown();
        }
    });
}

async function performPhoneSearch(query) {
    try {
        const res = await fetch(`/api/members/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        if (data.success) {
            state.searchResults = data.members;
            state.searchSelectedIndex = -1;
            renderSearchResults(data.members);
        }
    } catch (err) {
        console.error("Search error:", err);
    }
}

function renderSearchResults(members) {
    const dropdown = document.getElementById("searchResultsDropdown");
    if (!members || members.length === 0) {
        dropdown.innerHTML = `<div class="empty-ledger">No member found.<br><button class="btn btn-pill btn-terracotta btn-sm" style="margin-top:8px" onclick="openRegisterWithPhone()">+ Register Member</button></div>`;
        dropdown.style.display = "block";
        return;
    }

    dropdown.innerHTML = members.map((m, idx) => `
        <div class="search-result-item" data-index="${idx}" onclick="selectMemberById(${m.id})">
            <div class="result-member-info">
                <span class="result-name">${escapeHtml(m.name)}</span>
                <span class="result-phone">📞 ${escapeHtml(m.phone)}</span>
            </div>
            <div class="result-points-pill">
                <span class="result-badge ${m.tier_name.toLowerCase()}">${escapeHtml(m.tier_name)}</span>
                <span class="result-pts">${m.current_balance} pts</span>
            </div>
        </div>
    `).join("");
    dropdown.style.display = "block";
}

function updateSelectedDropdownItem(items) {
    items.forEach((item, idx) => {
        if (idx === state.searchSelectedIndex) {
            item.classList.add("selected");
            item.scrollIntoView({ block: "nearest" });
        } else {
            item.classList.remove("selected");
        }
    });
}

function closeSearchDropdown() {
    const dropdown = document.getElementById("searchResultsDropdown");
    if (dropdown) dropdown.style.display = "none";
    state.searchSelectedIndex = -1;
}

function clearSearch() {
    const input = document.getElementById("phoneSearchInput");
    if (input) {
        input.value = "";
        document.getElementById("clearSearchBtn").style.display = "none";
        closeSearchDropdown();
        input.focus();
    }
}

function openRegisterWithPhone() {
    const input = document.getElementById("phoneSearchInput");
    const val = input ? input.value.trim() : "";
    closeSearchDropdown();
    openModal("registerModal");
    if (val) document.getElementById("newMemberPhone").value = val;
}

async function selectMemberById(memberId) {
    closeSearchDropdown();
    try {
        const res = await fetch(`/api/members/${memberId}`);
        const data = await res.json();
        if (data.success) {
            selectMember(data.member);
        }
    } catch (err) {
        showToast("Error loading member.", "error");
    }
}

function selectMember(member) {
    state.activeMember = member;

    document.getElementById("noMemberPlaceholder").style.display = "none";
    const card = document.getElementById("activeMemberCard");
    card.style.display = "flex";

    document.getElementById("memberAvatar").textContent = (member.name || "M").charAt(0).toUpperCase();
    document.getElementById("memberName").textContent = member.name;
    document.getElementById("memberPhone").textContent = `📞 ${member.phone}`;

    const tierBadge = document.getElementById("memberTierBadge");
    tierBadge.textContent = member.tier_name;
    tierBadge.className = `tier-pill ${member.tier_name.toLowerCase()}`;

    document.getElementById("memberBalance").textContent = member.current_balance;
    document.getElementById("tierMultiplierValue").textContent = `${member.points_multiplier}x Earning Rate`;
    document.getElementById("earnRateChip").textContent = `${member.tier_name} Tier • ${member.points_multiplier}x Rate`;

    const nextNote = document.getElementById("tierNextNote");
    const fill = document.getElementById("tierProgressBar");

    if (member.next_tier) {
        fill.style.width = `${member.next_tier.progress_percentage}%`;
        nextNote.textContent = `${member.next_tier.points_needed} more pts to ${member.next_tier.name} Tier (${member.next_tier.progress_percentage}%)`;
    } else {
        fill.style.width = "100%";
        nextNote.textContent = `🏆 Top VIP Tier Achieved (${member.tier_name})!`;
    }

    document.getElementById("memberLifetimeSpend").textContent = `$${parseFloat(member.total_spend || 0).toFixed(2)}`;
    document.getElementById("memberVisits").textContent = member.visit_count || 0;
    document.getElementById("memberLifetimePoints").textContent = `${member.lifetime_points} pts`;

    updatePurchaseCalculation();
    document.getElementById("commitPurchaseBtn").disabled = false;
    document.getElementById("redeemAvailablePts").textContent = `${member.current_balance} PTS`;

    renderRewardsCatalog();
    loadMemberLedger(member.id);
}

// Purchase & Calculation
function initPurchaseInputEvents() {
    const input = document.getElementById("orderAmountInput");
    if (input) input.addEventListener("input", updatePurchaseCalculation);

    const commitBtn = document.getElementById("commitPurchaseBtn");
    if (commitBtn) commitBtn.addEventListener("click", handleCommitPurchase);
}

function addAmount(val) {
    const input = document.getElementById("orderAmountInput");
    const current = parseFloat(input.value) || 0.0;
    input.value = (current + val).toFixed(2);
    updatePurchaseCalculation();
}

function clearAmount() {
    const input = document.getElementById("orderAmountInput");
    if (input) input.value = "";
    updatePurchaseCalculation();
}

function updatePurchaseCalculation() {
    const amount = parseFloat(document.getElementById("orderAmountInput").value) || 0.0;
    const member = state.activeMember;

    if (!member || amount <= 0) {
        document.getElementById("calcBasePts").textContent = "0 pts";
        document.getElementById("calcMultiplier").textContent = member ? `${member.points_multiplier}x` : "1.0x";
        document.getElementById("calcTotalEarned").textContent = "+0 PTS";
        document.getElementById("calcProjectedBalance").textContent = member ? `${member.current_balance} pts` : "0 pts";
        document.getElementById("commitPurchaseBtn").disabled = true;
        return;
    }

    const multiplier = member.points_multiplier || 1.0;
    const basePts = Math.round(amount);
    const totalEarned = Math.max(1, Math.round(amount * multiplier));
    const projectedBalance = member.current_balance + totalEarned;

    document.getElementById("calcBasePts").textContent = `${basePts} pts`;
    document.getElementById("calcMultiplier").textContent = `${multiplier}x (${member.tier_name})`;
    document.getElementById("calcTotalEarned").textContent = `+${totalEarned} PTS`;
    document.getElementById("calcProjectedBalance").textContent = `${projectedBalance} pts`;

    const commitBtn = document.getElementById("commitPurchaseBtn");
    commitBtn.disabled = false;
    commitBtn.innerHTML = `<span>💳 Record $${amount.toFixed(2)} Purchase & Credit +${totalEarned} PTS</span>`;
}

async function handleCommitPurchase() {
    if (!state.activeMember) return;
    const amount = parseFloat(document.getElementById("orderAmountInput").value);
    if (!amount || amount <= 0) return;

    const commitBtn = document.getElementById("commitPurchaseBtn");
    commitBtn.disabled = true;

    try {
        const res = await fetch("/api/purchase", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                member_id: state.activeMember.id,
                order_amount: amount
            })
        });

        const data = await res.json();
        if (data.success) {
            const balanceEl = document.getElementById("memberBalance");
            balanceEl.classList.remove("flash-add");
            void balanceEl.offsetWidth;
            balanceEl.classList.add("flash-add");

            if (data.tier_upgraded) {
                showToast(`🎉 Tier Promotion! Promoted to ${data.new_tier} Tier!`, "success");
            } else {
                showToast(`✅ Purchase recorded! +${data.points_earned} points credited.`, "success");
            }

            selectMember(data.member);
            document.getElementById("orderAmountInput").value = "";
            updatePurchaseCalculation();
        } else {
            showToast(data.error || "Failed to record purchase.", "error");
        }
    } catch (err) {
        showToast("Error contacting server.", "error");
    } finally {
        commitBtn.disabled = false;
    }
}

// Rewards Catalog & Redemption
async function loadRewardsCatalog() {
    try {
        const res = await fetch("/api/rewards");
        const data = await res.json();
        if (data.success) {
            state.rewardsCatalog = data.rewards;
            renderRewardsCatalog();
            renderCustomerShowcase(data.rewards);
            renderAdminCatalog(data.rewards);
        }
    } catch (err) {
        console.error("Failed to load rewards:", err);
    }
}

function renderRewardsCatalog() {
    const grid = document.getElementById("rewardsGrid");
    if (!grid || !state.rewardsCatalog) return;

    const balance = state.activeMember ? state.activeMember.current_balance : 0;

    grid.innerHTML = state.rewardsCatalog.map(item => {
        const canAfford = state.activeMember && balance >= item.points_cost;
        const ptsShort = item.points_cost - balance;

        return `
            <div class="reward-card ${canAfford ? '' : 'locked'}">
                <div class="reward-card-top">
                    <span class="reward-card-icon">${item.icon || '☕'}</span>
                    <div class="reward-card-details">
                        <h4>${escapeHtml(item.item_name)}</h4>
                        <span style="font-size: 11px; color: #6B756E;">$${parseFloat(item.retail_value).toFixed(2)}</span>
                    </div>
                </div>
                <div class="reward-card-bottom">
                    <span class="reward-points-cost">${item.points_cost} PTS</span>
                    <button class="redeem-action-btn"
                        ${canAfford ? '' : 'disabled'}
                        onclick="handleRedeemReward(${item.id}, '${escapeHtml(item.item_name)}', ${item.points_cost})">
                        ${canAfford ? 'Redeem' : `+${ptsShort} pts`}
                    </button>
                </div>
            </div>
        `;
    }).join("");
}

async function handleRedeemReward(rewardId, itemName, pointsCost) {
    if (!state.activeMember) return;
    if (state.activeMember.current_balance < pointsCost) {
        showToast(`Member needs ${pointsCost} points.`, "error");
        return;
    }

    const ok = confirm(`Redeem '${itemName}' for ${pointsCost} points for ${state.activeMember.name}?`);
    if (!ok) return;

    try {
        const res = await fetch("/api/redeem", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                member_id: state.activeMember.id,
                reward_id: rewardId
            })
        });

        const data = await res.json();
        if (data.success) {
            const balanceEl = document.getElementById("memberBalance");
            balanceEl.classList.remove("flash-sub");
            void balanceEl.offsetWidth;
            balanceEl.classList.add("flash-sub");

            showToast(`🎁 Redeemed: ${itemName}!`, "success");
            selectMember(data.member);
        } else {
            showToast(data.error || "Redemption failed.", "error");
        }
    } catch (err) {
        showToast("Error processing redemption.", "error");
    }
}

// Ledger Table
async function loadMemberLedger(memberId) {
    const tbody = document.getElementById("ledgerTableBody");
    try {
        const res = await fetch(`/api/ledger/${memberId}`);
        const data = await res.json();

        if (data.success && data.ledger.length > 0) {
            tbody.innerHTML = data.ledger.map(tx => {
                const isPos = tx.points_delta > 0;
                const timeStr = tx.created_at ? tx.created_at.substring(0, 16) : "--";
                return `
                    <tr>
                        <td style="font-family:'JetBrains Mono'; font-size:11px; color:#6B756E;">${timeStr}</td>
                        <td><span class="ledger-badge ${tx.transaction_type.toLowerCase()}">${tx.transaction_type}</span></td>
                        <td>${escapeHtml(tx.notes || '--')}</td>
                        <td class="ledger-delta ${isPos ? 'positive' : 'negative'}">${isPos ? '+' : ''}${tx.points_delta} pts</td>
                        <td style="font-family:'JetBrains Mono'; font-weight:700;">${tx.balance_after} pts</td>
                    </tr>
                `;
            }).join("");
        } else {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-ledger">No ledger transactions found.</td></tr>`;
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-ledger">Error loading ledger.</td></tr>`;
    }
}

async function verifyActiveMemberAudit() {
    if (!state.activeMember) return;
    try {
        const res = await fetch(`/api/audit/${state.activeMember.id}`);
        const data = await res.json();
        if (data.success && data.audit.is_consistent) {
            showToast(`🛡️ Live Audit Passed: Balance ${data.audit.stored_balance} matches SUM(ledger) exactly (0 drift)`, "success");
        } else {
            showToast(`Discrepancy detected!`, "error");
        }
    } catch (err) {
        showToast("Audit check failed.", "error");
    }
}

async function loadQuickDemoMembers() {
    const container = document.getElementById("demoPillsList");
    if (!container) return;

    try {
        const res = await fetch("/api/members/search?q=");
        const data = await res.json();
        if (data.success && data.members.length > 0) {
            const regular = data.members.find(m => m.tier_name === "Regular") || data.members[0];
            const silver = data.members.find(m => m.tier_name === "Silver");
            const gold = data.members.find(m => m.tier_name === "Gold");

            const samples = [regular, silver, gold].filter(Boolean);
            container.innerHTML = samples.map(m => `
                <button class="demo-pill-btn" onclick="selectMemberById(${m.id})">
                    <span><strong>${escapeHtml(m.name)}</strong> (📞 ${m.phone})</span>
                    <span class="result-badge ${m.tier_name.toLowerCase()}">${m.tier_name} • ${m.current_balance} pts</span>
                </button>
            `).join("");
        }
    } catch (err) {
        console.error(err);
    }
}

// ===================================================================
// SLIDE 3: Admin & Database Control Portal (Authentication & Management)
// ===================================================================

async function checkAuthSession() {
    const token = state.authToken;
    const authPill = document.getElementById("navAuthPill");
    const authText = document.getElementById("navAuthText");

    if (!token) {
        setUnauthenticatedUI();
        return;
    }

    try {
        const res = await fetch("/api/auth/me", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.success && data.authenticated) {
            state.currentUser = data.user;
            setAuthenticatedUI(data.user);
        } else {
            setUnauthenticatedUI();
        }
    } catch (err) {
        setUnauthenticatedUI();
    }
}

function setAuthenticatedUI(user) {
    document.getElementById("adminLoginView").style.display = "none";
    document.getElementById("adminDashboardView").style.display = "block";
    document.getElementById("adminGreeting").textContent = `Signed in as ${user.full_name} (${user.role.toUpperCase()})`;

    const authText = document.getElementById("navAuthText");
    if (authText) authText.textContent = `Admin: ${user.username}`;

    loadAdminMembers();
    loadAdminAnalytics();
}

function setUnauthenticatedUI() {
    state.currentUser = null;
    state.authToken = null;
    localStorage.removeItem("cafe_admin_token");

    document.getElementById("adminLoginView").style.display = "flex";
    document.getElementById("adminDashboardView").style.display = "none";

    const authText = document.getElementById("navAuthText");
    if (authText) authText.textContent = "Guest Staff";
}

async function handleAdminLogin(e) {
    e.preventDefault();
    const username = document.getElementById("adminUsernameInput").value.trim();
    const password = document.getElementById("adminPasswordInput").value.trim();

    const submitBtn = document.getElementById("adminLoginBtn");
    submitBtn.disabled = true;
    submitBtn.textContent = "Authenticating...";

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();
        if (data.success) {
            state.authToken = data.token;
            state.currentUser = data.user;
            localStorage.setItem("cafe_admin_token", data.token);

            showToast(`Welcome back, ${data.user.full_name}!`, "success");
            setAuthenticatedUI(data.user);
        } else {
            showToast(data.error || "Authentication failed.", "error");
        }
    } catch (err) {
        showToast("Error connecting to auth server.", "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Authenticate & Enter";
    }
}

async function handleAdminLogout() {
    try {
        await fetch("/api/auth/logout", {
            method: "POST",
            headers: { "Authorization": `Bearer ${state.authToken}` }
        });
    } catch (err) {
        // Continue logout locally
    }
    setUnauthenticatedUI();
    showToast("Signed out successfully.", "success");
}

function switchAdminTab(tabName) {
    document.querySelectorAll(".admin-tab-btn").forEach(b => b.classList.remove("active"));
    document.getElementById("adminTabMembers").style.display = "none";
    document.getElementById("adminTabCatalog").style.display = "none";
    document.getElementById("adminTabAnalytics").style.display = "none";

    if (tabName === "members") {
        document.getElementById("adminTabMembers").style.display = "block";
        loadAdminMembers();
    } else if (tabName === "catalog") {
        document.getElementById("adminTabCatalog").style.display = "block";
        loadRewardsCatalog();
    } else if (tabName === "analytics") {
        document.getElementById("adminTabAnalytics").style.display = "block";
        loadAdminAnalytics();
    }
    event.target.classList.add("active");
}

let adminSearchTimer = null;
function debounceAdminMemberSearch() {
    if (adminSearchTimer) clearTimeout(adminSearchTimer);
    adminSearchTimer = setTimeout(() => {
        loadAdminMembers();
    }, 250);
}

async function loadAdminMembers() {
    const tbody = document.getElementById("adminMembersTableBody");
    const query = document.getElementById("adminMemberSearch").value.trim();
    const tierId = document.getElementById("adminTierFilter").value;

    let url = `/api/admin/members?limit=50&offset=0`;
    if (query) url += `&q=${encodeURIComponent(query)}`;
    if (tierId) url += `&tier_id=${tierId}`;

    try {
        const res = await fetch(url);
        const data = await res.json();

        if (data.success && data.members.length > 0) {
            tbody.innerHTML = data.members.map(m => `
                <tr>
                    <td>#${m.id}</td>
                    <td><strong>${escapeHtml(m.name)}</strong></td>
                    <td style="font-family:'JetBrains Mono';">${escapeHtml(m.phone)}</td>
                    <td><span class="result-badge ${m.tier_name.toLowerCase()}">${m.tier_name}</span></td>
                    <td style="font-family:'JetBrains Mono'; font-weight:700;">${m.current_balance} pts</td>
                    <td>$${parseFloat(m.total_spend || 0).toFixed(2)}</td>
                    <td>${m.visit_count}</td>
                    <td>
                        <button class="btn btn-pill btn-terracotta btn-sm" onclick="selectMemberById(${m.id}); switchSlide('pos');">
                            Open in POS
                        </button>
                    </td>
                </tr>
            `).join("");
        } else {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center" style="padding:24px; color:#6B756E;">No matching member accounts found.</td></tr>`;
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center">Failed to load member records.</td></tr>`;
    }
}

function renderAdminCatalog(catalog) {
    const list = document.getElementById("adminCatalogList");
    if (!list) return;

    list.innerHTML = catalog.map(item => `
        <div class="admin-catalog-item">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:22px;">${item.icon || '☕'}</span>
                <div>
                    <strong>${escapeHtml(item.item_name)}</strong>
                    <span style="font-size:11px; color:#6B756E; display:block;">${item.category} • $${parseFloat(item.retail_value).toFixed(2)}</span>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:12px;">
                <span class="reward-points-cost">${item.points_cost} PTS</span>
            </div>
        </div>
    `).join("");
}

async function handleAddReward(e) {
    e.preventDefault();
    const name = document.getElementById("newRewardName").value.trim();
    const category = document.getElementById("newRewardCategory").value;
    const points = parseInt(document.getElementById("newRewardCost").value, 10);
    const retail = parseFloat(document.getElementById("newRewardRetail").value);
    const desc = document.getElementById("newRewardDesc").value.trim();
    const icon = document.getElementById("newRewardIcon").value.trim() || "🥐";

    try {
        const res = await fetch("/api/admin/rewards", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                item_name: name,
                category,
                points_cost: points,
                retail_value: retail,
                description: desc,
                icon
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Added '${name}' to rewards menu!`, "success");
            document.getElementById("addRewardForm").reset();
            loadRewardsCatalog();
        } else {
            showToast(data.error || "Failed to add reward.", "error");
        }
    } catch (err) {
        showToast("Error adding reward.", "error");
    }
}

async function runSystemWideAudit() {
    try {
        showToast("Running full system mathematical audit...", "success");
        const res = await fetch("/api/admin/audit-all");
        const data = await res.json();

        if (data.success && data.audit.audit_passed) {
            alert(`✅ 100% MATHEMATICAL INTEGRITY CONFIRMED!\n\nAudited: ${data.audit.total_accounts_audited} member accounts.\nDiscrepancies found: 0\nEvery single stored balance matches SUM(points_delta) across all transactions.`);
        } else {
            alert(`⚠️ Audit alert! Discrepancies detected: ${data.audit.discrepancies_found}`);
        }
    } catch (err) {
        showToast("System audit failed.", "error");
    }
}

async function exportDatabaseJson() {
    try {
        const res = await fetch("/api/admin/export");
        const data = await res.json();
        if (data.success) {
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data.data, null, 2));
            const dlAnchor = document.createElement("a");
            dlAnchor.setAttribute("href", dataStr);
            dlAnchor.setAttribute("download", `cafe_rewards_backup_${Date.now()}.json`);
            document.body.appendChild(dlAnchor);
            dlAnchor.click();
            dlAnchor.remove();
            showToast("Database exported successfully!", "success");
        }
    } catch (err) {
        showToast("Failed to export database.", "error");
    }
}

async function loadAdminAnalytics() {
    try {
        const res = await fetch("/api/analytics");
        const data = await res.json();
        if (data.success) {
            const a = data.analytics;
            document.getElementById("adminKpiMembers").textContent = a.total_members;
            document.getElementById("adminKpiRevenue").textContent = `$${a.total_revenue.toLocaleString()}`;
            document.getElementById("adminKpiCirculation").textContent = `${a.total_points_in_circulation.toLocaleString()} pts`;
            document.getElementById("adminKpiRedemption").textContent = `${a.redemption_rate_pct}%`;

            const list = document.getElementById("adminTierList");
            list.innerHTML = a.tier_distribution.map(t => `
                <div class="tier-dist-item">
                    <span><strong>${t.tier_name} Tier</strong> (${t.member_count} members)</span>
                    <span>Average Customer Spend: <strong>$${parseFloat(t.avg_spend).toFixed(2)}</strong></span>
                </div>
            `).join("");
        }
    } catch (err) {
        console.error(err);
    }
}

// ===================================================================
// Registration & Modal Management
// ===================================================================

function switchOperationTab(tab) {
    const earnBtn = document.getElementById("tabEarnBtn");
    const redeemBtn = document.getElementById("tabRedeemBtn");
    const earnContent = document.getElementById("earnTabContent");
    const redeemContent = document.getElementById("redeemTabContent");

    if (tab === "earn") {
        earnBtn.classList.add("active");
        redeemBtn.classList.remove("active");
        earnContent.style.display = "block";
        redeemContent.style.display = "none";
    } else {
        redeemBtn.classList.add("active");
        earnBtn.classList.remove("active");
        redeemContent.style.display = "block";
        earnContent.style.display = "none";
        renderRewardsCatalog();
    }
}

function openModal(id) {
    document.getElementById(id).style.display = "flex";
}

function closeModal(id) {
    document.getElementById(id).style.display = "none";
}

async function handleRegisterSubmit(e) {
    e.preventDefault();
    const name = document.getElementById("newMemberName").value.trim();
    const phone = document.getElementById("newMemberPhone").value.trim();
    const email = document.getElementById("newMemberEmail").value.trim();

    try {
        const res = await fetch("/api/members", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, phone, email, welcome_bonus: 50 })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`🎉 Registered ${name}! +50 Welcome Bonus points credited.`, "success");
            closeModal("registerModal");
            document.getElementById("registerForm").reset();

            selectMember(data.member);
            switchSlide("pos");
            loadQuickDemoMembers();
        } else {
            showToast(data.error || "Registration failed.", "error");
        }
    } catch (err) {
        showToast("Error registering member.", "error");
    }
}

function showToast(message, type = "success") {
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        setTimeout(() => toast.remove(), 300);
    }, 3800);
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
