import streamlit as st
import json
import csv
from io import StringIO
import os
import re

# Initialize session state for glossary
if 'glossary' not in st.session_state:
    # Default glossary with common terms that should not be translated
    st.session_state.glossary = {
        'product_names': [
            'Deriv',
            'Deriv App',
            'Deriv Bot',
            'Deriv GO',
            'Deriv Life',
            'Deriv Blog',
            'Deriv X',
            'Deriv cTrader',
            'MT5',
            'P2P',
            'SmartTrader',
            'Deriv Trader',
            'Binary Bot'
        ],
        'technical_terms': [
            # Web Technologies
            'API',
            'URL',
            'HTTP',
            'HTTPS',
            'SSL',
            'TLS',
            'JSON',
            'XML',
            'REST',
            'RESTful',
            'SOAP',
            'WebSocket',
            'WS',
            'WSS',
            'GET',
            'POST',
            'PUT',
            'DELETE',
            'OAuth',
            'Passkey',
            
            # Web Browsers & Tools
            'Google Chrome',
            'Firefox',
            'Safari',
            'Edge',
            'Chrome DevTools',
            
            # Cloud & Storage
            'Google Drive',
            'Dropbox',
            'iCloud',
            'AWS',
            'Azure',
            
            # Development Frameworks & Libraries
            'Flutter',
            'React',
            'Angular',
            'Vue.js',
            'Node.js',
            'Express.js',
            'Django',
            'Flask',
            
            # Security
            'CORS',
            'XSS',
            'CSRF',
            'JWT',
            'SSH',
            'VPN',
            
            # Database
            'SQL',
            'NoSQL',
            'MongoDB',
            'PostgreSQL',
            'MySQL',
            'Redis',
            
            # File Types
            'CSV',
            'PDF',
            'ZIP',
            'RAR',
            'JPG',
            'PNG',
            'SVG',
            
            # Protocols
            'FTP',
            'SMTP',
            'POP3',
            'IMAP',
            'TCP/IP',
            'UDP',
            
            # Mobile Development
            'iOS',
            'Android',
            'APK',
            'IPA'
        ],
        'awards_name': [
            'Affiliate Program of the Year',
            'Best Customer Service - Global',
            'Best Latam Region Broker',
            'Best Partner Programme',
            'Best Trading Experience',
            'Best Trading Experience (LATAM) 2024',
            'Broker of the Year - Global',
            'Finance Magnates 2024',
            'Forex Expo Dubai 2024',
            'FX&Trust Score Awards 2024',
            'Global Forex Awards',
            'Global Forex Awards 2024',
            'Most Innovative Broker',
            'Most Innovative Broker— MEA 2025',
            'Most Trusted Broker',
            'UF Awards 2024'
        ],
        'address': [
            "17 Rue d'Antin, 75002 Paris",
            "181, Leoforos Archiepiskopou Makariou III Avenue 15 Business Centre, 1st Floor, 3030, Limassol Cyprus",
            "2nd Floor, Suite 2, Omar Hodge Building, 325 Waterfront Drive, Road Town, Tortola, VG 1110, British Virgin Islands",
            "67-1 & 69-1, Jalan KLJ 6, Taman Kota Laksamana Jaya, Melaka 75200",
            "72 Limassol Avenue, 12th floor, Asteroid Business Centre, 2014 Strovolos, Nicosia",
            "80 Robinson Road, #11-03, Singapore 068898",
            "AJIB Building, No 12A & 12B, 3rd Floor, Al Bonouk Street, Al Abdali Boulevard, Amman - Jordan.",
            "Cayman Enterprise City, Strathvale House, 2nd Floor, 90N Church St, George Town, Cayman Islands",
            "Deriv HQ, 3500, Jalan Teknokrat 3, 63000 Cyberjaya, Selangor",
            "Deriv Technologies Limited, Apex Forbury Road, Reading RG1 1AX",
            "E-5-6, Soho Ipoh 2, Jalan Sultan Idris Shah, Ipoh 30000, Perak",
            "Edificio Atrium, Piso 2, Guido Spano Esq. Doctor Morra, Asunción 1849",
            "F16, Level 1, Paragon Labuan, Jalan Tun Mustapha, Labuan 87000, Sabah",
            "First Floor, 68 - 72 Leonard Street, London, EC2A 4QX",
            "Kemperplatz 1 Mitte D, 10785 Berlin, Germany",
            "Level 2 East Wing, Kigali Heights, KG7 Avenue, Kigali",
            "Level 3, W Business Centre, Triq Dun Karm, Birkirkara, BKR 9033",
            "Nicosia",
            "No. 1-23A, First Floor, Paragon, Jalan Tun Mustapha, 87008, Federal Territory of Labuan, Malaysia.",
            "Office 1902, Jumeirah Business Center 1, JLT Cluster G",
            "Room 408A, Empire Centre, 68 Mody Road, Tsim Sha Tsui East, Kowloon, Hong Kong",
            "Suite 5, One Cornet Street, St Peter Port, Guernsey GY1 1 BZ",
            "World Trade Center Ciudad del Este",
            "Yumiwork, Lolam building, Kumul Highway, Land # 11/OD22/021, Port Vila, Vanuatu"
        ],
        'list_of_people': [  # New category
            'Jean Yeas',
            'Rakshit',
            'Chris Horn',
            'Derrick'
        ],
        'custom_terms': []  # For user-added terms
    }

# Add to session state initialization
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'page_size' not in st.session_state:
    st.session_state.page_size = 10
if 'current_page' not in st.session_state:
    st.session_state.current_page = {}  # Dictionary to store current page for each category

def save_glossary_to_file():
    """Save the current glossary to a JSON file"""
    try:
        with open('glossary.json', 'w') as f:
            json.dump(st.session_state.glossary, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving glossary: {str(e)}")
        return False

def load_glossary_from_file():
    """Load the glossary from a JSON file"""
    try:
        with open('glossary.json', 'r') as f:
            st.session_state.glossary = json.load(f)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        st.error(f"Error loading glossary: {str(e)}")
        return False

def export_glossary_to_csv():
    """Export the glossary to a CSV file"""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Category', 'Term'])
    
    for category, terms in st.session_state.glossary.items():
        for term in terms:
            writer.writerow([category, term])
    
    return output.getvalue()

def import_glossary_from_csv(csv_file):
    """Import glossary from a CSV file"""
    try:
        content = csv_file.getvalue().decode('utf-8')
        csv_reader = csv.reader(StringIO(content))
        next(csv_reader)  # Skip header row
        
        # Start with existing structure but empty lists
        new_glossary = {
            'product_names': [],
            'technical_terms': [],
            'awards_name': [],
            'address': [],
            'list_of_people': [],  # Add new category here too
            'custom_terms': []
        }
        
        # Process each row in the CSV
        for row in csv_reader:
            if len(row) == 2:
                category, term = row
                
                # Create category if it doesn't exist
                if category not in new_glossary:
                    new_glossary[category] = []
                
                # Add term to appropriate category
                new_glossary[category].append(term)
        
        st.session_state.glossary = new_glossary
        save_glossary_to_file()
        return True
    except Exception as e:
        st.error(f"Error importing glossary: {str(e)}")
        return False

def main():
    st.title("Translation Glossary Manager")
    st.write("""
    Manage terms that should not be translated during the translation process. 
    These terms will be preserved in their original form.
    """)
    
    # Load existing glossary if available
    if os.path.exists('glossary.json'):
        load_glossary_from_file()
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "View Glossary", 
        "Add/Remove Terms", 
        "Import/Export",
        "Settings"
    ])
    
    with tab1:
        st.header("Current Glossary")
        
        # Add search functionality
        search_query = st.text_input("Search terms", 
                                    placeholder="Type to search...",
                                    value=st.session_state.search_query)
        st.session_state.search_query = search_query
        
        # Display each category in an expander
        for category, terms in st.session_state.glossary.items():
            # Initialize current page for this category if not exists
            if category not in st.session_state.current_page:
                st.session_state.current_page[category] = 0
                
            # Filter terms based on search query
            if search_query:
                filtered_terms = [term for term in terms if search_query.lower() in term.lower()]
            else:
                filtered_terms = terms
                
            # Sort terms alphabetically
            sorted_terms = sorted(filtered_terms)
            
            # Calculate pagination
            total_pages = max(1, (len(sorted_terms) + st.session_state.page_size - 1) // st.session_state.page_size)
            
            # Ensure current page is valid
            if st.session_state.current_page[category] >= total_pages:
                st.session_state.current_page[category] = max(0, total_pages - 1)
            
            # Get terms for current page
            start_idx = st.session_state.current_page[category] * st.session_state.page_size
            end_idx = min(start_idx + st.session_state.page_size, len(sorted_terms))
            page_terms = sorted_terms[start_idx:end_idx]
            
            # Display category with pagination info
            with st.expander(f"{category.replace('_', ' ').title()} ({len(filtered_terms)} terms)"):
                if filtered_terms:
                    # Show pagination controls if needed
                    if total_pages > 1:
                        col1, col2, col3 = st.columns([1, 3, 1])
                        with col1:
                            if st.button("← Previous", key=f"prev_{category}", 
                                        disabled=st.session_state.current_page[category] == 0):
                                st.session_state.current_page[category] -= 1
                                st.rerun()
                        
                        with col2:
                            # Center the pagination text
                            st.markdown(f"<div style='text-align: center;'>Page {st.session_state.current_page[category] + 1} of {total_pages}</div>", unsafe_allow_html=True)
                        
                        with col3:
                            if st.button("Next →", key=f"next_{category}", 
                                        disabled=st.session_state.current_page[category] == total_pages - 1):
                                st.session_state.current_page[category] += 1
                                st.rerun()
                    
                    # Display terms with numbering
                    for i, term in enumerate(page_terms):
                        global_idx = start_idx + i + 1
                        # Highlight search term if present
                        if search_query and search_query.lower() in term.lower():
                            # Fix the split operation - don't use flags parameter directly
                            pattern = re.compile(re.escape(search_query), re.IGNORECASE)
                            term_parts = pattern.split(term)
                            highlighted_term = f"**{search_query}**".join(term_parts)
                            st.markdown(f"{global_idx}. {highlighted_term}")
                        else:
                            st.write(f"{global_idx}. {term}")
                else:
                    if search_query:
                        st.write(f"No matching terms found for '{search_query}'")
                    else:
                        st.write("No terms in this category")
    
    with tab2:
        st.header("Manage Terms")
        
        # Add category management section with a clear header
        with st.expander("Manage Categories", expanded=False):
            st.subheader("Add New Category")
            new_category = st.text_input(
                "Category name",
                placeholder="Enter category name (use lowercase and underscores)",
                help="Category names should be lowercase with underscores (e.g., 'trading_terms')"
            )
            
            if st.button("Add Category") and new_category:
                # Normalize category name
                normalized_category = new_category.lower().replace(' ', '_')
                if normalized_category not in st.session_state.glossary:
                    st.session_state.glossary[normalized_category] = []
                    save_glossary_to_file()
                    st.success(f"Added new category: {normalized_category}")
                else:
                    st.warning("Category already exists")
            
            st.divider()
            st.subheader("Delete Categories")
            # Delete category
            categories_to_delete = st.multiselect(
                "Select categories to delete",
                options=[cat for cat in st.session_state.glossary.keys() 
                        if cat not in ['product_names', 'technical_terms', 'awards_name', 'address', 'list_of_people', 'custom_terms']],
                help="Default categories cannot be deleted"
            )
            
            if st.button("Delete Selected Categories") and categories_to_delete:
                if st.checkbox("Confirm deletion? This cannot be undone."):
                    for cat in categories_to_delete:
                        del st.session_state.glossary[cat]
                    save_glossary_to_file()
                    st.success(f"Deleted {len(categories_to_delete)} categories")
        
        st.divider()
        
        # Add terms section with all elements in one line
        st.subheader("Add New Terms")
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            new_term = st.text_input("Term to add", label_visibility="collapsed", placeholder="Enter term to add")
        
        with col2:
            category = st.selectbox(
                "Select category",
                options=list(st.session_state.glossary.keys()),
                format_func=lambda x: x.replace('_', ' ').title(),
                label_visibility="collapsed"
            )
        
        with col3:
            if st.button("Add Term", use_container_width=True) and new_term:
                if new_term not in st.session_state.glossary[category]:
                    st.session_state.glossary[category].append(new_term)
                    save_glossary_to_file()
                    st.success(f"Added '{new_term}' to {category}")
                else:
                    st.warning(f"'{new_term}' already exists in {category}")
        
        # Remove terms section with similar layout to Add Terms
        st.divider()
        st.subheader("Remove Terms")
        
        col1, col2, col3 = st.columns([3, 3, 2])
        
        with col1:
            remove_category = st.selectbox(
                "Select category to remove terms from",
                options=list(st.session_state.glossary.keys()),
                format_func=lambda x: x.replace('_', ' ').title(),
                key="remove_category",
                label_visibility="collapsed",
                placeholder="Select category"
            )
        
        with col2:
            # Create numbered options for the multiselect
            numbered_terms = [
                f"{i+1}. {term}" 
                for i, term in enumerate(sorted(st.session_state.glossary[remove_category]))
            ]
            
            terms_to_remove = st.multiselect(
                "Select terms to remove",
                options=numbered_terms,
                label_visibility="collapsed",
                placeholder="Select terms to remove"
            )
        
        with col3:
            if st.button("Remove Selected Terms", use_container_width=True) and terms_to_remove:
                # Extract actual terms from numbered format
                actual_terms = [term.split('. ', 1)[1] for term in terms_to_remove]
                for term in actual_terms:
                    st.session_state.glossary[remove_category].remove(term)
                save_glossary_to_file()
                st.success(f"Removed {len(terms_to_remove)} term(s)")
    
    with tab3:
        st.header("Import/Export Glossary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Export")
            if st.button("Export to CSV"):
                csv_data = export_glossary_to_csv()
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name="translation_glossary.csv",
                    mime="text/csv"
                )
        
        with col2:
            st.subheader("Import")
            uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
            if uploaded_file is not None:
                if st.button("Import from CSV"):
                    if import_glossary_from_csv(uploaded_file):
                        st.success("Glossary imported successfully!")
    
    with tab4:
        st.header("Glossary Settings")
        
        # Add pagination settings
        st.subheader("Display Settings")
        new_page_size = st.number_input(
            "Terms per page", 
            min_value=5, 
            max_value=100, 
            value=st.session_state.page_size,
            step=5
        )
        
        if new_page_size != st.session_state.page_size:
            st.session_state.page_size = new_page_size
            # Reset current pages when changing page size
            st.session_state.current_page = {category: 0 for category in st.session_state.glossary.keys()}
            st.success(f"Page size updated to {new_page_size} terms")
        
        st.divider()
        
        if st.button("Reset to Default"):
            if st.checkbox("Are you sure? This will remove all custom terms."):
                # Reset to default glossary
                st.session_state.glossary = {
                    'product_names': [
                        'Deriv',
                        'Deriv App',
                        'Deriv Bot',
                        'Deriv GO',
                        'Deriv Life',
                        'Deriv Blog',
                        'Deriv X',
                        'Deriv cTrader',
                        'MT5',
                        'P2P',
                        'SmartTrader',
                        'Deriv Trader',
                        'Binary Bot',
                        'Forex',
                        'CFD',
                        'CFDs'                   
                    ],
                    'technical_terms': [
                        # Web Technologies
                        'API',
                        'URL',
                        'HTTP',
                        'HTTPS',
                        'SSL',
                        'TLS',
                        'JSON',
                        'XML',
                        'REST',
                        'RESTful',
                        'SOAP',
                        'WebSocket',
                        'WS',
                        'WSS',
                        'GET',
                        'POST',
                        'PUT',
                        'DELETE',
                        'OAuth',
                        'Passkey',
                        
                        # Web Browsers & Tools
                        'Google Chrome',
                        'Firefox',
                        'Safari',
                        'Edge',
                        'Chrome DevTools',
                        
                        # Cloud & Storage
                        'Google Drive',
                        'Dropbox',
                        'iCloud',
                        'AWS',
                        'Azure',
                        
                        # Development Frameworks & Libraries
                        'Flutter',
                        'React',
                        'Angular',
                        'Vue.js',
                        'Node.js',
                        'Express.js',
                        'Django',
                        'Flask',
                        
                        # Security
                        'CORS',
                        'XSS',
                        'CSRF',
                        'JWT',
                        'SSH',
                        'VPN',
                        
                        # Database
                        'SQL',
                        'NoSQL',
                        'MongoDB',
                        'PostgreSQL',
                        'MySQL',
                        'Redis',
                        
                        # Development Tools
                        'Git',
                        'GitHub',
                        'GitLab',
                        'VS Code',
                        'npm',
                        'yarn',
                        'webpack',
                        
                        # File Types
                        'CSV',
                        'PDF',
                        'ZIP',
                        'RAR',
                        'JPG',
                        'PNG',
                        'SVG',
                        
                        # Protocols
                        'FTP',
                        'SMTP',
                        'POP3',
                        'IMAP',
                        'TCP/IP',
                        'UDP',
                        
                        # Mobile Development
                        'iOS',
                        'Android',
                        'APK',
                        'IPA',
                        

                    ],
                    'awards_name': [
                        'Affiliate Program of the Year',
                        'Best Customer Service - Global',
                        'Best Latam Region Broker',
                        'Best Partner Programme',
                        'Best Trading Experience',
                        'Best Trading Experience (LATAM) 2024',
                        'Broker of the Year - Global',
                        'Finance Magnates 2024',
                        'Forex Expo Dubai 2024',
                        'FX&Trust Score Awards 2024',
                        'Global Forex Awards',
                        'Global Forex Awards 2024',
                        'Most Innovative Broker',
                        'Most Innovative Broker— MEA 2025',
                        'Most Trusted Broker',
                        'UF Awards 2024'
                    ],
                    'address': [
                        "17 Rue d'Antin, 75002 Paris",
                        "181, Leoforos Archiepiskopou Makariou III Avenue 15 Business Centre, 1st Floor, 3030, Limassol Cyprus",
                        "2nd Floor, Suite 2, Omar Hodge Building, 325 Waterfront Drive, Road Town, Tortola, VG 1110, British Virgin Islands",
                        "67-1 & 69-1, Jalan KLJ 6, Taman Kota Laksamana Jaya, Melaka 75200",
                        "72 Limassol Avenue, 12th floor, Asteroid Business Centre, 2014 Strovolos, Nicosia",
                        "80 Robinson Road, #11-03, Singapore 068898",
                        "AJIB Building, No 12A & 12B, 3rd Floor, Al Bonouk Street, Al Abdali Boulevard, Amman - Jordan.",
                        "Cayman Enterprise City, Strathvale House, 2nd Floor, 90N Church St, George Town, Cayman Islands",
                        "Deriv HQ, 3500, Jalan Teknokrat 3, 63000 Cyberjaya, Selangor",
                        "Deriv Technologies Limited, Apex Forbury Road, Reading RG1 1AX",
                        "E-5-6, Soho Ipoh 2, Jalan Sultan Idris Shah, Ipoh 30000, Perak",
                        "Edificio Atrium, Piso 2, Guido Spano Esq. Doctor Morra, Asunción 1849",
                        "F16, Level 1, Paragon Labuan, Jalan Tun Mustapha, Labuan 87000, Sabah",
                        "First Floor, 68 - 72 Leonard Street, London, EC2A 4QX",
                        "Kemperplatz 1 Mitte D, 10785 Berlin, Germany",
                        "Level 2 East Wing, Kigali Heights, KG7 Avenue, Kigali",
                        "Level 3, W Business Centre, Triq Dun Karm, Birkirkara, BKR 9033",
                        "Nicosia",
                        "No. 1-23A, First Floor, Paragon, Jalan Tun Mustapha, 87008, Federal Territory of Labuan, Malaysia.",
                        "Office 1902, Jumeirah Business Center 1, JLT Cluster G",
                        "Room 408A, Empire Centre, 68 Mody Road, Tsim Sha Tsui East, Kowloon, Hong Kong",
                        "Suite 5, One Cornet Street, St Peter Port, Guernsey GY1 1 BZ",
                        "World Trade Center Ciudad del Este",
                        "Yumiwork, Lolam building, Kumul Highway, Land # 11/OD22/021, Port Vila, Vanuatu"
                    ],
                    'list_of_people': [  # New category
                        'Derrick',
                        'Joanna Frendo',
                        'Seema Hallon',
                        'Louise Wolf',
                        'Jean-Yves Sireau',
                        'Rakshit Choudhary',
                        'Chris Horn',
                        'Derrick',
                        'Louise Wolf',
                        'Jennice Lourdsamy',
                        'Prakash Bhudia',          
                    ],
                    'custom_terms': []
                }
                save_glossary_to_file()
                st.success("Glossary reset to default")

if __name__ == "__main__":
    main() 