import requests
import streamlit as st

def get_site_locales(site_id, api_key):
    """Get list of locales with their IDs"""
    url = f"https://api.webflow.com/v2/sites/{site_id}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        locales = []
        # Add primary locale
        primary = data.get('locales', {}).get('primary', {})
        if primary:
            primary['type'] = 'Primary'
            locales.append(primary)
        
        # Add secondary locales
        secondary = data.get('locales', {}).get('secondary', [])
        for locale in secondary:
            locale['type'] = 'Secondary'
            locales.append(locale)
            
        return locales
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        st.error(f"Error fetching site locales: {str(e)}")
        return []
