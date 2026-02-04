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
# NOTE: This is an ORIENTATIVE list, not exhaustive
# - Only includes CLEAR machine function verbs (unambiguous)
# - Ambiguous verbs like "manage", "monitor", "carry" are excluded (could be administrative)
# - Default strategy: if verb is unknown, REJECT for Type="Other", ALLOW for Type="Equipment/Component"
MACHINE_FUNCTION_VERBS = {
    # Transmission/Control (clear machine functions)
    "transmit", "control", "regulate", "direct", "guide",
    "modulate", "coordinate", "synchronize",
    # Conversion/Transformation (clear machine functions)
    "convert", "compress", "expand", "generate", "produce", "pump",
    "circulate", "flow", "distribute", "supply", "transfer",
    "cool", "heat", "warm", "dissipate",
    # Protection/Isolation (clear machine functions)
    "protect", "relieve", "vent", "seal", "dampen", "isolate",
    "filter", "separate", "prevent", "block", "absorb",
    # Movement/Positioning (clear machine functions)
    "rotate", "move", "position", "hold", "support", "suspend",
    "bear", "lift", "lower", "raise",
    # Sensing (clear machine functions)
    "measure", "sense", "detect", "indicate",
    # Lubrication (clear machine functions)
    "lubricate", "coat",
}

# Verbs that indicate administrative/non-machine functions (reject)
# NOTE: This is an ORIENTATIVE list, not exhaustive. Default is to REJECT verbs not in MACHINE_FUNCTION_VERBS
ADMINISTRATIVE_VERBS = {
    # Operational/Procedural (inspection, maintenance planning - NOT machine functions)
    "inspect", "check", "verify", "analyze", "examine", "assess",
    "test", "validate", "audit", "review", "diagnose",
    # Maintenance planning/scheduling/performing (administrative activities)
    "schedule", "plan", "arrange", "prepare", "organize", "perform", "execute",
    "conduct", "carry", "implement", "complete",
    # Administrative/Business  
    "manage", "track", "log", "record", "report",
    "sell", "buy", "trade", "market", "advertise",
    "communicate", "notify", "alert", "announce", "inform", "document",
    "approve", "authorize", "sign", "certify", "confirm",
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
            
            # Strategy: CONSERVATIVE by default
            # 1. REJECT if administrative verb
            # 2. ACCEPT if machine verb
            # 3. REJECT for Type="Other" if unknown
            # 4. ALLOW for Type="Equipment/Component" if unknown (since list is orientative)
            
            # Step 1: Check if it's an administrative verb (these are ALWAYS rejected)
            if main_verb in ADMINISTRATIVE_VERBS:
                reason = f"Administrative/procedural verb '{main_verb}' (not machine): '{entity_function}'"
                if debug:
                    logger.info(f"[REJECTED] {entity_name} - {reason}")
                return False, reason
            
            # Step 2: Check if it's a known machine verb (these are ACCEPTED)
            if main_verb in MACHINE_FUNCTION_VERBS:
                reason = f"Valid machine function: '{entity_function}'"
                if debug:
                    logger.debug(f"Machine function accepted for '{entity_name}': {entity_function}")
                return True, reason
            
            # Step 3: Unknown verb - apply TYPE-specific logic
            # Type "Other" is CONSERVATIVE - unknown verb = likely procedural/administrative
            if normalized_type == "other":
                reason = f"Type 'Other' with unknown verb '{main_verb}' - likely procedural/administrative: '{entity_function}'"
                if debug:
                    logger.info(f"[REJECTED] {entity_name} - {reason}")
                return False, reason
            
            # Type "Equipment/Component" - allow unknown verbs since MACHINE_FUNCTION_VERBS is ORIENTATIVE
            elif normalized_type in ["equipment", "component", "system", "device"]:
                # Validate it's a real word (not gibberish)
                if len(main_verb) >= 3 and main_verb.isalpha():
                    # Real word but uncommon - allow with warning (since list is orientative)
                    reason = f"Accepted with unknown verb '{main_verb}' (type: {entity_type})"
                    if debug:
                        logger.debug(f"Unknown verb '{main_verb}' for {entity_type} '{entity_name}': {entity_function}")
                    return True, reason
                else:
                    # Gibberish or too short
                    reason = f"Invalid/gibberish function verb '{main_verb}': '{entity_function}'"
                    if debug:
                        logger.info(f"[REJECTED] {entity_name} - {reason}")
                    return False, reason
            
            # Any other type without recognized verb - unknown, be conservative
            else:
                reason = f"Type '{entity_type}' with unknown verb '{main_verb}': '{entity_function}'"
                if debug:
                    logger.debug(f"Unknown verb for entity type '{entity_type}': {entity_function}")
                return False, reason
    
    # Check 7: If no function or function is "unknown", validate based on type
    if not normalized_func or normalized_func == "unknown":
        if is_brand_type:
            reason = f"Valid manufacturer/brand (no function): '{entity_name}'"
            if debug:
                logger.info(f"[ACCEPTED] {entity_name} - {reason}")
            return True, reason
        
        # Type "Other" without proper function should be rejected
        if normalized_type == "other":
            reason = f"Type 'Other' with no function - likely not equipment: '{entity_name}'"
            if debug:
                logger.info(f"[REJECTED] {entity_name} - {reason}")
            return False, reason
        
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
    Deduplicate entities using simple normalization strategies:
    1. Singular/Plural normalization (e.g., "Bearings" → "bearing")
    2. Case normalization (e.g., "Oil Pump" → "oil pump")
    3. Punctuation normalization (e.g., "Dry-Gas-Seal" → "Dry Gas Seal")
    4. Whitespace normalization (e.g., "Gas  Turbine" → "Gas Turbine")
    5. Suffix merging (e.g., "X System" + "X" → one entity)
    6. Translation handling (e.g., "Gás Turbina" → "Gas Turbine")
    
    NOTE: Does NOT handle complex cases like acronym matching (e.g., "IGV" vs "Inlet Guide Vane").
    Those are kept as separate entities intentionally for simplicity.
    
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
        
        # Apply normalization strategies (simple, no acronyms)
        normalized = _normalize_entity_name(original_name)
        
        if normalized not in dedup_map:
            # New entity
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
    
    # Strategy 5: Normalize plural/singular for EACH WORD
    # This handles cases like "Bearings Covers" → "bearing cover"
    words = normalized.split()
    normalized_words = [_normalize_singular_plural(word) for word in words]
    normalized = " ".join(normalized_words)
    
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
    
    # Handle common plural endings (check specifics BEFORE generals)
    # Order matters: check longer patterns first to avoid over-stripping
    if name_lower.endswith("sses"):  # glasses -> glass
        return name[:-2] if len(name) > 2 else name
    elif name_lower.endswith("ies"):  # batteries -> battery
        return name[:-3] + "y" if len(name) > 3 else name
    elif name_lower.endswith("ches"):  # matches -> match
        return name[:-2] if len(name) > 2 else name
    elif name_lower.endswith("shes"):  # brushes -> brush
        return name[:-2] if len(name) > 2 else name
    elif name_lower.endswith("xes"):  # boxes -> box
        return name[:-2] if len(name) > 2 else name
    elif name_lower.endswith("zes"):  # buzzes -> buzz
        return name[:-2] if len(name) > 2 else name
    elif name_lower.endswith("oes"):  # tomatoes -> tomato
        return name[:-2] if len(name) > 2 else name
    elif name_lower.endswith("us"):  # cactus -> cactus (keep as-is)
        return name
    elif name_lower.endswith("es") and not name_lower.endswith("ss"):  # caves -> cave, dishes -> dish
        return name[:-2] if len(name) > 2 else name
    elif name_lower.endswith("s") and not name_lower.endswith("ss"):  # seals -> seal, bearings -> bearing
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
    """Handle Portuguese to English translations for common terms and OCR errors."""
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
    
    # Check for OCR/typo variations of known manufacturers
    # Normalize common OCR errors for "Nuovo Pignone" variants
    if "pignone" in name_lower or "pignona" in name_lower or "pignano" in name_lower:
        # All these variants should normalize to "nuovo pignone"
        if "tecnologie" in name_lower:
            return "nuovo pignone tecnologie s.r.l."
    
    for pt_term, en_term in translations.items():
        if name_lower == pt_term:
            return en_term
    
    return name

