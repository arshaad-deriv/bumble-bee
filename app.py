import streamlit as st
import requests
import json
import openai
import time
import tempfile
import os
import zipfile
from utils import get_site_locales

# Hide the default menu
st.set_page_config(
    page_title="Where's Spidey?", 
    layout="wide"
)

def validate_api_token(api_key):
    """Validate API token by making a test request"""
    url = "https://api.webflow.com/v2/sites"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("Invalid API token. Please check your token and ensure it has the required permissions (pages:read)")
        elif e.response.status_code == 403:
            st.error("API token doesn't have the required permissions. Please ensure it has 'pages:read' scope")
        else:
            st.error(f"API Error: {str(e)}")
        return False
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return False

def get_pages(site_id, api_key):
    """Get list of pages with their IDs"""
    url = f"https://api.webflow.com/v2/sites/{site_id}/pages"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    print(f"\n[DEBUG] Fetching pages from URL: {url}")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        pages = response.json()["pages"]
        print(f"[DEBUG] Successfully fetched {len(pages)} pages")
        return pages
    except Exception as e:
        print(f"[DEBUG] Error fetching pages: {str(e)}")
        st.error(f"Error fetching pages: {str(e)}")
        return []

# Initialize session state
if 'site_id' not in st.session_state:
    st.session_state.site_id = ''
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'openai_key' not in st.session_state:
    st.session_state.openai_key = ''
if 'claude_api_key' not in st.session_state:
    st.session_state.claude_api_key = ''
if 'pages' not in st.session_state:
    st.session_state.pages = []
if 'locales' not in st.session_state:
    st.session_state.locales = []
if 'current_content' not in st.session_state:
    st.session_state.current_content = None
if 'parsed_nodes' not in st.session_state:
    st.session_state.parsed_nodes = None
# Add these new session state variables for password verification
if 'password_attempts' not in st.session_state:
    st.session_state.password_attempts = 0
if 'is_authenticated' not in st.session_state:
    st.session_state.is_authenticated = False
if 'show_password_dialog' not in st.session_state:
    st.session_state.show_password_dialog = False

# Add sidebar configuration
with st.sidebar:
    
    # Add the "Do We Know You?" button
    if not st.session_state.is_authenticated:
        if st.button("Do We Know You?"):
            st.session_state.show_password_dialog = True
            
        # Show password dialog if button was clicked
        if st.session_state.show_password_dialog:
            # Check if max attempts reached
            if st.session_state.password_attempts >= 3:
                st.error("Maximum password attempts reached. Please refresh the page to try again.")
            else:
                # Create password input
                password = st.text_input("Enter password:", type="password")
                
                if st.button("Submit"):
                    # Get correct password from secrets
                    correct_password = st.secrets["password"]["LET_ME_IN"]
                    
                    if password == correct_password:
                        st.session_state.is_authenticated = True
                        st.session_state.show_password_dialog = False
                        
                        # Set API keys directly from secrets
                        try:
                            # Set OpenAI API key
                            st.session_state.openai_key = st.secrets["api_keys"]["openai"]
                            
                            # Set Claude API key - this is the part that wasn't working
                            st.session_state.claude_api_key = st.secrets["api_keys"]["claude"]
                            
                            print(f"OpenAI API key loaded: {st.session_state.openai_key[:10]}...")
                            print(f"Claude API key loaded: {st.session_state.claude_api_key[:10]}...")
                            
                            success_message = "Authentication successful! OpenAI and Claude API keys configured."
                        except Exception as e:
                            print(f"Error loading API keys: {str(e)}")
                            success_message = "Authentication successful, but there was an issue loading API keys."
                        
                        st.success(success_message)
                        # Refresh the sidebar
                        st.rerun()
                    else:
                        st.session_state.password_attempts += 1
                        remaining_attempts = 3 - st.session_state.password_attempts
                        st.error(f"Incorrect password. {remaining_attempts} attempts remaining.")
    
    # Show preset options if authenticated
    if st.session_state.is_authenticated:
        st.success("Welcome back!")
        preset_option = st.selectbox(
            "Select preset:",
            options=["Deriv UAE", "Deriv main"],
            key="preset_selector"
        )
        
        # Set API key and site ID based on selection
        if preset_option == "Deriv UAE":
            # Load Dubai webflow credentials from secrets
            try:
                # Print debug information
                print("\nAttempting to load Webflow Dubai credentials...")
                print(f"Available sections in secrets: {list(st.secrets.keys())}")
                
                # Check if the section exists
                if "webflow_dubai" in st.secrets:
                    print(f"webflow_dubai section found with keys: {list(st.secrets.webflow_dubai.keys())}")
                
                    # Get the credentials
                    site_id = st.secrets.webflow_dubai.webflow_dubai_site_id
                    api_key = st.secrets.webflow_dubai.webflow_dubai_api
                    
                    print(f"Retrieved site_id: {site_id[:4]}...")
                    print(f"Retrieved api_key: {api_key[:4]}...")
                    
                    # Update session state
                    st.session_state.site_id = site_id
                    st.session_state.api_key = api_key
                    
                    # Reset cached data related to site changes
                    st.session_state.pages = []
                    st.session_state.locales = []
                    st.session_state.current_content = None
                    st.session_state.parsed_nodes = None
                    
                    st.info(f"Using Deriv UAE credentials - Site ID: {site_id[:4]}...")
                    
                    # Add a button to validate immediately
                    if st.button("Validate UAE Credentials"):
                        if validate_api_token(st.session_state.api_key):
                            st.success("Deriv UAE API credentials validated successfully!")
                            
                            # Fetch site data
                            with st.spinner("Fetching site data..."):
                                locales = get_site_locales(st.session_state.site_id, st.session_state.api_key)
                                if locales:
                                    st.session_state.locales = locales
                                
                                pages = get_pages(st.session_state.site_id, st.session_state.api_key)
                                if pages:
                                    st.session_state.pages = pages
                                    st.success(f"Successfully fetched {len(pages)} pages and {len(locales)} locales!")
                else:
                    st.error("webflow_dubai section not found in secrets.toml")
                    print("Available sections:", list(st.secrets.keys()))
                    
            except Exception as e:
                st.error(f"Error loading Deriv UAE credentials: {str(e)}")
                print(f"Exception details: {str(e)}")
                import traceback
                print(traceback.format_exc())
                
        elif preset_option == "Deriv main":
            # Load main webflow credentials from secrets
            try:
                # Print debug information
                print("\nAttempting to load Webflow Main credentials...")
                print(f"Available sections in secrets: {list(st.secrets.keys())}")
                
                # Check if the section exists - FIXED SECTION NAME HERE
                if "wf_main_deriv" in st.secrets:
                    print(f"wf_main_deriv section found with keys: {list(st.secrets.wf_main_deriv.keys())}")
                
                    # Get the credentials using the correct section name
                    site_id = st.secrets.wf_main_deriv.webflow_main_site_id
                    api_key = st.secrets.wf_main_deriv.webflow_main_api
                    
                    print(f"Retrieved site_id: {site_id[:4]}...")
                    print(f"Retrieved api_key: {api_key[:4]}...")
                    
                    # Update session state
                    st.session_state.site_id = site_id
                    st.session_state.api_key = api_key
                    
                    # Reset cached data related to site changes
                    st.session_state.pages = []
                    st.session_state.locales = []
                    st.session_state.current_content = None
                    st.session_state.parsed_nodes = None
                    
                    st.info(f"Using Deriv Main credentials - Site ID: {site_id[:4]}...")
                    
                    # Add a button to validate immediately
                    if st.button("Validate Deriv main Credentials"):
                        if validate_api_token(st.session_state.api_key):
                            st.success("Deriv main API credentials validated successfully!")
                            
                            # Fetch site data
                            with st.spinner("Fetching site data..."):
                                locales = get_site_locales(st.session_state.site_id, st.session_state.api_key)
                                if locales:
                                    st.session_state.locales = locales
                                
                                pages = get_pages(st.session_state.site_id, st.session_state.api_key)
                                if pages:
                                    st.session_state.pages = pages
                                    st.success(f"Successfully fetched {len(pages)} pages and {len(locales)} locales!")
                else:
                    st.error("wf_main_deriv section not found in secrets.toml")
                    print("Available sections:", list(st.secrets.keys()))
                    
            except Exception as e:
                st.error(f"Error loading Deriv main credentials: {str(e)}")
                print(f"Exception details: {str(e)}")
                import traceback
                print(traceback.format_exc())
    
    # OpenAI Configuration with header and expander
    st.subheader("OpenAI Configuration")
    with st.expander("Configure API Key", expanded=False):
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=st.session_state.openai_key,
            help="Your OpenAI API key for translations"
        )
        if openai_key:
            st.session_state.openai_key = openai_key
    
    # Claude Configuration with header and expander
    st.subheader("Claude Configuration")
    with st.expander("Configure API Key", expanded=False):
        claude_api_key = st.text_input(
            "Claude API Key",
            type="password",
            value=st.session_state.claude_api_key,
            help="Your Claude API key for Portuguese translations"
        )
        if claude_api_key:
            st.session_state.claude_api_key = claude_api_key
    
    # Add divider between configurations
    st.divider()
    
    # Webflow Configuration with header and expander
    st.subheader("Webflow Configuration")
    with st.expander("Configure API Settings", expanded=False):
        site_id = st.text_input(
            "Site ID", 
            value=st.session_state.site_id,
            help="The unique identifier for your Webflow site"
        )
        api_key = st.text_input(
            "API Key", 
            type="password", 
            value=st.session_state.api_key,
            help="Your Webflow API token"
        )
    
    # Update session state with new values
    if site_id:
        # Check if site ID has changed
        if st.session_state.site_id != site_id:
            # Reset cached data related to site
            st.session_state.pages = []
            st.session_state.locales = []
            st.session_state.current_content = None
            st.session_state.parsed_nodes = None
        st.session_state.site_id = site_id
        
    if api_key:
        # Check if API key has changed
        if st.session_state.api_key != api_key:
            # Reset cached data related to API
            st.session_state.pages = []
            st.session_state.locales = []
            st.session_state.current_content = None
            st.session_state.parsed_nodes = None
        st.session_state.api_key = api_key
    
    # Add validate button to sidebar
    if st.button("Validate & Fetch Site Data", key="sidebar_validate_button"):
        # First validate the API token
        if validate_api_token(st.session_state.api_key):
            st.success("API token validated successfully!")
            
            # Get Pages and Locales
            with st.spinner("Fetching site data..."):
                # Get and display locales for session state
                locales = get_site_locales(st.session_state.site_id, st.session_state.api_key)
                if locales:
                    st.session_state.locales = locales
                
                # Fetch pages for session state
                pages = get_pages(st.session_state.site_id, st.session_state.api_key)
                if pages:
                    st.session_state.pages = pages
                    st.success(f"Successfully fetched {len(pages)} pages and {len(locales)} locales!")

def get_page_content(page_id, api_key):
    """Get page content using DOM endpoint with pagination handling"""
    base_url = f"https://api.webflow.com/v2/pages/{page_id}/dom"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}",
        "accept-version": "1.0.0"
    }
    
    all_nodes = []
    offset = 0
    limit = 100  # Maximum allowed by API
    
    while True:
        # Construct URL with pagination parameters
        url = f"{base_url}?limit={limit}&offset={offset}"
        
        print(f"\nFetching nodes {offset} to {offset + limit}...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Add nodes from this batch to our collection
        current_nodes = data.get('nodes', [])
        all_nodes.extend(current_nodes)
        
        # Get pagination info
        pagination = data.get('pagination', {})
        total = pagination.get('total', 0)
        
        print(f"Retrieved {len(current_nodes)} nodes (Total: {len(all_nodes)}/{total})")
        
        # Check if we've got all nodes
        if len(all_nodes) >= total:
            break
            
        # Update offset for next batch
        offset += limit
    
    # Return complete data with all nodes
    return {
        "pageId": data.get("pageId"),
        "nodes": all_nodes,
        "lastUpdated": data.get("lastUpdated")
    }

def parse_page_content(content):
    """Parse page content and extract nodes with property overrides and text nodes"""
    parsed_nodes = []
    
    for node in content.get('nodes', []):
        node_data = {
            "nodeId": node['id'],
            "propertyOverrides": []
        }
        
        # Handle text type nodes
        if node.get('type') == 'text' and 'text' in node:
            node_data["text"] = node['text'].get('html', '')
            parsed_nodes.append(node_data)
            continue
        
        # Handle nodes with property overrides
        if node.get('propertyOverrides'):
            for override in node['propertyOverrides']:
                if 'propertyId' in override and 'text' in override:
                    # Get the property type
                    property_type = override.get('type', 'Plain Text')
                    
                    # Extract text based on property type
                    if property_type == 'Rich Text':
                        text_content = override['text'].get('html', '')
                    else:  # Plain Text or other types
                        text_content = override['text'].get('text', '')
                    
                    property_data = {
                        "propertyId": override['propertyId'],
                        "type": property_type,
                        "label": override.get('label', ''),
                        "text": text_content
                    }
                    node_data["propertyOverrides"].append(property_data)
            
            if node_data["propertyOverrides"]:
                parsed_nodes.append(node_data)
    
    return parsed_nodes

def display_curl_commands(page_id, locale_id, api_key, nodes):
    """Display curl commands for each node"""
    st.subheader("Generated CURL Commands")
    
    for node in nodes:
        for prop in node["propertyOverrides"]:
            curl_command = f"""curl -X POST "https://api.webflow.com/v2/pages/{page_id}/dom?localeId={locale_id}" \\
     -H "Authorization: Bearer {api_key}" \\
     -H "Content-Type: application/json" \\
     -d '{{
  "nodes": [
    {{
      "nodeId": "{node['nodeId']}",
      "propertyOverrides": [
        {{
          "propertyId": "{prop['propertyId']}",
          "text": "{prop['text']}"
        }}
      ]
    }}
  ]
}}'"""
            st.code(curl_command, language="bash")
            st.markdown("---")

def translate_content_with_openai(parsed_nodes, target_language, api_key):
    """Translate content using OpenAI while preserving JSON structure"""
    try:
        # First verify we have valid inputs
        if not parsed_nodes:
            return None, "No content to translate"
        if not target_language:
            return None, "No target language specified"
        if not api_key:
            return None, "OpenAI API key is missing"
            
        client = openai.OpenAI(api_key=api_key)
        
        # Print debug information
        print("\n" + "="*50)
        print("TRANSLATION REQUEST")
        print("="*50)
        print(f"Target Language: {target_language}")
        print("Content to translate:")
        print(json.dumps(parsed_nodes, indent=2))
        
        # Get all terms from the glossary that should not be translated
        do_not_translate_terms = []
        if 'glossary' in st.session_state:
            for category, terms in st.session_state.glossary.items():
                do_not_translate_terms.extend(terms)
        
        # Format the terms as a bulleted list for the prompt
        terms_list = "\n".join([f"- {term}" for term in do_not_translate_terms])
        
        # Prepare the system message explaining what we want
        system_message = f"""You are a professional translator with 20 years of experience.  
        Translate only the "text" values in the JSON to {target_language}.

        If the {target_language} is "sw", then in that case translate to Swahili.
                 
        DO NOT TRANSLATE the following terms - keep them exactly as they appear:
        {terms_list}
        
        Follow these additional rules when translating:
        - When encountering the word "Deriv" and any succeeding word, analyze the context and based on it, keep it in English. For example, "Deriv Blog," "Deriv Life," "Deriv Bot," and "Deriv App" should be kept in English.
        - Keep product names such as Forex, CFDs, P2P, MT5, Deriv X, Deriv cTrader, SmartTrader, Deriv Trader, Deriv GO, Deriv Bot, and Binary Bot in English.
        - Do not translate the following names of people explicitly mentioned in the JSON: Louise Wolf, Rakshit Choudhary,Chris Horn, Seema Hallon, Jean-Yves Sireau, and others. Keep them in English.
        - Do not translate "24/7". Keep the number in English.
        - When encountering the symbol "?", mirror it in the translated text when the target language is Arabic.
        
        Keep all other JSON structure and values exactly the same.
        Return only the JSON, no explanations."""
        
        # Prepare the JSON for translation
        user_message = f"Translate this JSON content. Original JSON:\n{json.dumps(parsed_nodes, indent=2)}"
        
        # Make the API call with new syntax
        try:
            response = client.chat.completions.create(
                model="o3-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ]
                # temperature=0.3
            )
            
            # Print the raw response for debugging
            print("\nOpenAI Response:")
            print(response)
            
            # Extract and validate the response content
            response_content = response.choices[0].message.content
            if not response_content:
                return None, "Empty response from OpenAI"
                
            # Try to parse the JSON response
            try:
                translated_json = json.loads(response_content)
                return translated_json, None
            except json.JSONDecodeError as e:
                print(f"JSON Parse Error: {str(e)}")
                print("Raw response content:")
                print(response_content)
                return None, f"Failed to parse OpenAI response as JSON: {str(e)}"
                
        except Exception as e:
            print(f"OpenAI API Error: {str(e)}")
            return None, f"OpenAI API Error: {str(e)}"
            
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return None, f"Translation error: {str(e)}"

def update_page_content(page_id, locale_id, api_key, translated_content):
    """Update page content with translated text"""
    url = f"https://api.webflow.com/v2/pages/{page_id}/dom?localeId={locale_id}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json"
    }
    
    # Restructure the translated content to match API requirements
    request_body = {
        "nodes": []
    }
    
    # Convert translated content into the correct format
    for node in translated_content:
        node_id = node.get('id') or node.get('nodeId')
        node_data = {
            "nodeId": node_id
        }
        
        # Check if this is a component instance (has propertyOverrides)
        if "propertyOverrides" in node and node["propertyOverrides"]:
            # Only add propertyOverrides if there are actual overrides
            node_data["propertyOverrides"] = [
                {
                    "propertyId": override["propertyId"],
                    "text": override["text"] if isinstance(override["text"], str) 
                           else (override["text"].get('text', '') if override["text"] is not None else '')
                }
                for override in node["propertyOverrides"]
            ]
        else:
            # For non-component instances, use text field directly
            node_data["text"] = node.get("text", "")
        
        request_body["nodes"].append(node_data)
    
    print("\n" + "="*50)
    print("UPDATE PAGE CONTENT REQUEST")
    print("="*50)
    print(f"URL: {url}")
    print("\nHeaders:")
    for key, value in headers.items():
        if key.lower() == 'authorization':
            print(f"{key}: Bearer ****{value[-4:]}")
        else:
            print(f"{key}: {value}")
    
    print("\nPayload:")
    print(json.dumps(request_body, indent=2))
    
    try:
        response = requests.post(url, headers=headers, json=request_body)
        
        print("\n" + "="*50)
        print("API RESPONSE")
        print("="*50)
        print(f"Status Code: {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
            
        # Check for specific node errors in the response
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("errors"):
                print("\nWarning: Some nodes had errors:")
                for error in response_data["errors"]:
                    print(f"Node {error['nodeId']}: {error['error']}")
        
        response.raise_for_status()
        return True, None
    except Exception as e:
        error_message = str(e)
        print(f"\nERROR: {error_message}")
        return False, error_message

def main():
    st.title("Webflow Page Content Manager")
    
    # Add the image at the top with centering and stretching
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.image("jameson.webp", caption="J. Jonah Jameson")
    
    # Print current session state
    print("\nCurrent Session State:")
    print(f"Has site_id: {bool(st.session_state.site_id)}")
    print(f"Has api_key: {bool(st.session_state.api_key)}")
    print(f"Number of pages: {len(st.session_state.pages)}")
    print(f"Number of locales: {len(st.session_state.locales)}")
    print(f"Has OpenAI key: {bool(st.session_state.openai_key)}")
    print(f"Has current content: {bool(st.session_state.current_content)}")
    
    # Check if credentials are set in session state
    if not st.session_state.api_key or not st.session_state.site_id:
        st.warning("Please enter your Webflow API Key and Site ID in the sidebar to continue.")
        st.stop()
        
    # Add page description instead of API token requirements
    st.header("JJJ - The webflow page translator ")
    st.markdown(
        "This tool helps you view, translate, and manage Webflow content across multiple languages. "
        "Select a page to view its content, then use OpenAI to translate it to any available locale."
    )
    
    # Display available locales and pages if they exist in session state
    if st.session_state.locales:
        st.subheader("Available Locales")
        locale_data = {
            "Type": [locale.get('type', 'Unknown') for locale in st.session_state.locales],
            "Display Name": [locale.get('displayName', 'Unnamed') for locale in st.session_state.locales],
            "Locale ID": [locale.get('id', 'No ID') for locale in st.session_state.locales],
            "Tag": [locale.get('tag', 'No tag') for locale in st.session_state.locales]
        }
        st.table(locale_data)
    
    if st.session_state.pages:
        st.subheader("Available Pages")
        page_data = {
            "Title": [page.get('title', 'Untitled') for page in st.session_state.pages],
            "Page ID": [page['id'] for page in st.session_state.pages],
            "Slug": [page.get('slug', 'No slug') for page in st.session_state.pages]
        }
        st.table(page_data)
    
    # Page selection and content viewing
    if st.session_state.pages:
        st.subheader("View Page Content")
        selected_page = st.selectbox(
            "Select a page",
            options=[f"{page.get('title', 'Untitled')} ({page['id']})" for page in st.session_state.pages],
            key="page_selector"
        )
        
        if selected_page:
            page_id = selected_page.split('(')[-1].strip(')')
            
            # View content button
            if st.button("View Content", key="view_content_button"):
                with st.spinner("Fetching page content..."):
                    content = get_page_content(page_id, st.session_state.api_key)
                    if content:
                        st.session_state.current_content = content
                        st.session_state.parsed_nodes = parse_page_content(content)
            
            # Display content if available
            if st.session_state.current_content:
                st.subheader("Page Content View")
                
                # Create two columns for side-by-side display
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Raw Page Content")
                    with st.expander("Show/Hide Raw Content", expanded=True):
                        st.json(st.session_state.current_content)
                
                with col2:
                    st.markdown("### Parsed Nodes with Property Overrides")
                    with st.expander("Show/Hide Parsed Nodes", expanded=True):
                        st.json(st.session_state.parsed_nodes)
                
                # Translation section
                if st.session_state.openai_key and st.session_state.locales:
                    st.subheader("Translate Content")
                    
                    # Add user role selection
                    user_role = st.radio(
                        "Select your role:",
                        ["Designer/Content Writer", "Proofreader"],
                        key="user_role"
                    )

                    # Create language selection with both tag and ID
                    locale_options = {
                        f"{locale.get('displayName', 'Unnamed')} ({locale.get('tag', 'No tag')})": {
                            'tag': locale.get('tag', 'unknown'),
                            'id': locale.get('id')
                        }
                        for locale in st.session_state.locales
                    }
                    
                    # Multi-select for languages
                    target_languages = st.multiselect(
                        "Select target languages",
                        options=list(locale_options.keys()),
                        key="translate_languages_select"
                    )
                    
                    if st.button("Translate to Selected Languages", key="translate_button"):
                        if not target_languages:
                            st.warning("Please select at least one language")
                            return
                            
                        print(f"\nTranslating to {len(target_languages)} languages")
                        
                        # Create a progress bar
                        progress_bar = st.progress(0)
                        translation_status = st.empty()
                        
                        # Process each language
                        for index, target_language in enumerate(target_languages):
                            translation_status.text(f"Processing {target_language} ({index + 1}/{len(target_languages)})")
                            print(f"\nProcessing language: {target_language}")
                            
                            with st.spinner(f"Translating to {target_language}..."):
                                # Use the language tag for translation
                                translated_content, error = translate_content_with_openai(
                                    st.session_state.parsed_nodes,
                                    locale_options[target_language]['tag'],
                                    st.session_state.openai_key
                                )
                                
                                if error:
                                    st.error(f"Error translating to {target_language}: {error}")
                                    continue
                                
                                # Get the locale ID for the API call
                                locale_id = locale_options[target_language]['id']
                                print(f"\nUsing locale ID: {locale_id}")
                                print(f"Language tag: {locale_options[target_language]['tag']}")
                                
                                # Create a minimal status indicator for this language
                                st.success(f"Translation completed for {target_language}")
                                
                                # Create an expander for the language details
                                with st.expander(f"Translation Details - {target_language}", expanded=False):
                                    st.subheader("Translated Content")
                                    st.json(translated_content)
                                
                                # Handle content update based on user role
                                if user_role == "Designer/Content Writer":
                                    # Update the page content immediately
                                    success, error = update_page_content(
                                        page_id=page_id,
                                        locale_id=locale_id,
                                        api_key=st.session_state.api_key,
                                        translated_content=translated_content
                                    )
                                    
                                    if success:
                                        st.success(f"Successfully updated content for {target_language}")
                                    else:
                                        st.error(f"Failed to update content for {target_language}: {error}")
                                elif user_role == "Proofreader":
                                    st.write("### Proofreader Review")
                                    st.info("Review and edit translations before publishing to Webflow.")
                                    
                                    # Create tabs for different views
                                    tab1, tab2 = st.tabs(["Side-by-Side View", "Full JSON View"])
                                    
                                    with tab1:
                                        # Track if any translations were modified
                                        modified_translations = False
                                        
                                        # Create a dictionary to store edited translations
                                        if 'edited_translations' not in st.session_state:
                                            st.session_state.edited_translations = {}
                                        
                                        # Initialize the edited translations for this language if not present
                                        lang_key = f"edited_{target_language}"
                                        if lang_key not in st.session_state.edited_translations:
                                            st.session_state.edited_translations[lang_key] = {}
                                        
                                        # Add a filter option
                                        filter_text = st.text_input("Filter translations", placeholder="Type to filter...", key=f"filter_{target_language}")
                                        
                                        # Count total translation items for progress tracking
                                        total_items = 0
                                        for node in translated_content:
                                            if "propertyOverrides" in node and node["propertyOverrides"]:
                                                total_items += len([o for o in node["propertyOverrides"] if 'text' in o])
                                            elif "text" in node:
                                                total_items += 1
                                        
                                        st.progress(0.0, text=f"0/{total_items} items reviewed")
                                        
                                        # Process each node for side-by-side display
                                        item_counter = 0
                                        reviewed_counter = 0
                                        
                                        for i, node in enumerate(translated_content):
                                            node_id = node.get('id') or node.get('nodeId')
                                            
                                            # Handle nodes with property overrides
                                            if "propertyOverrides" in node and node["propertyOverrides"]:
                                                for j, override in enumerate(node["propertyOverrides"]):
                                                    if 'text' in override:
                                                        item_counter += 1
                                                        
                                                        # Get the text content
                                                        text_content = override['text'] if isinstance(override['text'], str) else override['text'].get('text', '')
                                                        
                                                        # Skip if filtered and doesn't match
                                                        if filter_text and filter_text.lower() not in text_content.lower():
                                                            continue
                                                        
                                                        # Create a unique key for this text item
                                                        item_key = f"{node_id}_prop_{j}"
                                                        
                                                        # Find the original text if available
                                                        original_text = "Original text not available"
                                                        for orig_node in st.session_state.parsed_nodes:
                                                            if orig_node.get('nodeId') == node_id:
                                                                for orig_override in orig_node.get('propertyOverrides', []):
                                                                    if orig_override.get('propertyId') == override.get('propertyId'):
                                                                        original_text = orig_override.get('text', 'No text')
                                                                        break
                                                        
                                                        # Create an expander for each translation item
                                                        with st.expander(f"Item #{item_counter}: Property Override", expanded=False):
                                                            col1, col2 = st.columns(2)
                                                            
                                                            with col1:
                                                                st.caption("Original Text")
                                                                st.code(original_text, language=None)
                                                                st.caption(f"Node ID: {node_id[:8]}... | Property ID: {override.get('propertyId', 'N/A')[:8]}...")
                                                            
                                                            with col2:
                                                                st.caption(f"Translation ({target_language})")
                                                                # Use the stored edited value or the original translation
                                                                current_value = st.session_state.edited_translations[lang_key].get(item_key, text_content)
                                                                
                                                                # Create a text area for editing
                                                                edited_text = st.text_area(
                                                                    "Edit translation",
                                                                    value=current_value,
                                                                    height=max(100, min(300, 100 + 20 * text_content.count('\n'))),
                                                                    key=f"edit_{target_language}_{item_key}",
                                                                    label_visibility="collapsed"
                                                                )
                                                                
                                                                # Add a "Mark as reviewed" checkbox
                                                                reviewed = st.checkbox("Mark as reviewed", 
                                                                                      key=f"reviewed_{target_language}_{item_key}",
                                                                                      value=item_key in st.session_state.edited_translations.get(f"reviewed_{target_language}", set()))
                                                                
                                                                if reviewed:
                                                                    if f"reviewed_{target_language}" not in st.session_state.edited_translations:
                                                                        st.session_state.edited_translations[f"reviewed_{target_language}"] = set()
                                                                    st.session_state.edited_translations[f"reviewed_{target_language}"].add(item_key)
                                                                    reviewed_counter += 1
                                                                elif f"reviewed_{target_language}" in st.session_state.edited_translations and item_key in st.session_state.edited_translations[f"reviewed_{target_language}"]:
                                                                    st.session_state.edited_translations[f"reviewed_{target_language}"].remove(item_key)
                                                                
                                                                # Check if the text was modified
                                                                if edited_text != text_content:
                                                                    st.session_state.edited_translations[lang_key][item_key] = edited_text
                                                                    modified_translations = True
                                                                    
                                                                    # Update the translation in our content
                                                                    override['text'] = edited_text
                                            
                                            # Handle text nodes
                                            elif "text" in node:
                                                item_counter += 1
                                                
                                                # Get the text content
                                                text_content = node['text'] if isinstance(node['text'], str) else node['text'].get('html', '')
                                                
                                                # Skip if filtered and doesn't match
                                                if filter_text and filter_text.lower() not in text_content.lower():
                                                    continue
                                                
                                                # Create a unique key for this text item
                                                item_key = f"{node_id}_text"
                                                
                                                # Find the original text if available
                                                original_text = "Original text not available"
                                                for orig_node in st.session_state.parsed_nodes:
                                                    if orig_node.get('nodeId') == node_id and "text" in orig_node:
                                                        original_text = orig_node.get('text', 'No text')
                                                        break
                                                
                                                # Create an expander for each translation item
                                                with st.expander(f"Item #{item_counter}: Text Node", expanded=False):
                                                    col1, col2 = st.columns(2)
                                                    
                                                    with col1:
                                                        st.caption("Original Text")
                                                        st.code(original_text, language=None)
                                                        st.caption(f"Node ID: {node_id[:8]}...")
                                                    
                                                    with col2:
                                                        st.caption(f"Translation ({target_language})")
                                                        # Use the stored edited value or the original translation
                                                        current_value = st.session_state.edited_translations[lang_key].get(item_key, text_content)
                                                        
                                                        # Create a text area for editing
                                                        edited_text = st.text_area(
                                                            "Edit translation",
                                                            value=current_value,
                                                            height=max(100, min(300, 100 + 20 * text_content.count('\n'))),
                                                            key=f"edit_{target_language}_{item_key}",
                                                            label_visibility="collapsed"
                                                        )
                                                        
                                                        # Add a "Mark as reviewed" checkbox
                                                        reviewed = st.checkbox("Mark as reviewed", 
                                                                              key=f"reviewed_{target_language}_{item_key}",
                                                                              value=item_key in st.session_state.edited_translations.get(f"reviewed_{target_language}", set()))
                                                        
                                                        if reviewed:
                                                            if f"reviewed_{target_language}" not in st.session_state.edited_translations:
                                                                st.session_state.edited_translations[f"reviewed_{target_language}"] = set()
                                                            st.session_state.edited_translations[f"reviewed_{target_language}"].add(item_key)
                                                            reviewed_counter += 1
                                                        elif f"reviewed_{target_language}" in st.session_state.edited_translations and item_key in st.session_state.edited_translations[f"reviewed_{target_language}"]:
                                                            st.session_state.edited_translations[f"reviewed_{target_language}"].remove(item_key)
                                                        
                                                        # Check if the text was modified
                                                        if edited_text != text_content:
                                                            st.session_state.edited_translations[lang_key][item_key] = edited_text
                                                            modified_translations = True
                                                            
                                                            # Update the translation in our content
                                                            node['text'] = edited_text
                                        
                                        # Update progress bar
                                        if total_items > 0:
                                            progress_value = reviewed_counter / total_items
                                            st.progress(progress_value, text=f"{reviewed_counter}/{total_items} items reviewed")
                                        
                                        # Add approval button
                                        st.divider()
                                        col1, col2 = st.columns([3, 1])
                                        
                                        with col1:
                                            if modified_translations:
                                                st.success("You've made changes to the translations.")
                                            else:
                                                st.info("No changes made to translations.")
                                            
                                            # Show review progress
                                            if reviewed_counter == total_items:
                                                st.success("All items have been reviewed!")
                                            else:
                                                st.warning(f"{total_items - reviewed_counter} items still need review.")
                                        
                                        with col2:
                                            if st.button(f"Approve & Update Webflow", key=f"approve_{target_language}", use_container_width=True):
                                                success, error = update_page_content(
                                                    page_id=page_id,
                                                    locale_id=locale_id,
                                                    api_key=st.session_state.api_key,
                                                    translated_content=translated_content
                                                )
                                                
                                                if success:
                                                    st.success(f"Successfully updated content for {target_language}")
                                                    # Clear the edited translations for this language
                                                    st.session_state.edited_translations[lang_key] = {}
                                                    if f"reviewed_{target_language}" in st.session_state.edited_translations:
                                                        st.session_state.edited_translations[f"reviewed_{target_language}"] = set()
                                                else:
                                                    st.error(f"Failed to update content for {target_language}: {error}")
                                    
                                    with tab2:
                                        st.subheader("Full JSON View")
                                        st.json(translated_content)
                                        
                                        if st.button("Update Webflow from JSON", key=f"json_update_{target_language}"):
                                            success, error = update_page_content(
                                                page_id=page_id,
                                                locale_id=locale_id,
                                                api_key=st.session_state.api_key,
                                                translated_content=translated_content
                                            )
                                            
                                            if success:
                                                st.success(f"Successfully updated content for {target_language}")
                                            else:
                                                st.error(f"Failed to update content for {target_language}: {error}")
                                
                                # Update progress
                                progress = (index + 1) / len(target_languages)
                                progress_bar.progress(progress)
                                
                                # Create a summary of the translation
                                st.write(f"✅ {target_language}: Translation completed")
                                
                                # Add a small delay between requests to avoid rate limits
                                time.sleep(1)
                        
                        translation_status.text("All translations completed!")
                        
                        # Add an expander with all results
                        with st.expander("View all translation details", expanded=False):
                            for index, target_language in enumerate(target_languages):
                                st.subheader(f"Translation Details - {target_language}")
                                st.write(f"Status: Completed")
                                if user_role == "Proofreader":
                                    st.write("Review status available in the Side-by-Side View tab")
                                else:
                                    st.write("Content was updated directly to Webflow")
                        
                else:
                    if not st.session_state.openai_key:
                        st.warning("Please add your OpenAI API key in the sidebar to enable translations")
                    if not st.session_state.locales:
                        st.warning("No locales available for translation")

    # Add footer at the bottom of the app
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; padding: 10px;'>"
        "If you find this tool helpful, please buy me coffee and some shawarmas! ☕🌯"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
