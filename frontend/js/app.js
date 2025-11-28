// AdvisorMatch Frontend Application

const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const topKInput = document.getElementById('topK');
const loadingSpinner = document.getElementById('loadingSpinner');
const errorMessage = document.getElementById('errorMessage');
const resultsSection = document.getElementById('resultsSection');
const resultsInfo = document.getElementById('resultsInfo');
const resultsContainer = document.getElementById('resultsContainer');

// Event Listeners
searchButton.addEventListener('click', performSearch);
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});

// Perform Search
async function performSearch() {
    const query = searchInput.value.trim();

    if (!query) {
        showError('Please enter a research query');
        return;
    }

    // Show loading, hide results and errors
    showLoading();
    hideError();
    hideResults();

    try {
        const topK = parseInt(topKInput.value) || 10;

        const response = await fetch(`${API_BASE_URL}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                top_k: topK,
                include_publications: true
            })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        displayResults(data);

    } catch (error) {
        console.error('Search error:', error);
        showError(`Search failed: ${error.message}. Make sure the API server is running at ${API_BASE_URL}`);
    } finally {
        hideLoading();
    }
}

// Display Results
function displayResults(data) {
    if (!data.results || data.results.length === 0) {
        showError('No advisors found for your query. Try different keywords.');
        return;
    }

    // Update results info
    resultsInfo.textContent = `Found ${data.total_results} advisor${data.total_results !== 1 ? 's' : ''} for "${data.query}" (${data.search_time_ms.toFixed(0)}ms)`;

    // Clear previous results
    resultsContainer.innerHTML = '';

    // Create professor cards
    data.results.forEach((professor, index) => {
        const card = createProfessorCard(professor, index + 1);
        resultsContainer.appendChild(card);
    });

    // Show results section
    showResults();
}

// Create Professor Card
function createProfessorCard(professor, rank) {
    const card = document.createElement('div');
    card.className = 'professor-card';

    // Score percentage for display
    const scorePercent = (professor.final_score * 100).toFixed(1);

    card.innerHTML = `
        <div class="professor-header">
            <div class="professor-info">
                <h3>${rank}. ${professor.name}</h3>
                <div class="professor-meta">
                    ${professor.department} • ${professor.college}
                </div>
            </div>
            <div class="score-badge">
                Score: ${scorePercent}%
            </div>
        </div>
        
        <div class="professor-details">
            ${professor.interests ? `
                <div class="detail-row">
                    <span class="detail-label">Research Interests:</span>
                    <span class="detail-value">${truncateText(professor.interests, 200)}</span>
                </div>
            ` : ''}
            
            <div class="detail-row">
                <span class="detail-label">Matching Papers:</span>
                <span class="detail-value">${professor.num_matching_papers}</span>
            </div>
            
            ${professor.url ? `
                <div class="detail-row">
                    <span class="detail-label">Profile:</span>
                    <span class="detail-value">
                        <a href="${professor.url}" target="_blank">View Faculty Page →</a>
                    </span>
                </div>
            ` : ''}
        </div>
        
        <div class="score-breakdown">
            <div class="score-item">
                <div class="score-item-label">Similarity</div>
                <div class="score-item-value">${(professor.avg_similarity * 100).toFixed(1)}%</div>
            </div>
            <div class="score-item">
                <div class="score-item-label">Recency</div>
                <div class="score-item-value">${(professor.recency_weight * 100).toFixed(1)}%</div>
            </div>
            <div class="score-item">
                <div class="score-item-label">Activity</div>
                <div class="score-item-value">+${(professor.activity_bonus * 100).toFixed(1)}%</div>
            </div>
        </div>
        
        ${professor.top_publications && professor.top_publications.length > 0 ? `
            <div class="publications-section">
                <h4>Top Matching Publications</h4>
                ${professor.top_publications.map(pub => createPublicationHTML(pub)).join('')}
            </div>
        ` : ''}
    `;

    return card;
}

// Create Publication HTML
function createPublicationHTML(publication) {
    return `
        <div class="publication-item">
            <div class="publication-title">${publication.title}</div>
            <div class="publication-meta">
                <span>${publication.year || 'N/A'}</span>
                <span>•</span>
                <span>${publication.citations || 0} citations</span>
                ${publication.venue ? `
                    <span>•</span>
                    <span>${publication.venue}</span>
                ` : ''}
                <span>•</span>
                <span class="similarity-score">Similarity: ${(publication.similarity * 100).toFixed(1)}%</span>
            </div>
        </div>
    `;
}

// Utility Functions
function showLoading() {
    loadingSpinner.classList.remove('hidden');
}

function hideLoading() {
    loadingSpinner.classList.add('hidden');
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
}

function hideError() {
    errorMessage.classList.add('hidden');
}

function showResults() {
    resultsSection.classList.remove('hidden');
}

function hideResults() {
    resultsSection.classList.add('hidden');
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Check API Health on Load
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            console.log('✓ API server is running');
        }
    } catch (error) {
        console.warn('⚠ API server not reachable. Make sure to start it with: cd app && python3 api.py');
    }
}

// Initialize
checkAPIHealth();
