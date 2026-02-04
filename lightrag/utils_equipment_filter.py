"""Equipment entity validation and filtering utilities for industrial knowledge graphs."""

import os
import re
from typing import Tuple, Dict, Optional, Set
from lightrag.utils import logger

# Default lists of known consumables, tiny parts, and brands
DEFAULT_CONSUMABLES = {
    "o-ring", "oring", "o ring",
    "gasket", "seal", "sealant",
    "bolt", "nut", "screw", "washer", "fastener",
    "lubricant", "oil", "grease", "coolant",
    "paint", "coating", "varnish",
    "cap", "plug", "stopper",
    "shim", "spacer",
    "tape", "adhesive", "sealant tape",
}

DEFAULT_TINY_PARTS = {
    "o-ring", "oring", "o ring",
    "gasket", "seal", "pin",
    "bolt", "nut", "screw", "washer",
    "spring", "clip", "latch",
    "ring", "retainer",
}

DEFAULT_BRANDS = {
    "baker hughes", "bakerhughes",
    "ge", "general electric",
    "siemens",
    "asco", "asco numatics",
    "woodward",
    "honeywell",
    "emerson", "emerson process management",
    "flowserve",
    "eaton",
    "parker", "parker hannifin",
    "bosch",
    "trane",
    "carrier",
    "danaher",
}


def _load_list_from_env(env_var: str, default_set: Set[str]) -> Set[str]:
    """
    Load a list from environment variable or use defaults as fallback.
    
    Strategy:
    - If environment variable is provided: Use ONLY the provided list (REPLACEMENT)
    - If environment variable is NOT provided: Use the default list (FALLBACK)
    
    Args:
        env_var: Environment variable name to check
        default_set: Default set to use if env var is not provided
        
    Returns:
        Set of items (either from environment or defaults)
    """
    env_value = os.getenv(env_var)
    if not env_value:
        # No env var provided, use defaults
        logger.debug(f"{env_var}: Not provided, using {len(default_set)} default items")
        return default_set.copy()
    
    # Parse comma-separated values and use ONLY these items (no merge with defaults)
    custom_items = {item.strip().lower() for item in env_value.split(',') if item.strip()}
    
    logger.debug(f"{env_var}: Provided, using {len(custom_items)} custom items (defaults ignored)")
    return custom_items


# Load from environment or use defaults (cached)
KNOWN_CONSUMABLES = _load_list_from_env("ENTITY_CUSTOM_CONSUMABLES", DEFAULT_CONSUMABLES)
KNOWN_TINY_PARTS = _load_list_from_env("ENTITY_CUSTOM_TINY_PARTS", DEFAULT_TINY_PARTS)
PURE_BRANDS = _load_list_from_env("ENTITY_CUSTOM_BRANDS", DEFAULT_BRANDS)

# Verbs that indicate machine functions (acceptable)
MACHINE_FUNCTION_VERBS = {
    # Transmission/Control
    "transmit", "control", "regulate", "manage", "direct", "guide",
    "modulate", "coordinate", "synchronize",
    # Conversion/Transformation
    "convert", "compress", "expand", "generate", "produce", "pump",
    "circulate", "flow", "distribute", "supply", "transfer",
    "cool", "heat", "warm", "dissipate",
    # Protection/Isolation
    "protect", "relieve", "vent", "seal", "dampen", "isolate",
    "filter", "separate", "prevent", "block", "absorb",
    # Movement/Positioning
    "rotate", "move", "position", "hold", "support", "suspend",
    "bear", "carry", "lift", "lower", "raise",
    # Sensing
    "measure", "sense", "detect", "monitor", "indicate",
    # Lubrication
    "lubricate", "coat",
}

# Verbs that indicate administrative/non-machine functions (reject)
ADMINISTRATIVE_VERBS = {
    "manage", "organize", "track", "log", "record", "report",
    "sell", "buy", "trade", "market", "advertise",
    "communicate", "notify", "alert", "announce",
    "approve", "authorize", "validate", "verify",
    "schedule", "plan", "arrange",
}


def _get_filter_config() -> Dict:
    """
    Build filter configuration from environment variables.
    
    Returns:
        Dict with filter configuration parameters
    """
    return {
        "min_length": int(os.getenv("ENTITY_MIN_LENGTH", "3")),
        "max_numeric_ratio": float(os.getenv("ENTITY_MAX_NUMERIC_RATIO", "0.4")),
        "strategy": os.getenv("ENTITY_VALIDATION_STRATEGY", "balanced"),
        "debug": os.getenv("ENTITY_FILTER_DEBUG", "false").lower() == "true",
    }


def is_valid_equipment_entity(
    entity_name: str,
    entity_type: str,
    entity_function: str,
    filter_config: Optional[Dict] = None,
) -> Tuple[bool, str]:
    """
    Validate if an entity is a valid equipment/component in industrial context.
    
    Args:
        entity_name: Name of the entity
        entity_type: Type of the entity (manufacturer, equipment, component, etc.)
        entity_function: Function description (verb + object format)
        filter_config: Optional configuration dict with custom filters (from environment)
        
    Returns:
        Tuple of (is_valid: bool, reason: str)
    """
    
    if not entity_name or not entity_name.strip():
        return False, "Empty entity name"
    
    # Load configuration from environment if not provided
    if filter_config is None:
        filter_config = _get_filter_config()
    
    # Extract configuration parameters
    min_length = filter_config.get("min_length", 3)
    max_numeric_ratio = filter_config.get("max_numeric_ratio", 0.4)
    debug = filter_config.get("debug", False)
    
    # Normalize for comparison
    normalized_name = entity_name.lower().strip()
    normalized_type = entity_type.lower().strip() if entity_type else ""
    normalized_func = entity_function.lower().strip() if entity_function else ""
    
    # Check 1: Name length (configurable)
    if len(entity_name) < min_length:
        reason = f"Name too short (< {min_length} chars): '{entity_name}'"
        if debug:
            logger.info(f"[REJECTED] {entity_name} - {reason}")
        return False, reason
    
    # Check 2: Numeric character ratio (configurable, likely model codes)
    numeric_char_count = sum(1 for c in entity_name if c.isdigit())
    total_chars = len([c for c in entity_name if c.isalnum() or c == "-"])
    
    if total_chars > 0:
        numeric_ratio = numeric_char_count / total_chars
        
        # Too many numbers relative to letters (e.g., "111TE" has 60% numbers)
        if numeric_ratio > max_numeric_ratio:
            reason = f"Likely model/part code (numeric ratio: {numeric_ratio:.0%})"
            if debug:
                logger.info(f"[REJECTED] {entity_name} - {reason}")
            return False, reason
    
    # Check 3: Known consumables (from environment or defaults)
    if normalized_name in KNOWN_CONSUMABLES:
        reason = f"Known consumable: '{entity_name}'"
        if debug:
            logger.info(f"[REJECTED] {entity_name} - {reason}")
        return False, reason
    
    # Check 4: Known tiny parts (from environment or defaults)
    if normalized_name in KNOWN_TINY_PARTS:
        reason = f"Known tiny part/consumable: '{entity_name}'"
        if debug:
            logger.info(f"[REJECTED] {entity_name} - {reason}")
        return False, reason
    
    # Check 5: Pure brand names (from environment or defaults)
    # Brands with TYPE=manufacturer or brand should be accepted
    is_brand_type = normalized_type in ["manufacturer", "brand", "company", "organization"]
    
    if normalized_name in PURE_BRANDS:
        if is_brand_type:
            reason = f"Valid manufacturer/brand: '{entity_name}'"
            if debug:
                logger.info(f"[ACCEPTED] {entity_name} - {reason}")
            return True, reason
        else:
            # Could be a brand mentioned in context, allow but log
            reason = f"Brand (type: {entity_type}): '{entity_name}'"
            if debug:
                logger.info(f"[ACCEPTED] {entity_name} - {reason}")
            return True, reason
    
    # Check 6: Validate function verb if provided and type is not brand
    if not is_brand_type and normalized_func and normalized_func != "unknown":
        # Extract main verb (first word)
        verb_match = re.match(r'^(\w+)', normalized_func)
        if verb_match:
            main_verb = verb_match.group(1).lower()
            
            # Check if it's an administrative verb
            if main_verb in ADMINISTRATIVE_VERBS:
                reason = f"Administrative function verb '{main_verb}' not suitable for equipment: '{entity_function}'"
                if debug:
                    logger.info(f"[REJECTED] {entity_name} - {reason}")
                return False, reason
            
            # Check if it's a known machine verb
            if main_verb not in MACHINE_FUNCTION_VERBS:
                # Unknown verb - check if it's a real word (not gibberish)
                if len(main_verb) >= 3 and main_verb.isalpha():
                    # Real word but uncommon - allow with warning
                    reason = f"Accepted (uncommon verb: {main_verb})"
                    if debug:
                        logger.debug(f"Uncommon machine function verb '{main_verb}' for entity '{entity_name}': '{entity_function}'")
                    return True, reason
                else:
                    # Gibberish or too short
                    reason = f"Invalid function verb: '{entity_function}'"
                    if debug:
                        logger.info(f"[REJECTED] {entity_name} - {reason}")
                    return False, reason
    
    # Check 7: If no function or function is "unknown", still accept if type is reasonable
    if not normalized_func or normalized_func == "unknown":
        if is_brand_type:
            reason = f"Valid manufacturer/brand (no function): '{entity_name}'"
            if debug:
                logger.info(f"[ACCEPTED] {entity_name} - {reason}")
            return True, reason
        # For equipment/component types without function, still accept
        # (LLM may not always provide good functions)
        reason = f"Accepted (no function, type: {entity_type})"
        if debug:
            logger.debug(f"No function provided for entity '{entity_name}' of type '{entity_type}' - allowing")
        return True, reason
    
    # Default: Accept valid equipment
    reason = f"Valid entity: '{entity_name}' (type: {entity_type})"
    if debug:
        logger.info(f"[ACCEPTED] {entity_name} - {reason}")
    return True, reason


def deduplicate_entities_advanced(
    entities: list[Dict],
    filter_config: Optional[Dict] = None,
) -> list[Dict]:
    """
    Deduplicate entities using 6 strategies:
    1. Singular/Plural normalization
    2. Case normalization
    3. Punctuation normalization
    4. Whitespace normalization
    5. Suffix merging
    6. Prefix/Translation handling
    
    Args:
        entities: List of entity dicts with keys: entity_name, entity_type, etc.
        filter_config: Optional configuration
        
    Returns:
        Deduplicated list of entities
    """
    if not entities:
        return []
    
    # Filter out None and invalid entries
    valid_entities = [e for e in entities if e is not None and isinstance(e, dict)]
    
    if not valid_entities:
        return []
    
    # Build a map of normalized name -> original entities
    dedup_map: Dict[str, Dict] = {}
    merge_history: Dict[str, list[str]] = {}  # Track which names were merged
    
    for entity in valid_entities:
        original_name = entity.get("entity_name", "")
        if not original_name:
            continue
        
        # Apply all 6 normalization strategies
        normalized = _normalize_entity_name(original_name)
        
        if normalized not in dedup_map:
            dedup_map[normalized] = entity.copy()
            merge_history[normalized] = [original_name]
        else:
            # Entity already exists - merge by keeping longer description
            existing = dedup_map[normalized]
            existing_desc_len = len(existing.get("description", "") or "")
            new_desc_len = len(entity.get("description", "") or "")
            
            if new_desc_len > existing_desc_len:
                dedup_map[normalized] = entity.copy()
            
            # Track merged entity
            if original_name not in merge_history[normalized]:
                merge_history[normalized].append(original_name)
    
    # Merge any remaining duplicates by fuzzy matching
    final_entities = list(dedup_map.values())
    
    # Add merge history as metadata (optional)
    for entity in final_entities:
        normalized = _normalize_entity_name(entity.get("entity_name", ""))
        if normalized in merge_history and len(merge_history[normalized]) > 1:
            entity["_merged_from"] = merge_history[normalized]
    
    return final_entities


def _normalize_entity_name(name: str) -> str:
    """
    Apply all 6 normalization strategies to entity name.
    
    Returns a canonical form for deduplication.
    """
    if not name:
        return ""
    
    # Strategy 1: Punctuation normalization (must come first)
    normalized = _normalize_punctuation(name)
    
    # Strategy 2: Whitespace normalization
    normalized = _normalize_whitespace(normalized)
    
    # Strategy 3: Case normalization (lowercase for comparison)
    normalized = normalized.lower()
    
    # Strategy 4: Suffix merging (remove common suffixes)
    normalized = _merge_suffixes(normalized)
    
    # Strategy 5: Singular/Plural normalization
    normalized = _normalize_singular_plural(normalized)
    
    # Strategy 6: Prefix/Translation handling
    normalized = _handle_translations(normalized)
    
    return normalized.strip()


def _normalize_singular_plural(name: str) -> str:
    """Normalize singular/plural forms using simple rules."""
    # Try to use inflect library if available (optional)
    try:
        import inflect
        engine = inflect.engine()
        # Convert plural to singular
        singular = engine.singular_noun(name)
        if singular:
            return singular
    except (ImportError, ModuleNotFoundError, Exception):
        # If inflect is not available, use fallback rules
        pass
    
    # Fallback simple rules (no inflect dependency)
    name_lower = name.lower()
    
    # Handle common plural endings
    if name_lower.endswith("ings"):
        return name[:-4] if len(name) > 4 else name
    elif name_lower.endswith("ing"):
        return name[:-3] if len(name) > 3 else name
    elif name_lower.endswith("ies"):
        return name[:-3] + "y" if len(name) > 3 else name
    elif name_lower.endswith("es") and not name_lower.endswith("ss"):
        return name[:-2] if len(name) > 2 else name
    elif name_lower.endswith("s") and not name_lower.endswith("ss"):
        return name[:-1] if len(name) > 1 else name
    
    return name


def _normalize_case(name: str) -> str:
    """Normalize to title case."""
    return " ".join(word.capitalize() for word in name.split())


def _normalize_punctuation(name: str) -> str:
    """Remove or normalize punctuation."""
    # Replace hyphens with spaces
    name = re.sub(r'-+', ' ', name)
    # Remove other punctuation except spaces
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    return name


def _normalize_whitespace(name: str) -> str:
    """Normalize whitespace (collapse multiple spaces to single)."""
    return re.sub(r'\s+', ' ', name).strip()


def _merge_suffixes(name: str) -> str:
    """Merge entities that differ only by common suffixes."""
    suffixes = [" system", " component", " unit", " assembly", " module"]
    
    name_lower = name.lower()
    for suffix in suffixes:
        if name_lower.endswith(suffix):
            return name[:-len(suffix)].strip()
    
    return name


def _handle_translations(name: str) -> str:
    """Handle Portuguese to English translations for common terms."""
    # Simple translation map for Portuguese industrial terms
    translations = {
        "gás turbina": "gas turbine",
        "compressor centrífugo": "centrifugal compressor",
        "bomba": "pump",
        "válvula": "valve",
        "tubo": "tube",
        "cilindro": "cylinder",
        "eixo": "shaft",
        "rotor": "rotor",
        "estator": "stator",
        "mancal": "bearing",
        "rolamento": "bearing",
    }
    
    name_lower = name.lower()
    for pt_term, en_term in translations.items():
        if name_lower == pt_term:
            return en_term
    
    return name
