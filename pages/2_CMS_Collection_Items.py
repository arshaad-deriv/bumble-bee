import streamlit as st
import requests
import json
import openai
import logging
import time
import datetime
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import anthropic  # Add this new import for Claude API

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
        "display_name": "Help Centre Category",
        "item_identifier": "name"
    },
    "Help Centre Categories": {
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
        "display_name": "Help Centre Category",
        "item_identifier": "name"
    },
    "Help Centre Questions": {
        "fields_to_translate": [
            'name',                    # Question title
            'answer',                 # Answer content
        ],
        "fields_to_preserve": [
            'slug',                   # URL slug
            'category',            # Category identifier
            'order-number'
        ],
        "display_name": "Help Centre Question",
        "item_identifier": "name"  # Use question field as identifier
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
        "item_identifier": "name"  # Use question field as identifier
    },
    "EU Blogs": {
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
    
    "EU Newsroom": {
        "fields_to_translate": [
            'post',
            'image-alt-text',
            'summary',
            'name',
            'meta-description-2',
            'page-title'
        ],
        "fields_to_preserve": ['slug'],
        "display_name": "EU Newsroom",
        "item_identifier": "name"
    },

        "Newsroom": {
        "fields_to_translate": [
            'post',
            'image-alt-text',
            'summary',
            'name',
            'meta-description-2',
            'page-title'
        ],
        "fields_to_preserve": ['slug'],
        "display_name": "Newsroom",
        "item_identifier": "name"
    },

    "Tactical Indices": {
        "fields_to_translate": [
            'disclaimer-2',
            'text'
            ],
        "fields_to_preserve": ['slug'],
        "display_name": "Tactical Indices",
        "item_identifier": "name"
    },
    
    "ROW Trading pages FAQ's": {
        "fields_to_translate": [
            'answer',
            'name'
            ],
        "fields_to_preserve": ['slug'],
        "display_name": "ROW Trading pages FAQ's",
        "item_identifier": "name"
    },
    
    "EU CTA Footer CMS": {
        "fields_to_translate": [
            'description'
        ],
        "fields_to_preserve": ['slug'],
        "display_name": "EU CTA Footer",
        "item_identifier": "description"
    },

        "CTA Footer CMS": {
        "fields_to_translate": [
            'description'
        ],
        "fields_to_preserve": ['slug'],
        "display_name": " CTA Footer CMS",
        "item_identifier": "description"
    },

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

def translate_with_openai_concurrent(text, target_language, api_key):
    """Thread-safe version of translate_with_openai for concurrent processing"""
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

        If the {target_language} is "sw", then in that case translate to Swahili only.
        
        DO NOT TRANSLATE the following terms - keep them exactly as they appear:
        {terms_list}
        
        Follow these additional rules when translating:
        - When encountering the word "Deriv" and any succeeding word, keep it in English. For example, "Deriv Blog," "Deriv Life," "Deriv Bot," and "Deriv App" should be kept in English.
        - Keep product names such as P2P, MT5, Deriv X, Deriv cTrader, SmartTrader, Deriv Trader, Deriv GO, Deriv Bot, and Binary Bot in English.
        - When encountering the symbol "?", mirror it in the translated text when the target language is Arabic.
        
        Return only the translation, no explanations."""
        
        # Log OpenAI request
        logger.info(f"\n{'='*50}")
        logger.info("OPENAI API REQUEST")
        logger.info(f"{'='*50}")
        logger.info(f"Model: gpt-4.1-mini")
        logger.info("System Message:")
        logger.info(system_message)
        logger.info("\nUser Message:")
        logger.info(text)
        
        # Make API call with timing
        start_time = time.time()
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": text}
            ]
            # temperature=0.3
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

def execute_curl_command_concurrent(collection_id, item_id, api_key, cms_locale_id, field_data):
    """Thread-safe version of execute_curl_command for concurrent processing"""
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
        if response.status_code == 200:
            return {
                'status_code': response.status_code,
                'response': response.json(),
                'error': None
            }
        else:
            return {
                'status_code': response.status_code,
                'response': response.text,
                'error': f"HTTP Error: {response.status_code}"
            }
    except Exception as e:
        return {
            'status_code': None,
            'response': None,
            'error': str(e)
        }

def translate_with_claude_portuguese(text, target_language, api_key):
    """Thread-safe version of translate with Claude API for Portuguese translations"""
    try:
        # Log translation request details
        logger.info(f"\n{'='*50}")
        logger.info("CLAUDE PORTUGUESE TRANSLATION REQUEST DETAILS")
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
        
        # Format terms for prompt
        terms_list = "\n".join([f"- {term}" for term in do_not_translate_terms])
        
        # Create Claude client
        client = anthropic.Anthropic(api_key=api_key)
        
        system_message = f"""Act as a professional translator with 20 years of experience specializing in European Portuguese (Portugal) and these translation MUST strictly adhere to Portugal's Portuguese language standards, NOT Brazilian Portuguese. Your role is to ensure accurate, contextually relevant translations, adhering strictly to guidelines and using available resources efficiently. Translations should read naturally to native speakers of the target language, not just as direct translations from English.
        Translate the text to {target_language}.
        
        DO NOT TRANSLATE the following terms - keep them exactly as they appear:
        {terms_list}
        
        Follow these additional rules when translating:
        - When encountering the word "Deriv" and any succeeding word, keep it in English. For example, "Deriv Blog," "Deriv Life," "Deriv Bot," and "Deriv App" should be kept in English.
        - Keep product names such as P2P, MT5, Deriv X, Deriv cTrader, SmartTrader, Deriv Trader, Deriv GO, Deriv Bot, and Binary Bot in English.
        
        Return only the translation, no explanations."""
        
        # Log Claude API request
        logger.info(f"\n{'='*50}")
        logger.info("CLAUDE API REQUEST (PORTUGUESE)")
        logger.info(f"{'='*50}")
        logger.info(f"Model: claude-3-5-sonnet")
        logger.info("System Message:")
        logger.info(system_message)
        logger.info("\nUser Message:")
        logger.info(text)
        
        # Make API call with timing
        start_time = time.time()
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            system=system_message,
            messages=[
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=8000
        )
        end_time = time.time()
        
        # Log Claude API response
        logger.info(f"\n{'='*50}")
        logger.info("CLAUDE API RESPONSE (PORTUGUESE)")
        logger.info(f"{'='*50}")
        logger.info(f"Response Time: {end_time - start_time:.2f} seconds")
        
        translated_text = response.content[0].text
        
        # Log translation result
        logger.info(f"\nTranslated Text Preview: {translated_text[:200]}..." if len(translated_text) > 200 else translated_text)
        
        # Log term preservation check
        logger.info(f"\n{'='*50}")
        logger.info("TERM PRESERVATION CHECK (PORTUGUESE)")
        logger.info(f"{'='*50}")
        for term in do_not_translate_terms:
            if term in text and term in translated_text:
                logger.info(f"✅ Term preserved: {term}")
            elif term in text and term not in translated_text:
                logger.warning(f"⚠️ Term not preserved: {term}")
        
        logger.info(f"\n{'='*50}\n")
        
        return translated_text, None
    except Exception as e:
        error_msg = f"Claude Portuguese translation error: {str(e)}"
        logger.error(error_msg)
        logger.error(f"{'='*50}\n")
        return None, error_msg

def process_language_translation_concurrent(item_data, locale, openai_key, webflow_key, collection_id, config):
    """Process translation for a single language using concurrent approach"""
    # Store translations for this language
    current_translations = {}
    
    # Determine if we should use Claude API for Portuguese (only if Claude API key is available)
    is_portuguese = locale['code'].lower() in ['pt', 'pt-br', 'pt-pt']
    use_claude = is_portuguese and st.session_state.get('claude_api_key')
    
    # Translate each field - only translate fields in fields_to_translate
    for key, value in item_data['data'].items():
        if key in config['fields_to_translate'] and isinstance(value, str):
            # Translate the field using appropriate API
            if use_claude:
                # Use Claude for Portuguese if API key is available
                translated_text, error = translate_with_claude_portuguese(
                    value, locale['code'], st.session_state.claude_api_key
                )
            else:
                # Use OpenAI for all other languages and for Portuguese if Claude API key is not available
                translated_text, error = translate_with_openai_concurrent(
                    value, locale['code'], openai_key
                )
                
            if error:
                return {
                    'item': item_data['identifier'],
                    'language': locale['name'],
                    'status': 'error',
                    'message': f"Error translating {key}: {error}"
                }
            current_translations[key] = translated_text
        else:
            # Preserve other fields
            current_translations[key] = value
    
    # Execute update to Webflow
    result = execute_curl_command_concurrent(
        collection_id=collection_id,
        item_id=item_data['id'],
        api_key=webflow_key,
        cms_locale_id=locale['id'],
        field_data=current_translations
    )
    
    # Return result
    return {
        'item': item_data['identifier'],
        'language': locale['name'],
        'status': 'success' if not result.get('error') else 'error',
        'message': result.get('error', 'Translation completed successfully')
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
    
    # Check if at least one API key is available (OpenAI or Claude)
    if not st.session_state.get('openai_key') and not st.session_state.get('claude_api_key'):
        st.warning("Please add either an OpenAI API key or a Claude API key in the sidebar to enable translations")
        return
    
    # Display warnings about missing API keys 
    if not st.session_state.get('openai_key'):
        st.info("OpenAI API key is not set. Translations will not be available.")
    
    if not st.session_state.get('claude_api_key'):
        st.info("Claude API key is not set. Portuguese translations will use OpenAI instead of Claude.")
    
    # Track API credential changes
    if 'previous_api_key' not in st.session_state:
        st.session_state.previous_api_key = st.session_state.api_key
    if 'previous_site_id' not in st.session_state:
        st.session_state.previous_site_id = st.session_state.site_id
    
    # Reset cached data if credentials have changed
    if (st.session_state.previous_api_key != st.session_state.api_key or 
        st.session_state.previous_site_id != st.session_state.site_id):
        # Reset all cached data
        st.session_state.cms_locales = None
        st.session_state.collections = None
        st.session_state.selected_collection = None
        st.session_state.collection_items = None
        st.session_state.parsed_items = None
        st.session_state.selected_item = 'All'
        st.session_state.multi_selected_items = []
        
        # Update the stored credentials
        st.session_state.previous_api_key = st.session_state.api_key
        st.session_state.previous_site_id = st.session_state.site_id
        
        # Inform the user
        st.success("API credentials updated. Data will be refreshed.")
    
    # Initialize session state variables if they don't exist
    if 'cms_locales' not in st.session_state:
        st.session_state.cms_locales = None
    if 'collections' not in st.session_state:
        st.session_state.collections = None
    if 'selected_collection' not in st.session_state:
        st.session_state.selected_collection = None
    if 'collection_items' not in st.session_state:
        st.session_state.collection_items = None
    if 'parsed_items' not in st.session_state:
        st.session_state.parsed_items = None
    if 'selected_item' not in st.session_state:
        st.session_state.selected_item = 'All'
    if 'selected_mode' not in st.session_state:
        st.session_state.selected_mode = "Single Item"
    if 'multi_selected_items' not in st.session_state:
        st.session_state.multi_selected_items = []
    
    # Add mode selection at the top
    st.subheader("Translation Mode")
    mode_options = ["Single Item", "The Need for Speed (Batch Translation)"]
    selected_mode = st.radio("Select Mode", mode_options, key="mode_selection")
    st.session_state.selected_mode = selected_mode
    
    # Display warning if "The Need for Speed" is selected but not for Blog collection
    if st.session_state.selected_mode == "The Need for Speed (Batch Translation)" and st.session_state.selected_collection and "Blog" not in st.session_state.selected_collection:
        st.warning("⚠️ 'The Need for Speed' mode is currently only available for Blog collections. Please select a Blog collection to use this feature.")
    
    # Fetch CMS locales (different from site locales in app.py)
    st.subheader("CMS Locales")
    
    # Fetch CMS locales if not already in session state
    if st.session_state.cms_locales is None:
        with st.spinner("Fetching CMS locales..."):
            cms_locales = get_cms_locales(st.session_state.site_id, st.session_state.api_key)
            if cms_locales:
                st.session_state.cms_locales = cms_locales
    
    # Display locales from session state
    if st.session_state.cms_locales:
        locale_data = {
            "Language": [locale.get('name', 'Unnamed') for locale in st.session_state.cms_locales],
            "CMS Locale ID": [locale.get('id', 'No ID') for locale in st.session_state.cms_locales],
            "Language Code": [locale.get('code', 'No code') for locale in st.session_state.cms_locales],
            "Default": [str(locale.get('default', False)) for locale in st.session_state.cms_locales]
        }
        st.table(locale_data)
    
    # Replace Collection ID input with dropdown
    st.subheader("Collection Details")
    
    # Only fetch collections if not already in session state
    if st.session_state.collections is None:
        with st.spinner("Fetching collections..."):
            collections = get_collections(st.session_state.site_id, st.session_state.api_key)
            if collections:
                st.session_state.collections = collections
    
    # Display collections from session state
    if st.session_state.collections:
        collection_options = [f"{col['displayName']} ({col['id']})" for col in st.session_state.collections]
        
        # Use selectbox with key to maintain state
        selected_collection = st.selectbox(
            "Select Collection",
            options=collection_options,
            help="Choose the collection you want to manage",
            key="collection_selectbox"
        )
        
        # Only fetch items if collection changes
        if selected_collection != st.session_state.selected_collection:
            st.session_state.selected_collection = selected_collection
            st.session_state.collection_items = None  # Clear cached items
            st.session_state.parsed_items = None
            st.session_state.selected_item = 'All'  # Reset selected item
            st.session_state.multi_selected_items = []  # Reset multi-selected items
        
        if selected_collection:
            # Get collection type and config
            collection_name = selected_collection.split('(')[0].strip()
            collection_type, config = get_collection_config(collection_name)
            
            if not config:
                st.warning(f"Collection type '{collection_name}' is not configured for translation.\n\nAvailable types: {', '.join(COLLECTION_CONFIGS.keys())}")
                return
            
            # Extract collection ID
            collection_id = selected_collection.split('(')[-1].strip(')')
            
            # Only fetch items if not already in session state
            if st.session_state.collection_items is None:
                with st.status("Loading collection items...", expanded=True) as status:
                    items = get_all_collection_items(st.session_state.site_id, collection_id, st.session_state.api_key)
                    if items:
                        st.session_state.collection_items = items
                        
                        # Parse items based on collection type
                        st.session_state.parsed_items = parse_collection_items(items, collection_type, config)
                        status.update(label="Collection items loaded successfully!", state="complete", expanded=False)
            
            # Use items from session state
            if st.session_state.parsed_items:
                parsed_items = st.session_state.parsed_items
                
                # Add search functionality
                search_term = st.text_input("Search items", key="search_items")
                
                # Filter items based on search term
                filtered_items = parsed_items
                if search_term:
                    filtered_items = [item for item in parsed_items 
                                     if search_term.lower() in item['identifier'].lower() or 
                                        search_term.lower() in item['slug'].lower()]
                    st.write(f"Found {len(filtered_items)} items matching '{search_term}'")
                
                # SINGLE ITEM MODE
                if st.session_state.selected_mode == "Single Item":
                    # Create a selectbox with filtered items
                    item_options = ['All'] + [f"{item['identifier']} ({item['slug']})" for item in filtered_items]
                    
                    # Use selectbox with key to maintain state
                    selected_item = st.selectbox(
                        f"Select {config['display_name']} (Total: {len(filtered_items)} of {len(parsed_items)})",
                        options=item_options,
                        key="item_selectbox"
                    )
                    
                    # Update selected item in session state
                    st.session_state.selected_item = selected_item
                    
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
                                            for locale in st.session_state.cms_locales]
                                )
                                
                                if target_language:
                                    # Extract CMS Locale ID and language code
                                    cms_locale_id = target_language.split(' - ')[-1]
                                    language_code = target_language.split('(')[1].split(')')[0]
                                    
                                    # Check if this is Portuguese
                                    is_portuguese = language_code.lower() in ['pt', 'pt-br', 'pt-pt']
                                    if is_portuguese and not st.session_state.get('claude_api_key'):
                                        st.info("You are translating to Portuguese. For better European Portuguese translations, consider adding a Claude API key in the sidebar. OpenAI will be used instead.")
                                    
                                    # Initialize a dictionary to store translations
                                    if 'current_translations' not in st.session_state:
                                        st.session_state.current_translations = {}
                                    
                                    # Display form with translations in a two-column layout
                                    with st.form("translation_form"):
                                        edited_fields = {}
                                        
                                        # Add a header for the columns
                                        col_orig, col_trans = st.columns(2)
                                        with col_orig:
                                            st.markdown("### Original Content")
                                        with col_trans:
                                            st.markdown("### Translated Content")
                                        
                                        # Process each field
                                        for key, value in selected_data['data'].items():
                                            if key in config['fields_to_preserve']:
                                                edited_fields[key] = value
                                                continue
                                            
                                            if isinstance(value, str):
                                                # Create two columns for each field
                                                col_orig, col_trans = st.columns(2)
                                                
                                                # Show original text in left column
                                                with col_orig:
                                                    if len(value) > 200:
                                                        st.text_area(
                                                            f"Original {key}",
                                                            value=value,
                                                            height=300,
                                                            disabled=True
                                                        )
                                                    else:
                                                        st.text_input(
                                                            f"Original {key}",
                                                            value=value,
                                                            disabled=True
                                                        )
                                                
                                                # Show editable translated text in right column
                                                with col_trans:
                                                    # Use the stored translation if available
                                                    translation_value = st.session_state.current_translations.get(key, value)
                                                    
                                                    if len(value) > 200:
                                                        edited_fields[key] = st.text_area(
                                                            key,
                                                            value=translation_value,
                                                            height=300
                                                        )
                                                    else:
                                                        edited_fields[key] = st.text_input(
                                                            key,
                                                            value=translation_value
                                                        )
                                        
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            translate_button = st.form_submit_button("Translate")
                                        with col2:
                                            update_button = st.form_submit_button("Update Content")
                                        
                                        if translate_button:
                                            # Check if we're already in a post-translation state
                                            if 'just_translated' in st.session_state and st.session_state.just_translated:
                                                # Clear the flag and don't rerun
                                                st.session_state.just_translated = False
                                            else:
                                                with st.spinner("Translating content..."):
                                                    # Clear previous translations
                                                    st.session_state.current_translations = {}
                                                    
                                                    for key, value in selected_data['data'].items():
                                                        if isinstance(value, str) and key not in config['fields_to_preserve']:
                                                            # Use the same logic as process_language_translation_concurrent
                                                            # to determine which API to use
                                                            is_portuguese = language_code.lower() in ['pt', 'pt-br', 'pt-pt']
                                                            use_claude = is_portuguese and st.session_state.get('claude_api_key')
                                                            
                                                            if use_claude:
                                                                # Use Claude for Portuguese if API key is available
                                                                translated_text, error = translate_with_claude_portuguese(
                                                                    value, language_code, st.session_state.claude_api_key
                                                                )
                                                            else:
                                                                # Use OpenAI for all other languages and for Portuguese if Claude API key is not available
                                                                translated_text, error = translate_with_openai_concurrent(
                                                                    value, language_code, st.session_state.openai_key
                                                                )
                                                            
                                                            if error:
                                                                st.error(f"Error translating {key}: {error}")
                                                            else:
                                                                # Store the translation in session state
                                                                st.session_state.current_translations[key] = translated_text
                                                                edited_fields[key] = translated_text
                                                    
                                                    # Set a flag to indicate translation just completed
                                                    st.session_state.just_translated = True
                                                    # Force a rerun to show the translations
                                                    st.rerun()
                                        
                                        if update_button:
                                            with st.spinner("Updating content..."):
                                                result = execute_curl_command_concurrent(
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
                                    languages_to_translate = [l for l in st.session_state.cms_locales if not l.get('default', False)]
                                    total_languages = len(languages_to_translate)
                                    
                                    for idx, locale in enumerate(languages_to_translate):
                                        # Update progress (ensure it's between 0 and 1)
                                        progress = min(idx / total_languages, 1.0)
                                        progress_container.progress(progress)
                                        
                                        # Update status message
                                        status_container.info(f"Translating to {locale['name']} ({locale['code']})...")
                                        
                                        # Store translations for this language
                                        current_translations = {}
                                        
                                        # Process this language using the same function used in batch mode
                                        # This will automatically use Claude for Portuguese if available
                                        result = process_language_translation_concurrent(
                                            item_data=selected_data,
                                            locale=locale,
                                            openai_key=st.session_state.openai_key,
                                            webflow_key=st.session_state.api_key,
                                            collection_id=collection_id,
                                            config=config
                                        )
                                        
                                        # Store result
                                        translation_results.append({
                                            'language': locale['name'],
                                            'status': 'success' if not result.get('message') else 'error',
                                            'message': result.get('message', 'Translation completed successfully')
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
                
                # THE NEED FOR SPEED MODE (BATCH TRANSLATION)
                else:
                    st.subheader("The Need for Speed - Batch Translation")
                    st.write("Select multiple items to translate to all languages at once.")
                    
                    # Add option for parallel or sequential processing
                    translation_processing = st.radio(
                        "Translation Processing Method",
                        ["Parallel (Faster, translates all languages in parallel)", 
                         "Sequential (Slower, translates one language at a time)"],
                        index=0,
                        key="translation_processing"
                    )
                    
                    # Add max workers option for parallel processing
                    if translation_processing == "Parallel (Faster, translates all languages in parallel)":
                        max_workers = st.slider(
                            "Maximum parallel translations",
                            min_value=2,
                            max_value=10,
                            value=5,
                            help="Higher values may be faster but could hit API rate limits"
                        )
                    
                    # Create a multiselect with filtered items
                    item_options = [f"{item['identifier']} ({item['slug']})" for item in filtered_items]
                    
                    # Use multiselect to allow multiple item selection
                    multi_selected_items = st.multiselect(
                        f"Select {config['display_name']} items to translate (Total: {len(filtered_items)} of {len(parsed_items)})",
                        options=item_options,
                        key="multi_item_selectbox"
                    )
                    
                    # Update selected items in session state
                    st.session_state.multi_selected_items = multi_selected_items
                    
                    if multi_selected_items:
                        st.write(f"Selected {len(multi_selected_items)} items for batch translation.")
                        
                        # Get non-default languages
                        languages_to_translate = [l for l in st.session_state.cms_locales if not l.get('default', False)]
                        
                        # Display language information
                        st.write(f"Will translate to {len(languages_to_translate)} languages:")
                        for locale in languages_to_translate:
                            st.write(f"- {locale['name']} ({locale['code']})")
                        
                        # Display fields that will be translated
                        st.write("Fields that will be translated:")
                        for field in config['fields_to_translate']:
                            st.write(f"- {field}")
                        
                        # Start batch translation button
                        if st.button("Start Batch Translation", key="start_batch_translation"):
                            # Verify that the OpenAI API key is available
                            if not st.session_state.get('openai_key'):
                                st.error("OpenAI API Key is missing. Please add it in the sidebar to enable translations.")
                                return
                            
                            # Debug information
                            st.write("Debug Information:")
                            st.write(f"OpenAI API Key available: {bool(st.session_state.get('openai_key'))}")
                            st.write(f"Webflow API Key available: {bool(st.session_state.get('api_key'))}")
                            
                            # Create containers for progress tracking
                            main_progress_container = st.empty()
                            main_status_container = st.empty()
                            item_progress_container = st.empty()
                            item_status_container = st.empty()
                            language_status_container = st.empty()
                            timer_container = st.empty()
                            results_container = st.container()
                            
                            # Initialize results and timer
                            all_results = []
                            start_time = time.time()
                            
                            # Function to format elapsed time
                            def format_elapsed_time(seconds):
                                return str(datetime.timedelta(seconds=int(seconds)))
                            
                            # Get selected item data
                            selected_items_data = []
                            for selected_item in multi_selected_items:
                                selected_slug = selected_item.split('(')[-1].strip(')')
                                item_data = next(
                                    (item for item in filtered_items if item['slug'] == selected_slug),
                                    None
                                )
                                if item_data:
                                    selected_items_data.append(item_data)
                            
                            # Update main progress
                            total_items = len(selected_items_data)
                            
                            # PARALLEL PROCESSING
                            if translation_processing == "Parallel (Faster, translates all languages in parallel)":
                                # Process each item
                                for item_idx, item_data in enumerate(selected_items_data):
                                    # Update elapsed time
                                    elapsed = time.time() - start_time
                                    timer_container.info(f"⏱️ Elapsed time: {format_elapsed_time(elapsed)}")
                                    
                                    # Update main progress
                                    main_progress = min((item_idx) / total_items, 1.0)
                                    main_progress_container.progress(main_progress)
                                    main_status_container.info(f"Processing item {item_idx + 1} of {total_items}: {item_data['identifier']}")
                                    
                                    # Reset item progress
                                    item_progress_container.progress(0)
                                    item_status_container.info(f"Starting translation for: {item_data['identifier']}")
                                    
                                    # Item start time
                                    item_start_time = time.time()
                                    
                                    # Process all languages for this item in parallel using ThreadPoolExecutor
                                    language_status_container.info(f"Translating to {len(languages_to_translate)} languages in parallel...")
                                    
                                    # Create tasks for parallel execution
                                    tasks = []
                                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                                        # Submit tasks to the executor
                                        futures = []
                                        for locale in languages_to_translate:
                                            future = executor.submit(
                                                process_language_translation_concurrent,
                                                item_data=item_data,
                                                locale=locale,
                                                openai_key=st.session_state.openai_key,
                                                webflow_key=st.session_state.api_key,
                                                collection_id=collection_id,
                                                config=config
                                            )
                                            futures.append(future)
                                        
                                        # Process results as they complete
                                        item_results = []
                                        for i, future in enumerate(concurrent.futures.as_completed(futures)):
                                            result = future.result()
                                            item_results.append(result)
                                            
                                            # Update progress
                                            progress = (i + 1) / len(futures)
                                            item_progress_container.progress(progress)
                                            
                                            # Update status in real-time
                                            if result['status'] == 'success':
                                                language_status_container.info(f"Completed {i+1}/{len(futures)}: {result['language']} ✅")
                                            else:
                                                language_status_container.warning(f"Completed {i+1}/{len(futures)}: {result['language']} ❌ - {result['message']}")
                                        
                                        # Add item results to all results
                                        all_results.extend(item_results)
                                        
                                        # Calculate item processing time
                                        item_elapsed = time.time() - item_start_time
                                        
                                        # Update results in real-time
                                        with results_container:
                                            st.write(f"Results for {item_data['identifier']}:")
                                            with st.expander(f"View translation results for {item_data['identifier']}", expanded=False):
                                                for res in item_results:
                                                    if res['status'] == 'success':
                                                        st.success(f"✅ {res['language']}: {res['message']}")
                                                    else:
                                                        st.error(f"❌ {res['language']}: {res['message']}")
                                        
                                        # Update item status
                                        item_status_container.success(f"Completed translations for: {item_data['identifier']} in {format_elapsed_time(item_elapsed)}")
                            
                            # SEQUENTIAL PROCESSING (ORIGINAL METHOD)
                            else:
                                # Process each item
                                for item_idx, item_data in enumerate(selected_items_data):
                                    # Update elapsed time
                                    elapsed = time.time() - start_time
                                    timer_container.info(f"⏱️ Elapsed time: {format_elapsed_time(elapsed)}")
                                    
                                    # Update main progress
                                    main_progress = min((item_idx) / total_items, 1.0)
                                    main_progress_container.progress(main_progress)
                                    main_status_container.info(f"Processing item {item_idx + 1} of {total_items}: {item_data['identifier']}")
                                    
                                    # Reset item progress
                                    item_progress_container.progress(0)
                                    item_status_container.info(f"Starting translation for: {item_data['identifier']}")
                                    
                                    # Item start time
                                    item_start_time = time.time()
                                    
                                    # Process each language for this item
                                    item_results = []
                                    for lang_idx, locale in enumerate(languages_to_translate):
                                        # Update elapsed time
                                        elapsed = time.time() - start_time
                                        timer_container.info(f"⏱️ Elapsed time: {format_elapsed_time(elapsed)}")
                                        
                                        # Update language progress
                                        language_status_container.info(f"Translating to {locale['name']} ({locale['code']})...")
                                        
                                        # Process this language
                                        result = process_language_translation_concurrent(
                                            item_data=item_data,
                                            locale=locale,
                                            openai_key=st.session_state.openai_key,
                                            webflow_key=st.session_state.api_key,
                                            collection_id=collection_id,
                                            config=config
                                        )
                                        
                                        # Add to results
                                        item_results.append(result)
                                        
                                        # Update item progress
                                        item_progress = min((lang_idx + 1) / len(languages_to_translate), 1.0)
                                        item_progress_container.progress(item_progress)
                                    
                                    # Add item results to all results
                                    all_results.extend(item_results)
                                    
                                    # Calculate item processing time
                                    item_elapsed = time.time() - item_start_time
                                    
                                    # Update results in real-time
                                    with results_container:
                                        st.write(f"Results for {item_data['identifier']}:")
                                        with st.expander(f"View translation results for {item_data['identifier']}", expanded=False):
                                            for res in item_results:
                                                if res['status'] == 'success':
                                                    st.success(f"✅ {res['language']}: {res['message']}")
                                                else:
                                                    st.error(f"❌ {res['language']}: {res['message']}")
                                    
                                    # Update item status
                                    item_status_container.success(f"Completed translations for: {item_data['identifier']} in {format_elapsed_time(item_elapsed)}")
                                
                            # Calculate total elapsed time
                            total_elapsed = time.time() - start_time
                            
                            # Update main progress when complete
                            main_progress_container.progress(1.0)
                            main_status_container.success(f"Completed batch translation for all {total_items} items in {format_elapsed_time(total_elapsed)}!")
                            
                            # Display summary
                            st.subheader("Batch Translation Summary")
                            success_count = sum(1 for res in all_results if res['status'] == 'success')
                            error_count = sum(1 for res in all_results if res['status'] == 'error')
                            
                            # Show basic stats outside expander
                            st.write(f"Total translations: {len(all_results)} ({success_count} successful, {error_count} failed)")
                            st.write(f"Total time: {format_elapsed_time(total_elapsed)}")
                            
                            # Show detailed stats in expander
                            with st.expander("View detailed translation statistics", expanded=False):
                                st.write(f"Processing method: {translation_processing}")
                                st.write(f"Total translations: {len(all_results)}")
                                st.write(f"Successful translations: {success_count}")
                                st.write(f"Failed translations: {error_count}")
                                st.write(f"Total time: {format_elapsed_time(total_elapsed)}")
                                st.write(f"Average time per item: {format_elapsed_time(total_elapsed/max(total_items, 1))}")
                                st.write(f"Average time per translation: {format_elapsed_time(total_elapsed/max(len(all_results), 1))}")
                            
                            # Clear progress indicators
                            language_status_container.empty()
                            item_progress_container.empty()
                            item_status_container.empty()

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
