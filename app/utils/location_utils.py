# ================================
# LOCATION UTILITIES (utils/location_utils.py)
# ================================

from typing import Optional

# German state mapping
STATE_NAME_MAPPING = {
    # English to German
    'bavaria': 'Bayern',
    'baden-württemberg': 'Baden-Württemberg',
    'baden-wurttemberg': 'Baden-Württemberg',
    'berlin': 'Berlin',
    'brandenburg': 'Brandenburg',
    'bremen': 'Bremen',
    'hamburg': 'Hamburg',
    'hesse': 'Hessen',
    'lower saxony': 'Niedersachsen',
    'mecklenburg-vorpommern': 'Mecklenburg-Vorpommern',
    'north rhine-westphalia': 'Nordrhein-Westfalen',
    'nrw': 'Nordrhein-Westfalen',
    'rhineland-palatinate': 'Rheinland-Pfalz',
    'saarland': 'Saarland',
    'saxony': 'Sachsen',
    'saxony-anhalt': 'Sachsen-Anhalt',
    'schleswig-holstein': 'Schleswig-Holstein',
    'thuringia': 'Thüringen',
    # German variations (already correct but normalize casing)
    'bayern': 'Bayern',
    'hessen': 'Hessen',
    'niedersachsen': 'Niedersachsen',
    'nordrhein-westfalen': 'Nordrhein-Westfalen',
    'rheinland-pfalz': 'Rheinland-Pfalz',
    'sachsen': 'Sachsen',
    'sachsen-anhalt': 'Sachsen-Anhalt',
    'thüringen': 'Thüringen',
}

def normalize_state_name(state: Optional[str]) -> Optional[str]:
    """
    Normalize state names to standard German format.
    
    Args:
        state: State name in any format (English, German, mixed case)
        
    Returns:
        Normalized German state name or original if not found
    """
    if not state:
        return state
    
    # Try to find in mapping (case-insensitive)
    normalized = STATE_NAME_MAPPING.get(state.lower().strip())
    if normalized:
        return normalized
    
    # If not found in mapping, check if it's already a valid German state
    # by checking if any mapping value matches (case-sensitive)
    german_states = set(STATE_NAME_MAPPING.values())
    if state in german_states:
        return state
    
    # Return original if no mapping found
    return state


def is_valid_german_state(state: str) -> bool:
    """
    Check if a state name is a valid German state.
    
    Args:
        state: State name to validate
        
    Returns:
        True if valid German state, False otherwise
    """
    if not state:
        return False
    
    german_states = set(STATE_NAME_MAPPING.values())
    return state in german_states or normalize_state_name(state) in german_states