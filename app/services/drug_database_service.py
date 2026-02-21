"""
Drug Database Service - Queries Bahrain approved health products from Supabase.

Used to inject official drug registration data into GPT prompts for
more accurate supplement spec extraction.
"""
import logging
from typing import List, Dict, Optional
from app.services.database_service import get_supabase_client

logger = logging.getLogger(__name__)


async def find_matching_drugs(query: str, limit: int = 5) -> List[Dict]:
    """Full-text search against bahrain_approved_drugs table.

    Args:
        query: Product name or ingredient to search for (e.g. "Omega 3", "Vitamin D3")
        limit: Maximum number of results to return

    Returns:
        List of matching drug records with trade_name, api_name, form,
        pack_size, applicant_name, manufacturer, country.
        Empty list if no matches or on error.
    """
    try:
        client = get_supabase_client()
        response = client.table("bahrain_approved_drugs").select(
            "trade_name, api_name, form, pack_size, applicant_name, manufacturer, country"
        ).limit(limit).text_search(
            "search_vector", query, options={"type": "plain", "config": "english"}
        ).execute()

        return response.data if response.data else []

    except Exception as e:
        logger.warning(f"Drug database lookup failed for '{query}': {e}")
        return []


def format_drug_context(drugs: List[Dict]) -> str:
    """Format matched drugs into a string for GPT prompt injection.

    Args:
        drugs: List of drug records from find_matching_drugs()

    Returns:
        Formatted string to append to GPT prompt, or empty string if no drugs.
    """
    if not drugs:
        return ""

    lines = [
        "\n## Official Bahrain Drug Registration Data",
        "The following registered health products may be relevant. "
        "Use this as ground truth for dosage, form, and ingredient details:"
    ]

    for drug in drugs:
        entry = f"- Trade Name: {drug.get('trade_name', 'N/A')}"
        if drug.get('api_name'):
            entry += f"\n  Ingredients: {drug['api_name']}"
        if drug.get('form'):
            entry += f"\n  Form: {drug['form']}"
        if drug.get('pack_size'):
            entry += f"\n  Pack Size: {drug['pack_size']}"
        if drug.get('applicant_name'):
            entry += f"\n  Sold at: {drug['applicant_name']}"
        if drug.get('manufacturer'):
            entry += f"\n  Manufacturer: {drug['manufacturer']}"
        if drug.get('country'):
            entry += f"\n  Country: {drug['country']}"
        lines.append(entry)

    return "\n".join(lines)
