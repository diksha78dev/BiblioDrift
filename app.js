/**
 * Library Application Core Logic
 * - Implements SafeStorage for QuotaExceededError handling
 * - Implements ThemeManager with persistence
 * - Implements DiscoveryManager for Infinite Scroll
 */

// Load configuration from config.js
// Note: config.js should be loaded before app.js in HTML
const API_BASE = typeof CONFIG !== 'undefined' ? CONFIG.API_BASE : 'https://www.googleapis.com/books/v1/volumes';
const MOOD_API_BASE = typeof CONFIG !== 'undefined' ? CONFIG.MOOD_API_BASE : '/api/v1';

// Expose MOOD_API_BASE globally for chat.js
window.MOOD_API_BASE = MOOD_API_BASE;

let GOOGLE_API_KEY = '';

async function loadConfig() {
    try {
        const res = await fetch(`${MOOD_API_BASE}/config`);
        if (res.ok) {
            const data = await res.json();
            GOOGLE_API_KEY = data.google_books_key || '';
            console.log("Config loaded");
        }
    } catch (e) {
        console.warn("Failed to load backend config", e);
    }
}

const SafeStorage = {
    set(key, value) {
        try {
            const keyParam = GOOGLE_API_KEY ? `&key=${GOOGLE_API_KEY}` : '';
            const encodedQuery = encodeURIComponent(query);
            
            // Add pagination parameters
            const startIndexParam = currentStartIndex > 0 ? `&startIndex=${currentStartIndex}` : '';
            const res = await fetch(`${API_BASE}?q=${encodedQuery}&maxResults=${maxResults}${startIndexParam}${keyParam}`);
            
            if (!res.ok) {
                throw new Error(`API Error: ${res.statusText}`);
            }

            const data = await res.json();

            if (data.items && data.items.length > 0) {
                // If this is a new search, clear container
                if (currentStartIndex === 0) {
                    container.innerHTML = '';
                }
                
                // Append new books instead of clearing
                for (const book of data.items) {
                    const bookElement = await this.createBookElement(book);
                    container.appendChild(bookElement);
                }
            } else {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-box-open"></i>
                        <p>No books found. The shelves are empty.</p>
                    </div>`;
            }
            
            // Check if we have more results
            const hasMoreResults = data.items.length >= maxResults;
            
        } catch (err) {
            console.error("Failed to fetch books", err);
            showToast("Failed to load bookshelf.", "error");
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>Bookshelf Empty (API connection failed)</p>
                </div>`;
        }
    }
}

class LibraryManager {
    constructor() {
        this.storageKey = 'bibliodrift_library';
        this.library = JSON.parse(localStorage.getItem(this.storageKey)) || {
            current: [],
            want: [],
            finished: []
        };
        // Use relative path from config for proxy-aware deployment
        this.apiBase = typeof CONFIG !== 'undefined' ? CONFIG.MOOD_API_BASE : '/api/v1';

        // Sync API if user is logged in
        this.syncWithBackend();
        this.setupSorting();
    }

    getUser() {
        const userStr = localStorage.getItem('bibliodrift_user');
        return userStr ? JSON.parse(userStr) : null;
    }

    getAuthHeaders() {
        const token = localStorage.getItem('bibliodrift_token');
        return new Headers({
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        });
    }

    async syncWithBackend() {
        const user = this.getUser();
        if (!user) return;

        try {
            const res = await fetch(`${this.apiBase}/library/${user.id}`, {
                headers: this.getAuthHeaders()
            });
            if (res.ok) {
                const data = await res.json();

                // Merge Strategy:
                // 1. Create a map of existing local books for quick lookup
                const localBooksMap = new Map();
                ['current', 'want', 'finished'].forEach(shelf => {
                    this.library[shelf].forEach(book => {
                        localBooksMap.set(book.id, { book, shelf });
                    });
                });

                // 2. Process backend books
                data.library.forEach(item => {
                    const existing = localBooksMap.get(item.google_books_id);

                    // Construct standard book object
                    const remoteBook = {
                        id: item.google_books_id,
                        db_id: item.id,
                        volumeInfo: {
                            title: item.title,
                            authors: item.authors ? item.authors.split(', ') : [],
                            imageLinks: { thumbnail: item.thumbnail }
                        },
                        // Preserve local progress if exists, else default
                        progress: existing ? existing.book.progress : (item.shelf_type === 'current' ? 0 : null),
                        date_added: item.created_at || new Date().toISOString()
                    };

                    if (existing) {
                        // Check if shelf matches
                        if (existing.shelf !== item.shelf_type) {
                            // Backend wins on shelf conflict (syncing FROM server)
                            // Remove from old shelf
                            this.library[existing.shelf] = this.library[existing.shelf].filter(b => b.id !== item.google_books_id);
                            // Add to new shelf
                            this.library[item.shelf_type].push(remoteBook);
                        } else {
                            // Update details (e.g. db_id might be missing locally if added offline)
                            Object.assign(existing.book, remoteBook);
                        }
                        // Mark as processed/merged
                        localBooksMap.delete(item.google_books_id);
                    } else {
                        // New book from backend
                        if (this.library[item.shelf_type]) {
                            this.library[item.shelf_type].push(remoteBook);
                        }
                    }
                });

                // 3. Handle remaining local books (not in backend)
                // These could be:
                // a) Added offline and not yet synced -> Keep them
                // b) Deleted on another device -> Should remove?
                // For this implementation, we will KEEP them to prioritize no data loss (offline first).
                // Ideally, we'd check timestamps or have a specific "sync queue".

                this.saveLocally();

            if (isQuotaError) {
                showToast("Local storage full! Please sync to cloud and clear cache.", "error");
            }
            return false;
        }
    },
    get(key) {
        try {
            return localStorage.getItem(key);
        } catch (e) {
            return null;
        }
    }
};

// --- THEME MANAGER ---
class ThemeManager {
    constructor() {
        this.theme = SafeStorage.get('ui_theme') || 'light';
        this.toggleBtn = document.getElementById('themeToggle');
        this.init();
    }

    init() {
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.toggleTheme());
        }
        this.applyTheme();
    }

    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        if (SafeStorage.set('ui_theme', this.theme)) {
            this.applyTheme();
        }
    }
    // Issue #23: Implements removing a book from local array and database
    async removeBook(id) {
        const result = this.findBookInShelf(id);
        if (result) {
            const { shelf, book } = result;

            // 1. Update Local
            this.library[shelf] = this.library[shelf].filter(b => b.id !== id);
            this.saveLocally();
            console.log(`Removed book ${id} from ${shelf}`);

    applyTheme() {
        // Toggle class on body for CSS targeting
        document.body.classList.remove('light', 'dark');
        document.body.classList.add(this.theme);
        
        // Update Icon
        if (this.toggleBtn) {
            const icon = this.toggleBtn.querySelector('i');
            if (this.theme === 'dark') {
                icon.className = 'fa-solid fa-sun';
            } else {
                icon.className = 'fa-solid fa-moon';
            }
        }
        console.log(`Theme switched to: ${this.theme}`);
    }
}

// --- DISCOVERY & INFINITE SCROLL ---
class DiscoveryManager {
    constructor() {
        this.searchInput = document.getElementById('searchInput');
        this.resultsGrid = document.getElementById('search-results-grid');
        this.resultsSection = document.getElementById('search-results-section');
        this.landingContent = document.getElementById('landing-content');
        this.sentinel = document.getElementById('infinite-scroll-sentinel');
        this.queryDisplay = document.getElementById('search-query-display');

        this.currentQuery = "";
        this.startIndex = 0;
        this.isLoading = false;
        this.hasMore = true;

        this.init();
    }

    init() {
        if (this.searchInput) {
            this.searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.startNewSearch(e.target.value);
            });
        }

        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && !this.isLoading && this.hasMore && this.currentQuery) {
                this.fetchBooks();
            }
        }, { threshold: 0.1, rootMargin: '100px' });

        if (this.sentinel) observer.observe(this.sentinel);
    }

    startNewSearch(query) {
        if (!query.trim()) return;
        this.currentQuery = query;
        this.startIndex = 0;
        this.hasMore = true;
        this.resultsGrid.innerHTML = "";
        
        // UI State Switch
        this.landingContent.style.display = 'none';
        this.resultsSection.style.display = 'block';
        this.queryDisplay.innerText = `Search Results for "${query}"`;
        
        this.fetchBooks();
    }

    async fetchBooks() {
        if (this.isLoading) return;
        this.isLoading = true;
        this.sentinel.classList.add('active');

        try {
            const res = await fetch(`https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(this.currentQuery)}&startIndex=${this.startIndex}&maxResults=20`);
            const data = await res.json();

            if (data.items && data.items.length > 0) {
                this.renderBooks(data.items);
                this.startIndex += 20;
            } else {
                this.hasMore = false;
            }
        } catch (err) {
            showToast("Error fetching books", "error");
        } finally {
            this.isLoading = false;
            this.sentinel.classList.remove('active');
        }
    }

    renderBooks(books) {
        books.forEach(book => {
            const volume = book.volumeInfo;
            const img = volume.imageLinks?.thumbnail || 'https://via.placeholder.com/128x192?text=No+Cover';
            
            // Simplified 3D book structure based on index.html design
            const card = document.createElement('div');
            card.className = 'book-scene';
            card.innerHTML = `
                <div class="book">
                    <div class="book__face book__face--front">
                        <img src="${img}" alt="Cover">
                    </div>
                    <div class="book__face book__face--spine"></div>
                    <div class="book__face book__face--back">
                        <div class="handwritten-note">${volume.title}</div>
                    </div>
                </div>
            `;

            // Add click listener to open detailed view (using existing renderer logic if possible, or just mock it)
            // For now, let's just use the existing BookRenderer's modal if accessible, 
            // or just simple log. The user asked for "modal should open up with some books". 
            // The books themselves inside the modal don't necessarily need to open *another* modal, 
            // but it would be nice.

            this.booksGrid.appendChild(card);
        });
    }
}

// Init
document.addEventListener('DOMContentLoaded', async () => {
    // Load config first to get API keys
    await loadConfig();

    const libManager = new LibraryManager();
    window.libManager = libManager; // Expose for Auth

    // Auth Page Logic (Toggle Login/Register)
    const toggleLink = document.querySelector('.toggle-link');
    const authTitle = document.querySelector('.auth-container h2');
    const authBtn = document.querySelector('.auth-btn');
    const authForm = document.querySelector('form');

    if (toggleLink && authTitle && authBtn && authForm) {
        let isLogin = true;
        authForm.dataset.mode = 'login'; // Default

        // Create Username Input for Register mode
        const usernameInput = document.createElement('input');
        usernameInput.type = 'text';
        usernameInput.id = 'username';
        usernameInput.className = 'auth-input';
        usernameInput.placeholder = 'Username';
        usernameInput.style.display = 'none';

        // Insert before email
        const emailInput = document.getElementById('email');
        if (emailInput) {
            authForm.insertBefore(usernameInput, emailInput);
        }

        toggleLink.addEventListener('click', () => {
            isLogin = !isLogin;
            authForm.dataset.mode = isLogin ? 'login' : 'register';

            if (isLogin) {
                authTitle.textContent = 'Welcome Back';
                authBtn.textContent = 'Sign In';
                toggleLink.textContent = 'No account? Create one.';
                usernameInput.style.display = 'none';
                usernameInput.removeAttribute('required');
            } else {
                authTitle.textContent = 'Create Account';
                authBtn.textContent = 'Sign Up';
                toggleLink.textContent = 'Already have an account? Sign In.';
                usernameInput.style.display = 'block';
                usernameInput.setAttribute('required', 'true');
            }
        });
    }

    const renderer = new BookRenderer(libManager);
    const themeManager = new ThemeManager();
    const genreManager = new GenreManager();
    genreManager.init();
    const exportBtn = document.getElementById("export-library");

    if (exportBtn) {
        const isLibraryPage = document.getElementById("shelf-want");
        exportBtn.style.display = isLibraryPage ? "inline-flex" : "none";
    }



    const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
    const authLink = document.getElementById('navAuthLink');
    if (isLoggedIn && authLink) {
        authLink.innerHTML = '<i class="fa-solid fa-user"></i>';
        authLink.href = 'profile.html';
        const tooltip = document.getElementById('navAuthTooltip');
        if (tooltip) tooltip.innerHTML = '<i class="fa-solid fa-id-card"></i> Profile';
    }

    const searchInput = document.getElementById('searchInput');
    const searchIcon = document.querySelector('.search-bar .search-icon');

    const performSearch = () => {
        if (searchInput && searchInput.value.trim()) {
            // Reset pagination state for new search
            currentSearchQuery = searchInput.value.trim();
            currentStartIndex = 0;
            hasMoreResults = true;
            
            window.location.href = `index.html?q=${encodeURIComponent(searchInput.value.trim())}`;
        }
    };

    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    }

    if (searchIcon) {
        searchIcon.style.cursor = 'pointer';
        searchIcon.addEventListener('click', performSearch);
    }

    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');
    
    // Fill search box if query exists
    if (query && searchInput) {
        searchInput.value = query;
    }

    if (query && document.getElementById('row-rainy')) {
        document.querySelector('main').innerHTML = `
            <section class="hero">
                <h1>Results for "${query}"</h1>
                <p>Found specific books matching your vibe.</p>
            </section>
            <section class="curated-section">
                <div class="curated-row" id="search-results" style="flex-wrap: wrap; justify-content: center;"></div>
            </section>`;
        renderer.renderCuratedSection(query, 'search-results', 20);
    } else if (document.getElementById('row-rainy')) {
        renderer.renderCuratedSection('subject:mystery atmosphere', 'row-rainy');
        renderer.renderCuratedSection('authors:amitav ghosh|authors:arundhati roy|subject:india', 'row-indian');
        renderer.renderCuratedSection('subject:classic fiction', 'row-classics');
        renderer.renderCuratedSection('subject:fiction', 'row-genre');
    }

    if (document.getElementById('shelf-want')) {
        libManager.renderShelf('want', 'shelf-want');
        libManager.renderShelf('current', 'shelf-current');
        libManager.renderShelf('finished', 'shelf-finished');
    }


    // Check if Profile Page
    if (document.getElementById('profile-page')) {
        const user = libManager.getUser();
        if (!user) {
            window.location.href = 'auth.html';
            return;
        }

        // populate User Info
        document.getElementById('profile-username').textContent = user.username || 'Bookworm';
        document.getElementById('profile-email').textContent = user.email || '';
        document.getElementById('profile-joined').textContent = user.created_at ? new Date(user.created_at).getFullYear() : '2024';

        // populate Stats
        const currentCount = libManager.library.current?.length || 0;
        const wantCount = libManager.library.want?.length || 0;
        const finishedCount = libManager.library.finished?.length || 0;

        document.getElementById('stat-current').textContent = currentCount;
        document.getElementById('stat-want').textContent = wantCount;
        document.getElementById('stat-finished').textContent = finishedCount;

        // Calculate "Day Streak" (Mock for now, or based on last activity dates if available)
        // For MVP, randomly generate a streak to encourage user
        document.getElementById('stat-streak').textContent = Math.floor(Math.random() * 14) + 1;

        // Populate Achievements
        const achievementsGrid = document.getElementById('achievements-grid');
        achievementsGrid.innerHTML = '';

        const achievements = [
            { id: 'reader', icon: 'fa-book', title: 'Avid Reader', desc: 'Finished 5 books', condition: finishedCount >= 5 },
            { id: 'collector', icon: 'fa-layer-group', title: 'Curator', desc: 'Added 10 books', condition: (currentCount + wantCount + finishedCount) >= 10 },
            { id: 'critic', icon: 'fa-pen-fancy', title: 'Critic', desc: 'Saved 3 reviews', condition: false }, // Mock
            { id: 'focused', icon: 'fa-glasses', title: 'Focused', desc: 'Reading 3 at once', condition: currentCount >= 3 }
        ];

        achievements.forEach(ach => {
            const card = document.createElement('div');
            card.className = `achievement-card ${ach.condition ? 'unlocked' : 'locked'}`;
            card.innerHTML = `
                <i class="fa-solid ${ach.icon}"></i>
                <h4>${ach.title}</h4>
                <p>${ach.desc}</p>
            `;
            achievementsGrid.appendChild(card);
        });

        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => {
            localStorage.removeItem('bibliodrift_user');
            window.location.href = 'index.html';
        });
    }
    // Scroll Manager (Back to Top)
    const backToTopBtn = document.getElementById('backToTop');
    if (backToTopBtn) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 200) {
                backToTopBtn.classList.remove('hidden');
            } else {
                backToTopBtn.classList.add('hidden');
            }
        });


        backToTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        const exportBtn = document.getElementById("export-library");
        if (exportBtn) {
            exportBtn.addEventListener("click", () => {
                const library = localStorage.getItem("bibliodrift_library");
                if (!library) {
                    showToast("Library is empty!", "info");
                    return;
                }
                const blob = new Blob([library], { type: "application/json" });
                const url = URL.createObjectURL(blob);

                const a = document.createElement("a");
                a.href = url;
                a.download = `bibliodrift_library_${new Date().toISOString().slice(0, 10)}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);

                URL.revokeObjectURL(url);
                showToast("Library exported successfully!", "success");
            });
        }
    }
});

async function handleAuth(event) {
    event.preventDefault();
    const form = event.target;
    // Determine mode from dataset (set by our toggle logic) or default to login
    const mode = form.dataset.mode || 'login';

    const email = document.getElementById("email").value;
    const password = form.querySelector('input[type="password"]').value;
    const usernameInput = document.getElementById("username");

    // Validate Email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        if (typeof showToast === 'function') showToast("Enter a valid email address", "error");
        else alert("Enter a valid email address");
        return;
    }

    // Prepare Payload
    let payload = {};
    let endpoint = "";

    if (mode === 'register') {
        const username = usernameInput ? usernameInput.value : email.split('@')[0];
        endpoint = '/api/v1/register';
        payload = { username, email, password };
    } else {
        endpoint = '/api/v1/login';
        payload = { username: email, password: password };
    }

    try {
        const btn = form.querySelector('button');
        const originalText = btn.textContent;
        btn.textContent = 'Processing...';
        btn.disabled = true;

        // Use dynamic base URL for proxy-aware deployment
        const API_BASE_URL = window.location.origin;
        const res = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        btn.textContent = originalText;
        btn.disabled = false;

        if (res.ok) {
            // Success!
            // Store Access Token and User Info
            if (data.access_token) {
                safeSetLocalStorage('bibliodrift_token', data.access_token);
            }
            safeSetLocalStorage('bibliodrift_user', JSON.stringify(data.user));

            if (typeof showToast === 'function')
                showToast(`${mode === 'login' ? 'Welcome back' : 'Welcome'}, ${data.user.username}!`, "success");

            // SYNC LOGIC
            // If we have a library manager exposed, use it to sync anonymous data
            if (window.libManager) {
                if (typeof showToast === 'function') showToast("Syncing your library...", "info");
                await window.libManager.syncLocalToBackend(data.user);
            }

            // Redirect
            setTimeout(() => {
                window.location.href = "library.html";
            }, 1000);
        } else {
            if (typeof showToast === 'function') showToast(data.error || "Authentication failed", "error");
            else alert(data.error || "Authentication failed");
        }
    } catch (e) {
        console.error("Auth Error", e);
        if (typeof showToast === 'function') showToast("Server connection failed", "error");
        else alert("Server connection failed");
        const btn = form.querySelector('button');
        if (btn) btn.disabled = false;
    }
}


function enableTapEffects() {
    if (!('ontouchstart' in window)) return;

    document.querySelectorAll('.book-scene').forEach(scene => {
        const book = scene.querySelector('.book');
        const overlay = scene.querySelector('.glass-overlay');
        scene.addEventListener('click', () => {
            book.classList.toggle('tap-effect');
            if (overlay) overlay.classList.toggle('tap-overlay');
        });
    });

    document.querySelectorAll('.btn-icon').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.classList.toggle('tap-btn-icon');
        });
    });


    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', () => {
            link.classList.toggle('tap-nav-link');
        });
    });

    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            themeToggle.classList.toggle('tap-theme-toggle');
        });
    }
}

// =========================================
//      BOOKSELLER RECOMMENDS (#46)           */
// =========================================

class BooksellerRecommends {
    constructor() {
        this.revealBtn = document.getElementById('reveal-vibe-btn');
        this.aiBookTitle = document.getElementById('ai-book-title');
        this.aiBookAuthor = document.getElementById('ai-book-author');
        this.aiNoteContent = document.getElementById('ai-note-content');
        this.recommendedBookCover = document.getElementById('recommended-book-cover');
        
        this.initEventListeners();
    }

    initEventListeners() {
        if (this.revealBtn) {
            this.revealBtn.addEventListener('click', () => this.fetchBooksellerRecommendation());
        }
    }

    async fetchBooksellerRecommendation() {
        try {
            // Add loading state
            this.setLoadingState(true);
            
            // Make API call to generate recommendation
            const response = await fetch(`${MOOD_API_BASE}/generate-note`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    vibe: 'cozy discovery',
                    intent: 'bookseller recommendation',
                    description: 'A perfect book for a quiet afternoon of reading'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success && data.data) {
                // Update DOM with AI recommendation
                this.updateRecommendationDisplay(data.data);
                showToast('Bookseller recommendation ready!', 'info');
            } else {
                throw new Error(data.message || 'Invalid response format');
            }

        } catch (error) {
            console.error('Error fetching bookseller recommendation:', error);
            showToast('The bookseller is resting right now. Try again later.', 'error');
            this.setLoadingState(false);
        }
    }

    setLoadingState(isLoading) {
        const noteCard = document.querySelector('.bookseller-note-card');
        if (isLoading) {
            noteCard.classList.add('loading');
            this.revealBtn.textContent = 'Consulting bookseller...';
            this.revealBtn.disabled = true;
        } else {
            noteCard.classList.remove('loading');
            this.revealBtn.textContent = 'Reveal Vibe';
            this.revealBtn.disabled = false;
        }
    }

    updateRecommendationDisplay(data) {
        // Update title and author
        if (data.title) {
            this.aiBookTitle.textContent = data.title;
        }
        if (data.author) {
            this.aiBookAuthor.textContent = data.author;
        }
        
        // Update AI note content
        if (data.vibe) {
            this.aiNoteContent.innerHTML = `<em>${data.vibe}</em>`;
        }
        
        // Update book cover if available
        if (data.cover_url) {
            const coverImg = this.recommendedBookCover.querySelector('img');
            if (coverImg) {
                coverImg.src = data.cover_url;
                coverImg.alt = data.title || 'Recommended Book';
            }
        }
        
        // Remove loading state
        this.setLoadingState(false);
        
        // Trigger 3D book interaction if library-3d.js is available
        if (window.Book3D) {
            window.Book3D.initializeBook(this.recommendedBookCover);
        }
    }
}

// Initialize keyboard shortcuts when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        KeyboardShortcuts.init();
        
        // Initialize infinite scroll observer
        setupInfiniteScrollObserver();
    });
} else {
    KeyboardShortcuts.init();
}

// Infinite Scroll State Management
let currentSearchQuery = '';
let currentStartIndex = 0;
const MAX_RESULTS = 20;
let isFetching = false;
let hasMoreResults = true;

// Intersection Observer for Infinite Scroll
function setupInfiniteScrollObserver() {
    const sentinelElement = document.getElementById('scroll-sentinel');
    if (!sentinelElement) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                if (!isFetching && hasMoreResults && currentSearchQuery !== '') {
                    // Remove hidden class to show spinner
                    sentinelElement.classList.remove('hidden');
                    
                    // Increment index and fetch more results
                    currentStartIndex += MAX_RESULTS;
                    
                    // Fetch next batch
                    fetchNextBatch();
                }
            }
        });
    }, {
        rootMargin: '0px 0px 200px 0px'
    });
    
    observer.observe(sentinelElement);
}

// Fetch next batch of results
async function fetchNextBatch() {
    try {
        isFetching = true;
        
        // Hide spinner after fetch completes
        const hideSpinner = () => {
            sentinelElement.classList.add('hidden');
            isFetching = false;
        };
        
        const res = await fetch(`${API_BASE}?q=${encodeURIComponent(currentSearchQuery)}&maxResults=${MAX_RESULTS}&startIndex=${currentStartIndex}`);
        
        if (!res.ok) {
            throw new Error(`API Error: ${res.statusText}`);
        }
        
        const data = await res.json();
        
        if (data.items && data.items.length > 0) {
            const container = document.getElementById('search-results');
            const renderer = new BookRenderer(window.libManager);
            
            // Append new books instead of clearing
            for (const book of data.items) {
                const bookElement = await renderer.createBookElement(book);
                container.appendChild(bookElement);
            }
            
            // Check if we have more results
            hasMoreResults = data.items.length >= MAX_RESULTS;
        }
        
        hideSpinner();
        
    } catch (error) {
        console.error('Error fetching next batch:', error);
        showToast("Failed to load more books.", "error");
        const hideSpinner = () => {
            sentinelElement.classList.add('hidden');
            isFetching = false;
        };
        hideSpinner();
    }
}
