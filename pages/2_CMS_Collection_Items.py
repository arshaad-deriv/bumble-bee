import streamlit as st
import requests
import json
import openai
import logging
import time

# Set up logging configuration at the top of the file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Hide the default menu
st.set_page_config(
    page_title="J.Jonah Jameson - Get it to the front page",
    layout="wide"
)

# Add at the top of the file with other imports
COLLECTION_CONFIGS = {
    "Blog": {
        "fields_to_translate": [
            'disclaimer-2',
            'post',
            'summary',
            'name',
            'meta-description-2',
            'page-title'
        ],
        "fields_to_preserve": ['slug', 'accumulators-option'],
        "display_name": "Blog Post",
        "item_identifier": "name"
    },
    "Support Questions": {
        "fields_to_translate": [
            'answer',
            'name'
        ],
        "fields_to_preserve": ['slug', 'category-3', 'order-number'],
        "display_name": "Help Center Question",
        "item_identifier": "question"
    },
    "Tncs": {
        "fields_to_translate": [
            'name',
            'content',
            'meta-description',
            'page-title'
        ],
        "fields_to_preserve": ['slug', 'order', 'category'],
        "display_name": "Tncs",
        "item_identifier": "name"
    },
    "Terms and Conditions": {
        "fields_to_translate": [
            'name',
            'content',
            'pdf-name-1',
            'description',
            'page-title'
        ],
        "fields_to_preserve": ['slug', 'order', 'category', 'pdf-link-1', 'link-1'],
        "display_name": "Terms and Conditions",
        "item_identifier": "name"
    },
    "Trading Specifications": {
        "fields_to_translate": [            
        ],
        "fields_to_preserve": [
            'type'
        ],
        "display_name": "Trading Specifications",
        "item_identifier": "name"
    },
    "Help Center Categories": {
        "fields_to_translate": [
            'name',
            'page-title',
            'meta-description'
        ],
        "fields_to_preserve": [
            'slug',
            'type',
            'order-number',
            'main-questions',
        ],
        "display_name": "Help Center Category",
        "item_identifier": "name"
    },
    "Help Center Questions": {
        "fields_to_translate": [
            'name',                    # Question title
            'answer',                 # Answer content
        ],
        "fields_to_preserve": [
            'slug',                   # URL slug
            'category',            # Category identifier
            'order-number'
        ],
        "display_name": "Help Center Question",
        "item_identifier": "question"  # Use question field as identifier
    }
}

def get_collection_config(collection_name):
    """Get collection configuration based on collection name"""
    for collection_type, config in COLLECTION_CONFIGS.items():
        if collection_type.lower() in collection_name.lower():
            return collection_type, config
    return None, None

def parse_collection_items(items, collection_type, config):
    """Parse collection items based on collection type"""
    parsed_items = []
    
    for item in items:
        field_data = item.get('fieldData', {})
        
        # Get identifier for display
        identifier = field_data.get(config['item_identifier'], 'Unnamed')
        
        # Create filtered data dictionary
        filtered_data = {
            key: field_data.get(key, '')
            for key in config['fields_to_translate'] + config['fields_to_preserve']
            if key in field_data
        }
        
        parsed_items.append({
            'id': item.get('id'),
            'identifier': identifier,
            'slug': field_data.get('slug', 'no-slug'),
            'data': filtered_data
        })
    
    return parsed_items

def get_cms_locales(site_id, api_key):
    """Get list of CMS locales from site data"""
    url = f"https://api.webflow.com/v2/sites/{site_id}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        cms_locales = []
        
        # Add primary locale
        primary = data.get('locales', {}).get('primary', {})
        if primary:
            cms_locales.append({
                'name': primary.get('displayName', 'Unnamed'),
                'id': primary.get('cmsLocaleId'),
                'code': primary.get('tag'),
                'default': True
            })
        
        # Add secondary locales
        secondary = data.get('locales', {}).get('secondary', [])
        for locale in secondary:
            if locale.get('enabled', False):  # Only include enabled locales
                cms_locales.append({
                    'name': locale.get('displayName', 'Unnamed'),
                    'id': locale.get('cmsLocaleId'),
                    'code': locale.get('tag'),
                    'default': False
                })
        
        return cms_locales
    except Exception as e:
        st.error(f"Error fetching CMS locales: {str(e)}")
        return []

def get_collection_items(site_id, collection_id, api_key, offset=0, limit=100):
    """Get collection items with optional filtering"""
    url = f"https://api.webflow.com/v2/collections/{collection_id}/items"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    params = {
        "offset": offset,
        "limit": limit
    }
    
    logger.info(f"Fetching collection items: URL={url}, offset={offset}, limit={limit}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Log pagination info for debugging
        pagination = data.get('pagination', {})
        logger.info(f"Pagination info: total={pagination.get('total', 'N/A')}, offset={pagination.get('offset', 'N/A')}, limit={pagination.get('limit', 'N/A')}")
        
        return data
    except Exception as e:
        error_msg = f"Error fetching collection items: {str(e)}"
        logger.error(error_msg)
        st.error(error_msg)
        return None

def translate_collection_item(collection_id, item_id, api_key, cms_locale_id):
    """Get translated version of a collection item"""
    url = f"https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    # Add the CMS Locale ID as a query parameter
    params = {
        "cmsLocaleId": cms_locale_id
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, f"Error fetching translation: {str(e)}"

def update_collection_item(collection_id, item_id, api_key, cms_locale_id, field_data):
    """Update a collection item with translated content"""
    url = f"https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json"
    }
    
    # Prepare the payload
    payload = {
        "isArchived": False,
        "isDraft": False,
        "fieldData": field_data,
        "cmsLocaleId": cms_locale_id
    }
    
    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, f"Error updating translation: {str(e)}"

def generate_curl_command(collection_id, item_id, api_key, cms_locale_id, field_data):
    """Generate curl command for updating translation"""
    # Prepare the payload with proper escaping for curl
    payload = {
        "isArchived": False,
        "isDraft": False,
        "fieldData": field_data,
        "cmsLocaleId": cms_locale_id
    }
    
    # Create the curl command
    curl_command = f"""curl -X PATCH "https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}" \\
     -H "Authorization: Bearer {api_key}" \\
     -H "Content-Type: application/json" \\
     -d '{json.dumps(payload, ensure_ascii=False)}'"""
    
    return curl_command

def translate_with_openai(text, target_language, api_key):
    """Translate text using OpenAI"""
    try:
        # Log translation request details
        logger.info(f"\n{'='*50}")
        logger.info("TRANSLATION REQUEST DETAILS")
        logger.info(f"{'='*50}")
        logger.info(f"Target Language: {target_language}")
        logger.info(f"Input Text Length: {len(text)} characters")
        logger.info(f"Input Text Preview: {text[:200]}..." if len(text) > 200 else text)
        
        # Log glossary terms being used
        do_not_translate_terms = []
        if 'glossary' in st.session_state:
            for category, terms in st.session_state.glossary.items():
                do_not_translate_terms.extend(terms)
            logger.info(f"\nGlossary Terms Applied:")
            logger.info(f"Total Terms: {len(do_not_translate_terms)}")
            logger.info("Terms List:")
            for term in do_not_translate_terms:
                logger.info(f"- {term}")
        
        client = openai.OpenAI(api_key=api_key)
        
        # Format terms for prompt
        terms_list = "\n".join([f"- {term}" for term in do_not_translate_terms])
        
        system_message = f"""You are a professional translator with 20 years of experience.
        Translate the text to {target_language}.
        
        DO NOT TRANSLATE the following terms - keep them exactly as they appear:
        {terms_list}
        
        Follow these additional rules when translating:
        - When encountering the word "Deriv" and any succeeding word, keep it in English. For example, "Deriv Blog," "Deriv Life," "Deriv Bot," and "Deriv App" should be kept in English.
        - Keep product names such as P2P, MT5, Deriv X, Deriv cTrader, SmartTrader, Deriv Trader, Deriv GO, Deriv Bot, and Binary Bot in English.
        
        Return only the translation, no explanations."""
        
        # Log OpenAI request
        logger.info(f"\n{'='*50}")
        logger.info("OPENAI API REQUEST")
        logger.info(f"{'='*50}")
        logger.info(f"Model: gpt-4o-mini")
        logger.info("System Message:")
        logger.info(system_message)
        logger.info("\nUser Message:")
        logger.info(text)
        
        # Make API call with timing
        start_time = time.time()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )
        end_time = time.time()
        
        # Log OpenAI response
        logger.info(f"\n{'='*50}")
        logger.info("OPENAI API RESPONSE")
        logger.info(f"{'='*50}")
        logger.info(f"Response Time: {end_time - start_time:.2f} seconds")
        
        translated_text = response.choices[0].message.content.strip()
        
        # Log translation result
        logger.info(f"\nTranslated Text Preview: {translated_text[:200]}..." if len(translated_text) > 200 else translated_text)
        
        # Log term preservation check
        logger.info(f"\n{'='*50}")
        logger.info("TERM PRESERVATION CHECK")
        logger.info(f"{'='*50}")
        for term in do_not_translate_terms:
            if term in text and term in translated_text:
                logger.info(f"✅ Term preserved: {term}")
            elif term in text and term not in translated_text:
                logger.warning(f"⚠️ Term not preserved: {term}")
        
        logger.info(f"\n{'='*50}\n")
        
        return translated_text, None
    except Exception as e:
        error_msg = f"Translation error: {str(e)}"
        logger.error(error_msg)
        logger.error(f"{'='*50}\n")
        return None, error_msg

def execute_curl_command(collection_id, item_id, api_key, cms_locale_id, field_data):
    """Execute the PATCH request and return response"""
    url = f"https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json"
    }
    
    payload = {
        "isArchived": False,
        "isDraft": False,
        "fieldData": field_data,
        "cmsLocaleId": cms_locale_id
    }
    
    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        return {
            'status_code': response.status_code,
            'response': response.json(),
            'error': None
        }
    except Exception as e:
        return {
            'status_code': None,
            'response': None,
            'error': str(e)
        }

def get_collections(site_id, api_key):
    """Get list of collections from the site"""
    url = f"https://api.webflow.com/v2/sites/{site_id}/collections"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get('collections', [])
    except Exception as e:
        st.error(f"Error fetching collections: {str(e)}")
        return []

def get_all_collection_items(site_id, collection_id, api_key):
    """Get all collection items with pagination handling"""
    all_items = []
    offset = 0
    limit = 100  # Maximum allowed by API
    
    # Create a progress placeholder
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    # First request to get total count
    status_placeholder.info(f"Fetching initial batch of items...")
    response = get_collection_items(site_id, collection_id, api_key, offset, limit)
    
    if not response or 'items' not in response:
        status_placeholder.error("Failed to fetch collection items")
        return []
    
    # Get total from first response - properly access the pagination object
    total = response.get('pagination', {}).get('total', 0)
    items = response.get('items', [])
    all_items.extend(items)
    
    # Update progress
    progress = min(len(all_items) / max(total, 1), 1.0)
    progress_placeholder.progress(progress)
    status_placeholder.info(f"Loaded {len(all_items)} of {total} items...")
    
    # Continue fetching if there are more items
    while len(all_items) < total:
        offset += limit
        status_placeholder.info(f"Fetching items {offset} to {min(offset + limit, total)}...")
        response = get_collection_items(site_id, collection_id, api_key, offset, limit)
        
        if not response or 'items' not in response:
            status_placeholder.warning(f"Error fetching batch at offset {offset}")
            break
        
        items = response.get('items', [])
        if not items:
            break
            
        all_items.extend(items)
        
        # Update progress
        progress = min(len(all_items) / max(total, 1), 1.0)
        progress_placeholder.progress(progress)
        status_placeholder.info(f"Loaded {len(all_items)} of {total} items...")
        
        # Optional: Add a small delay to avoid rate limiting
        time.sleep(0.2)
    
    # Clear the progress indicators when done
    if len(all_items) >= total:
        status_placeholder.success(f"Successfully loaded all {total} items!")
    else:
        status_placeholder.warning(f"Loaded {len(all_items)} of {total} items. Some items may be missing.")
    
    return all_items

def main():
    st.title("J.Jonah Jameson - Get it to the front page")
    
    # Check if we have the required credentials
    if not st.session_state.get('site_id') or not st.session_state.get('api_key'):
        st.error("Please enter your Site ID and API Key in the main page first")
        return
    
    if not st.session_state.get('openai_key'):
        st.warning("Please add your OpenAI API key in the sidebar to enable translations")
        return
    
    # Display CMS locales table
    st.subheader("CMS Locales")
    with st.spinner("Fetching CMS locales..."):
        cms_locales = get_cms_locales(st.session_state.site_id, st.session_state.api_key)
        if cms_locales:
            locale_data = {
                "Language": [locale.get('name', 'Unnamed') for locale in cms_locales],
                "CMS Locale ID": [locale.get('id', 'No ID') for locale in cms_locales],
                "Language Code": [locale.get('code', 'No code') for locale in cms_locales],
                "Default": [str(locale.get('default', False)) for locale in cms_locales]
            }
            st.table(locale_data)
    
    # Replace Collection ID input with dropdown
    st.subheader("Collection Details")
    with st.spinner("Fetching collections..."):
        collections = get_collections(st.session_state.site_id, st.session_state.api_key)
        if collections:
            collection_options = [f"{col['displayName']} ({col['id']})" for col in collections]
            selected_collection = st.selectbox(
                "Select Collection",
                options=collection_options,
                help="Choose the collection you want to manage"
            )
            
            if selected_collection:
                # Get collection type and config
                collection_name = selected_collection.split('(')[0].strip()
                collection_type, config = get_collection_config(collection_name)
                
                if not config:
                    st.warning(f"Collection type '{collection_name}' is not configured for translation. Available types: {', '.join(COLLECTION_CONFIGS.keys())}")
                    return
                
                st.write(f"Processing {config['display_name']} collection")
                
                # Extract collection ID and fetch items
                collection_id = selected_collection.split('(')[-1].strip(')')
                
                # Add a loading message
                with st.status("Loading collection items...", expanded=True) as status:
                    status.update(label="Fetching collection items... This may take a while for large collections.")
                    
                    # Use the improved pagination function
                    items = get_all_collection_items(
                        st.session_state.site_id,
                        collection_id,
                        st.session_state.api_key
                    )
                    
                    if items:
                        # Parse items based on collection type
                        parsed_items = parse_collection_items(items, collection_type, config)
                        status.update(label=f"Loaded {len(parsed_items)} items", state="complete")
                        
                        # Display pagination info
                        st.info(f"Successfully loaded {len(parsed_items)} items from the collection.")
                        
                        # Add a search filter for large collections
                        search_term = st.text_input("Filter items by name:", placeholder="Type to filter...")
                        
                        # Filter items based on search term
                        filtered_items = parsed_items
                        if search_term:
                            filtered_items = [item for item in parsed_items 
                                             if search_term.lower() in item['identifier'].lower() or 
                                                search_term.lower() in item['slug'].lower()]
                            st.write(f"Found {len(filtered_items)} items matching '{search_term}'")
                        
                        # Create a selectbox with filtered items
                        item_options = ['All'] + [f"{item['identifier']} ({item['slug']})" for item in filtered_items]
                        selected_item = st.selectbox(
                            f"Select {config['display_name']} (Total: {len(filtered_items)} of {len(parsed_items)})",
                            options=item_options
                        )
                        
                        if selected_item != 'All':
                            selected_slug = selected_item.split('(')[-1].strip(')')
                            selected_data = next(
                                (item for item in filtered_items if item['slug'] == selected_slug),
                                None
                            )
                            
                            if selected_data:
                                st.subheader("Original Content")
                                st.json(selected_data['data'])
                                
                                # Translation section
                                st.subheader("Translation Management")
                                
                                # Add translation mode selection
                                translation_mode = st.radio(
                                    "Translation Mode",
                                    ["Single Language", "All Languages"],
                                    help="Choose to translate to one language or all available languages"
                                )
                                
                                if translation_mode == "Single Language":
                                    # Single language translation logic
                                    target_language = st.selectbox(
                                        "Select target language",
                                        options=[f"{locale['name']} ({locale['code']}) - {locale['id']}" 
                                                for locale in cms_locales]
                                    )
                                    
                                    if target_language:
                                        # Extract CMS Locale ID and language code
                                        cms_locale_id = target_language.split(' - ')[-1]
                                        language_code = target_language.split('(')[1].split(')')[0]
                                        
                                        # Display form with translations
                                        with st.form("translation_form"):
                                            edited_fields = {}
                                            
                                            for key, value in selected_data['data'].items():
                                                if key in config['fields_to_preserve']:
                                                    edited_fields[key] = value
                                                    continue
                                                
                                                if isinstance(value, str):
                                                    if len(value) > 200:
                                                        edited_fields[key] = st.text_area(
                                                            key,
                                                            value=value,
                                                            height=300
                                                        )
                                                    else:
                                                        edited_fields[key] = st.text_input(
                                                            key,
                                                            value=value
                                                        )
                                            
                                            col1, col2 = st.columns(2)
                                            with col1:
                                                translate_button = st.form_submit_button("Translate")
                                            with col2:
                                                update_button = st.form_submit_button("Update Content")
                                            
                                            if translate_button:
                                                with st.spinner("Translating content..."):
                                                    for key, value in selected_data['data'].items():
                                                        if isinstance(value, str) and key not in config['fields_to_preserve']:
                                                            translated_text, error = translate_with_openai(
                                                                value,
                                                                language_code,
                                                                st.session_state.openai_key
                                                            )
                                                            if error:
                                                                st.error(f"Error translating {key}: {error}")
                                                            else:
                                                                edited_fields[key] = translated_text
                                            
                                            if update_button:
                                                with st.spinner("Updating content..."):
                                                    result = execute_curl_command(
                                                        collection_id=collection_id,
                                                        item_id=selected_data['id'],
                                                        api_key=st.session_state.api_key,
                                                        cms_locale_id=cms_locale_id,
                                                        field_data=edited_fields
                                                    )
                                                    
                                                    if result['error']:
                                                        st.error(f"Error updating content: {result['error']}")
                                                    else:
                                                        st.success("✅ Content updated successfully!")
                                
                                else:  # All Languages mode
                                    if st.button("Translate and Update All Languages"):
                                        # Create a progress container
                                        progress_container = st.empty()
                                        status_container = st.empty()
                                        results_container = st.container()
                                        
                                        # Initialize translation results
                                        translation_results = []
                                        
                                        # Get non-default languages
                                        languages_to_translate = [l for l in cms_locales if not l.get('default', False)]
                                        total_languages = len(languages_to_translate)
                                        
                                        for idx, locale in enumerate(languages_to_translate):
                                            # Update progress (ensure it's between 0 and 1)
                                            progress = min(idx / total_languages, 1.0)
                                            progress_container.progress(progress)
                                            
                                            # Update status message
                                            status_container.info(f"Translating to {locale['name']} ({locale['code']})...")
                                            
                                            # Store translations for this language
                                            current_translations = {}
                                            
                                            # Translate each field
                                            for key, value in selected_data['data'].items():
                                                if isinstance(value, str) and key not in config['fields_to_preserve']:
                                                    translated_text, error = translate_with_openai(
                                                        value,
                                                        locale['code'],
                                                        st.session_state.openai_key
                                                    )
                                                    if error:
                                                        translation_results.append({
                                                            'language': locale['name'],
                                                            'status': 'error',
                                                            'message': f"Error translating {key}: {error}"
                                                        })
                                                        translated_text = value
                                                    current_translations[key] = translated_text
                                                else:
                                                    current_translations[key] = value
                                            
                                            # Execute update for this language
                                            result = execute_curl_command(
                                                collection_id=collection_id,
                                                item_id=selected_data['id'],
                                                api_key=st.session_state.api_key,
                                                cms_locale_id=locale['id'],
                                                field_data=current_translations
                                            )
                                            
                                            # Store result
                                            translation_results.append({
                                                'language': locale['name'],
                                                'status': 'success' if not result['error'] else 'error',
                                                'message': result['error'] if result['error'] else 'Translation completed successfully'
                                            })
                                            
                                            # Update results in real-time
                                            with results_container:
                                                st.write("Translation Results:")
                                                for result in translation_results:
                                                    if result['status'] == 'success':
                                                        st.success(f"✅ {result['language']}: {result['message']}")
                                                    else:
                                                        st.error(f"❌ {result['language']}: {result['message']}")
                                        
                                        # Clear progress and status when complete
                                        progress_container.empty()
                                        status_container.success("All translations completed!")

if __name__ == "__main__":
    main() 