// Initialize Dexie Database
const db = new Dexie("BiblioDriftDB");

// Define schema: Store books by 'id' 
// We index title, author, and mood to make search and retrieval lightning-fast offline
db.version(1).stores({
    books: 'id, title, author, content, mood, coverUrl'
});

// Export the database instance to use across library scripts
export default db;