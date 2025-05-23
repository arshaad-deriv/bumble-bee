import streamlit as st
import requests
import json
import openai
import time
import tempfile
import os
import zipfile
from streamlit_option_menu import option_menu
from utils import get_site_locales

# Hide the default menu
st.set_page_config(
    page_title="Webflow Content Manager", 
    layout="wide"
)

# Horizontal navigation menu
selected = option_menu(
    menu_title=None,
    options=["Component Content", "Component Properties"],
    icons=["file-text", "gear"],
    menu_icon="cast",
    default_index=1,  # Set to 1 to highlight the Properties tab
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#fafafa"},
        "icon": {"color": "#0083B8", "font-size": "16px"},
        "nav-link": {
            "font-size": "16px",
            "text-align": "center",
            "margin": "0px",
            "--hover-color": "#eee",
            "color": "#333333",  # Darker text color for better contrast
        },
        "nav-link-selected": {
            "background-color": "#0083B8", 
            "color": "white",  # Ensure selected text is white
            "font-weight": "bold"  # Make selected text bold for better visibility
        },
    }
)

# Redirect to the other page if Component Content is selected
if selected == "Component Content":
    st.switch_page("pages/1_Static_Components_Content.py")

# Initialize session state
if 'site_id' not in st.session_state:
    st.session_state.site_id = ''
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'openai_key' not in st.session_state:
    st.session_state.openai_key = ''
if 'components' not in st.session_state:
    st.session_state.components = []
if 'current_component_content' not in st.session_state:
    st.session_state.current_component_content = None
if 'parsed_nodes' not in st.session_state:
    st.session_state.parsed_nodes = None
if 'selected_component' not in st.session_state:
    st.session_state.selected_component = None
if 'translated_content' not in st.session_state:
    st.session_state.translated_content = None
if 'translation_requested' not in st.session_state:
    st.session_state.translation_requested = False
if 'target_language' not in st.session_state:
    st.session_state.target_language = None
if 'translation_started' not in st.session_state:
    st.session_state.translation_started = False
if 'selected_languages' not in st.session_state:
    st.session_state.selected_languages = []
if 'translation_progress' not in st.session_state:
    st.session_state.translation_progress = 0
if 'excluded_components' not in st.session_state:
    st.session_state.excluded_components = {}  # Will store {name: count}

# Ensure locales are fetched if credentials are set
if 'locales' not in st.session_state and st.session_state.site_id and st.session_state.api_key:
    with st.spinner("Fetching site locales..."):
        locales = get_site_locales(st.session_state.site_id, st.session_state.api_key)
        if locales:
            st.session_state.locales = locales
            st.success(f"Successfully fetched {len(locales)} locales!")
        else:
            st.warning("No locales found or error fetching locales.")

# Add sidebar configuration
with st.sidebar:

    
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
            st.session_state.components = []
            st.session_state.current_component_content = None
            st.session_state.parsed_nodes = None
        st.session_state.site_id = site_id
        
    if api_key:
        st.session_state.api_key = api_key

def get_site_components(site_id, api_key):
    """Get list of components from the site with pagination handling"""
    base_url = f"https://api.webflow.com/v2/sites/{site_id}/components"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    all_components = []
    offset = 0
    limit = 100  # Maximum allowed by API
    
    while True:
        url = f"{base_url}?limit={limit}&offset={offset}"
        print(f"\n[DEBUG] Fetching components from URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Add components from this batch
            current_components = data.get('components', [])
            all_components.extend(current_components)
            
            # Get pagination info
            pagination = data.get('pagination', {})
            total = pagination.get('total', 0)
            
            print(f"[DEBUG] Retrieved {len(current_components)} components (Total: {len(all_components)}/{total})")
            
            # Check if we've got all components
            if len(all_components) >= total:
                break
                
            # Update offset for next batch
            offset += limit
            
        except Exception as e:
            print(f"[DEBUG] Error fetching components: {str(e)}")
            st.error(f"Error fetching components: {str(e)}")
            return []
    
    print(f"[DEBUG] Successfully fetched all {len(all_components)} components")
    return all_components

def get_component_content(site_id, component_id, api_key):
    """Get component content using DOM endpoint with pagination handling"""
    base_url = f"https://api.webflow.com/v2/sites/{site_id}/components/{component_id}/dom"
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
        
        print("\n" + "="*50)
        print(f"API REQUEST - Get Component Content (Offset: {offset})")
        print("="*50)
        print(f"URL: {url}")
        print("\nHeaders:")
        for key, value in headers.items():
            if key.lower() == 'authorization':
                print(f"{key}: Bearer ****{value[-4:]}")
            else:
                print(f"{key}: {value}")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Add nodes from this batch to our collection
            current_nodes = data.get('nodes', [])
            all_nodes.extend(current_nodes)
            
            # Get pagination info
            pagination = data.get('pagination', {})
            total = pagination.get('total', 0)
            
            print(f"\nRetrieved {len(current_nodes)} nodes (Total: {len(all_nodes)}/{total})")
            
            # Print the complete API response for debugging
            print("\n" + "="*50)
            print("COMPLETE API RESPONSE")
            print("="*50)
            print(json.dumps(data, indent=2))
            
            # Check if we've got all nodes
            if len(all_nodes) >= total:
                break
                
            # Update offset for next batch
            offset += limit
            
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            st.error(f"Error fetching component content: {str(e)}")
            return None
    
    # Return complete data with all nodes
    return {
        "nodes": all_nodes,
        "lastUpdated": data.get("lastUpdated")
    }

def parse_component_content(content):
    """Parse component content to extract node IDs and HTML"""
    parsed_nodes = []
    
    for node in content.get('nodes', []):
        # Only include nodes that have non-empty html
        if node.get('text', {}).get('html'):
            node_data = {
                "nodeId": node['id'],
                "text": node['text']['html']  # Getting HTML instead of plain text
            }
            parsed_nodes.append(node_data)
    
    return {"nodes": parsed_nodes}

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
        
        DO NOT TRANSLATE the following terms - keep them exactly as they appear:
        {terms_list}
        
        Follow these additional rules when translating:
        - When encountering the word "Deriv" and any succeeding word, analyze the context and based on it, keep it in English. For example, "Deriv Blog," "Deriv Life," "Deriv Bot," and "Deriv App" should be kept in English.
        - Keep product names such as P2P, MT5, Deriv X, Deriv cTrader, SmartTrader, Deriv Trader, Deriv GO, Deriv Bot, and Binary Bot in English.
        
        Keep all other JSON structure and values exactly the same.
        Return only the JSON, no explanations."""
        
        # Prepare the JSON for translation
        user_message = f"Translate this JSON content. Original JSON:\n{json.dumps(parsed_nodes, indent=2)}"
        
        # Make the API call
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3
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

def update_component_content(site_id, component_id, locale_id, nodes, api_key):
    """Update component content with translated text"""
    # Updated URL structure to match the API specification
    url = f"https://api.webflow.com/v2/sites/{site_id}/components/{component_id}/dom?localeId={locale_id}"
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json"
    }
    
    payload = {
        "nodes": nodes
    }
    
    print("\n" + "="*50)
    print("UPDATE COMPONENT CONTENT REQUEST")
    print("="*50)
    print(f"URL: {url}")
    print(f"Locale ID: {locale_id}")
    print("\nHeaders:")
    for key, value in headers.items():
        if key.lower() == 'authorization':
            print(f"{key}: Bearer ****{value[-4:]}")
        else:
            print(f"{key}: {value}")
    print("\nPayload:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print("\nResponse Status:", response.status_code)
        print("Response Body:", response.text)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        error_msg = f"Error updating component content: {str(e)}"
        print(f"\nERROR: {error_msg}")
        return None, error_msg

def get_component_properties(site_id, component_id, api_key, locale_id=None):
    """Get component properties with pagination handling"""
    base_url = f"https://api.webflow.com/v2/sites/{site_id}/components/{component_id}/properties"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    # Add locale_id as a query parameter if provided
    params = {}
    if locale_id:
        params["localeId"] = locale_id
    
    all_properties = []
    offset = 0
    limit = 100  # Maximum allowed by API
    
    while True:
        # Add pagination parameters
        params["limit"] = limit
        params["offset"] = offset
        
        print("\n" + "="*50)
        print(f"API REQUEST - Get Component Properties (Offset: {offset})")
        print("="*50)
        print(f"URL: {base_url}")
        print(f"Params: {params}")
        print("\nHeaders:")
        for key, value in headers.items():
            if key.lower() == 'authorization':
                print(f"{key}: Bearer ****{value[-4:]}")
            else:
                print(f"{key}: {value}")
        
        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Add properties from this batch
            current_properties = data.get('properties', [])
            all_properties.extend(current_properties)
            
            # Get pagination info
            pagination = data.get('pagination', {})
            total = pagination.get('total', 0)
            
            print(f"\nRetrieved {len(current_properties)} properties (Total: {len(all_properties)}/{total})")
            
            # Print the complete API response for debugging
            print("\n" + "="*50)
            print("COMPLETE API RESPONSE")
            print("="*50)
            print(json.dumps(data, indent=2))
            
            # Check if we've got all properties
            if len(all_properties) >= total:
                break
                
            # Update offset for next batch
            offset += limit
            
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            st.error(f"Error fetching component properties: {str(e)}")
            return None
    
    # Return complete data with all properties
    return {
        "componentId": data.get("componentId"),
        "properties": all_properties
    }

def parse_component_properties(properties_data):
    """Parse component properties to extract property IDs and text content"""
    parsed_properties = []
    
    for prop in properties_data.get('properties', []):
        # Only include properties that have text content
        if prop.get('type') in ['Plain Text', 'Rich Text'] and prop.get('text'):
            property_data = {
                "propertyId": prop['propertyId'],
                "type": prop['type'],
                "label": prop.get('label', ''),
            }
            
            # Add the appropriate text field based on property type
            if prop['type'] == 'Plain Text' and 'text' in prop.get('text', {}):
                property_data["text"] = prop['text']['text']
            elif prop['type'] == 'Rich Text' and 'html' in prop.get('text', {}):
                property_data["text"] = prop['text']['html']
                
            parsed_properties.append(property_data)
    
    return {"properties": parsed_properties}

def translate_properties_with_openai(parsed_properties, target_language, api_key):
    """Translate properties using OpenAI while preserving structure"""
    try:
        # First verify we have valid inputs
        if not parsed_properties:
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
        print("Properties to translate:")
        print(json.dumps(parsed_properties, indent=2))
        
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

        If the {target_language} is "sw", then in that case translate to Swahili only.
        
        DO NOT TRANSLATE the following terms - keep them exactly as they appear:
        {terms_list}
        
        Follow these additional rules when translating:
        - When encountering the word "Deriv" and any succeeding word, analyze the context and based on it, keep it in English. For example, "Deriv Blog," "Deriv Life," "Deriv Bot," and "Deriv App" should be kept in English.
        - Keep product names such as P2P, MT5, Deriv X, Deriv cTrader, SmartTrader, Deriv Trader, Deriv GO, Deriv Bot, and Binary Bot in English.
        
        Keep all other JSON structure and values exactly the same.
        Return only the JSON, no explanations."""
        
        # Prepare the JSON for translation
        user_message = f"Translate this JSON content. Original JSON:\n{json.dumps(parsed_properties, indent=2)}"
        
        # Make the API call
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3
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
                
                # Format the translated properties for the update API
                formatted_properties = []
                for prop in translated_json.get('properties', []):
                    formatted_prop = {
                        "propertyId": prop['propertyId']
                    }
                    
                    # Add the appropriate field based on property type
                    if prop['type'] == 'Plain Text':
                        formatted_prop["text"] = prop['text']
                    elif prop['type'] == 'Rich Text':
                        formatted_prop["text"] = prop['text']
                        
                    formatted_properties.append(formatted_prop)
                
                return {"properties": formatted_properties}, None
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

def update_component_properties(site_id, component_id, locale_id, properties, api_key):
    """Update component properties with translated text"""
    url = f"https://api.webflow.com/v2/sites/{site_id}/components/{component_id}/properties"
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json"
    }
    
    # Add locale_id as a query parameter
    params = {"localeId": locale_id}
    
    print("\n" + "="*50)
    print("UPDATE COMPONENT PROPERTIES REQUEST")
    print("="*50)
    print(f"URL: {url}")
    print(f"Params: {params}")
    print("\nHeaders:")
    for key, value in headers.items():
        if key.lower() == 'authorization':
            print(f"{key}: Bearer ****{value[-4:]}")
        else:
            print(f"{key}: {value}")
    print("\nPayload:")
    print(json.dumps(properties, indent=2))
    
    try:
        response = requests.post(url, headers=headers, params=params, json=properties)
        print("\nResponse Status:", response.status_code)
        print("Response Body:", response.text)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        error_msg = f"Error updating component properties: {str(e)}"
        print(f"\nERROR: {error_msg}")
        return None, error_msg

def main():
    st.title("Static Components Properties Manager")
    
    # Check if credentials are set in session state
    if not st.session_state.api_key or not st.session_state.site_id:
        st.warning("Please enter your Webflow API Key and Site ID in the sidebar to continue.")
        st.stop()
    
    # Track API credential changes
    if 'previous_api_key' not in st.session_state:
        st.session_state.previous_api_key = st.session_state.api_key
    if 'previous_site_id' not in st.session_state:
        st.session_state.previous_site_id = st.session_state.site_id
    
    # Reset cached data if credentials have changed
    if (st.session_state.previous_api_key != st.session_state.api_key or 
        st.session_state.previous_site_id != st.session_state.site_id):
        # Reset all cached data
        st.session_state.components = []
        st.session_state.current_component_content = None
        st.session_state.parsed_nodes = None
        st.session_state.selected_component = None
        st.session_state.locales = None
        
        # Update the stored credentials
        st.session_state.previous_api_key = st.session_state.api_key
        st.session_state.previous_site_id = st.session_state.site_id
        
        # Inform the user
        st.success("API credentials updated. Data will be refreshed.")
    
    # 2. Fetch and Display Locales
    if st.session_state.get('locales'):
        st.subheader("Available Locales")
        locale_data = {
            "Name": [locale.get('displayName', 'Unnamed') for locale in st.session_state.locales],
            "Tag": [locale.get('tag', 'No tag') for locale in st.session_state.locales],
            "Type": [locale.get('type', 'Unknown') for locale in st.session_state.locales]
        }
        st.table(locale_data)
    
    # 3. Fetch Components
    if st.button("Fetch Site Components", key="fetch_components"):
        with st.spinner("Fetching components..."):
            components = get_site_components(st.session_state.site_id, st.session_state.api_key)
            if components:
                st.session_state.components = components
                st.success(f"Successfully fetched {len(components)} components!")
    
    # 4. Display Components and Handle Selection
    if st.session_state.components:
        st.subheader("Available Components")
        
        # Filter out "Break" components and count them
        filtered_components = []
        break_count = 0
        
        for comp in st.session_state.components:
            comp_name = comp.get('name', 'Unnamed')
            if comp_name == "Break":
                break_count += 1
            else:
                filtered_components.append(comp)
        
        # Show exclusion statistics
        if break_count > 0:
            st.info(f"Excluded {break_count} 'Break' component(s)")
            st.write("---")
        
        # Show filtered components count
        total_components = len(st.session_state.components)
        filtered_count = len(filtered_components)
        st.write(f"Showing {filtered_count} of {total_components} total components")
        
        # Create a table of filtered components
        component_data = {
            "Name": [comp.get('name', 'Unnamed') for comp in filtered_components],
            "Component ID": [comp['id'] for comp in filtered_components]
        }
        st.write("Showing components in table (limited to 100 rows):")
        st.table(component_data)
        
        # Update component selection to use filtered list
        selected_component = st.selectbox(
            f"Select a component (Total visible: {filtered_count})",
            options=[f"{comp.get('name', 'Unnamed')} ({comp['id']})" for comp in filtered_components],
            key="component_selector",
            index=0 if st.session_state.selected_component else 0
        )
        
        if selected_component:
            st.session_state.selected_component = selected_component
            component_id = selected_component.split('(')[-1].strip(')')
            
            # Initialize component content state if not present
            if 'current_component_content' not in st.session_state:
                st.session_state.current_component_content = None
            if 'parsed_nodes' not in st.session_state:
                st.session_state.parsed_nodes = None
            if 'translation_in_progress' not in st.session_state:
                st.session_state.translation_in_progress = False
            if 'current_translation_index' not in st.session_state:
                st.session_state.current_translation_index = 0
            if 'selected_languages' not in st.session_state:
                st.session_state.selected_languages = []
            
            # 6. View Content Button - Updated for properties
            if (st.button("View Component Properties", key="view_component_button") or 
                st.session_state.current_component_content is not None):
                
                # Only fetch properties if we don't have them or if we're viewing a new component
                if (st.session_state.current_component_content is None or 
                    'last_viewed_component_id' not in st.session_state or 
                    st.session_state.last_viewed_component_id != component_id):
                    
                    with st.spinner("Fetching component properties..."):
                        content = get_component_properties(
                            site_id=st.session_state.site_id,
                            component_id=component_id,
                            api_key=st.session_state.api_key
                        )
                        if content:
                            st.session_state.current_component_content = content
                            st.session_state.parsed_nodes = parse_component_properties(content)
                            st.session_state.last_viewed_component_id = component_id
                
                if st.session_state.parsed_nodes and st.session_state.parsed_nodes.get('properties'):
                    st.subheader("Parsed Properties")
                    st.json(st.session_state.parsed_nodes)
                    
                    # Translation section
                    if st.session_state.openai_key and st.session_state.locales:
                        st.subheader("Translate Properties")
                        
                        # Create language selection with both tag and ID
                        locale_options = {
                            f"{locale.get('displayName', 'Unnamed')} ({locale.get('tag', 'No tag')})": {
                                'tag': locale.get('tag', 'unknown'),
                                'id': locale.get('id')
                            }
                            for locale in st.session_state.locales
                        }
                        
                        # Multi-select for languages
                        if not st.session_state.translation_in_progress:
                            selected_languages = st.multiselect(
                                "Select target languages",
                                options=list(locale_options.keys()),
                                key="translate_languages_select",
                                default=st.session_state.selected_languages
                            )
                            
                            # Store selected languages in session state
                            if selected_languages != st.session_state.selected_languages:
                                st.session_state.selected_languages = selected_languages
                                
                            # Start translation button
                            if st.button("Start Translation", key="start_translation"):
                                if not st.session_state.selected_languages:
                                    st.warning("Please select at least one language")
                                else:
                                    st.session_state.translation_in_progress = True
                                    st.session_state.current_translation_index = 0
                                    st.rerun()
                        
                        # Handle ongoing translation - Updated for properties
                        if st.session_state.translation_in_progress:
                            progress_bar = st.progress(st.session_state.current_translation_index / len(st.session_state.selected_languages))
                            current_language = st.session_state.selected_languages[st.session_state.current_translation_index]
                            
                            st.write(f"Translating {current_language} ({st.session_state.current_translation_index + 1}/{len(st.session_state.selected_languages)})")
                            
                            # Perform translation for current language
                            translated_properties, error = translate_properties_with_openai(
                                st.session_state.parsed_nodes,
                                locale_options[current_language]['tag'],
                                st.session_state.openai_key
                            )
                            
                            if error:
                                st.error(f"Error translating to {current_language}: {error}")
                                st.session_state.translation_in_progress = False
                            else:
                                # Get the locale ID for the API call
                                locale_id = locale_options[current_language]['id']
                                
                                # Create an expander for translation details
                                with st.expander(f"Translation Details - {current_language}", expanded=True):
                                    st.subheader("Translated Properties")
                                    st.json(translated_properties)
                                    
                                    # Update the component properties
                                    result, error = update_component_properties(
                                        site_id=st.session_state.site_id,
                                        component_id=component_id,
                                        locale_id=locale_id,
                                        properties=translated_properties,
                                        api_key=st.session_state.api_key
                                    )
                                    
                                    if error:
                                        st.error(f"Failed to update properties for {current_language}: {error}")
                                        st.session_state.translation_in_progress = False
                                    else:
                                        st.success(f"Successfully updated properties for {current_language}")
                                        
                                        # Move to next language or finish
                                        st.session_state.current_translation_index += 1
                                        if st.session_state.current_translation_index >= len(st.session_state.selected_languages):
                                            st.session_state.translation_in_progress = False
                                            st.success("All translations completed!")
                                            if st.button("Start New Translation"):
                                                st.session_state.translation_in_progress = False
                                                st.session_state.current_translation_index = 0
                                                st.session_state.selected_languages = []
                                                st.rerun()
                                        else:
                                            time.sleep(1)  # Small delay between translations
                                            st.rerun()
                    else:
                        if not st.session_state.openai_key:
                            st.warning("Please add your OpenAI API key in the sidebar to enable translations")
                        if not st.session_state.locales:
                            st.warning("No locales available for translation")
                else:
                    st.info("No text properties found in this component")

if __name__ == "__main__":
    main()