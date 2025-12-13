"""
WHO (World Health Organization) API Integration
Zugriff auf verifizierte Gesundheitsinformationen

APIs:
1. GHO (Global Health Observatory) - Gesundheitsstatistiken
2. Disease Outbreak News - Aktuelle Ausbrüche
3. Fact Sheets - Verifizierte Gesundheitsfakten

Alle APIs sind KOSTENLOS und brauchen keinen API-Key!
"""

import asyncio
import logging
import os
import certifi
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx

# Check if SSL verification should be disabled (for dev environments with proxies)
DISABLE_SSL = os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true"
SSL_VERIFY = False if DISABLE_SSL else certifi.where()

logger = logging.getLogger(__name__)


class WHOAPI:
    """WHO API Client für Gesundheitsinformationen"""

    def __init__(self):
        # GHO OData API
        self.gho_base_url = "https://ghoapi.azureedge.net/api"
        # WHO News API
        self.news_base_url = "https://www.who.int/api"
        self.timeout = 15.0

    async def search_health_topics(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Suche nach WHO Gesundheitsthemen und Fakten
        Kombiniert GHO Indikatoren und Fact Sheets
        """
        results = []

        # Parallel: GHO Indicators + Disease News
        gho_task = self._search_gho_indicators(query, max_results)
        news_task = self._search_who_news(query, max_results)

        gho_results, news_results = await asyncio.gather(
            gho_task, news_task, return_exceptions=True
        )

        if isinstance(gho_results, list):
            results.extend(gho_results)
        if isinstance(news_results, list):
            results.extend(news_results)

        # Add fact sheet links for common health topics
        fact_sheets = self._get_relevant_fact_sheets(query)
        results.extend(fact_sheets)

        logger.info(f"🏥 WHO: Found {len(results)} results for '{query[:50]}...'")
        return results[:max_results]

    async def _search_gho_indicators(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Suche in GHO (Global Health Observatory) Indikatoren"""
        results = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=SSL_VERIFY) as client:
                # Search indicators
                response = await client.get(
                    f"{self.gho_base_url}/Indicator",
                    params={"$filter": f"contains(IndicatorName,'{query}')"}
                )

                if response.status_code == 200:
                    data = response.json()
                    indicators = data.get("value", [])[:max_results]

                    for ind in indicators:
                        indicator_code = ind.get("IndicatorCode", "")
                        indicator_name = ind.get("IndicatorName", "")

                        results.append({
                            "source": "WHO GHO",
                            "title": indicator_name,
                            "snippet": f"WHO Global Health Observatory indicator: {indicator_name}",
                            "url": f"https://www.who.int/data/gho/data/indicators/indicator-details/GHO/{indicator_code}",
                            "credibility_score": 0.95,  # WHO = sehr hohe Glaubwürdigkeit
                            "pub_date": datetime.now().strftime("%Y-%m-%d"),
                            "type": "health_indicator"
                        })

        except Exception as e:
            logger.warning(f"WHO GHO search failed: {e}")

        return results

    async def _search_who_news(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Suche in WHO News und Disease Outbreak News"""
        results = []

        # Common health terms mapping to WHO topics
        topic_mapping = {
            "covid": "coronavirus",
            "corona": "coronavirus",
            "vaccine": "vaccines",
            "impfung": "vaccines",
            "cancer": "cancer",
            "krebs": "cancer",
            "diabetes": "diabetes",
            "heart": "cardiovascular",
            "herz": "cardiovascular",
            "mental": "mental-health",
            "depression": "mental-health",
            "obesity": "obesity",
            "übergewicht": "obesity",
            "malaria": "malaria",
            "hiv": "hiv-aids",
            "aids": "hiv-aids",
            "tuberculosis": "tuberculosis",
            "tb": "tuberculosis",
            "ebola": "ebola",
            "influenza": "influenza",
            "grippe": "influenza",
            "polio": "poliomyelitis",
            "measles": "measles",
            "masern": "measles"
        }

        query_lower = query.lower()
        matched_topic = None

        for keyword, topic in topic_mapping.items():
            if keyword in query_lower:
                matched_topic = topic
                break

        if matched_topic:
            results.append({
                "source": "WHO",
                "title": f"WHO Information: {matched_topic.replace('-', ' ').title()}",
                "snippet": f"Official WHO information and guidelines on {matched_topic.replace('-', ' ')}",
                "url": f"https://www.who.int/health-topics/{matched_topic}",
                "credibility_score": 0.98,
                "pub_date": datetime.now().strftime("%Y-%m-%d"),
                "type": "health_topic"
            })

        return results

    def _get_relevant_fact_sheets(self, query: str) -> List[Dict[str, Any]]:
        """Hole relevante WHO Fact Sheets basierend auf Query"""
        results = []

        # WHO Fact Sheet database (commonly cited)
        fact_sheets = {
            "vaccine": {
                "title": "WHO Fact Sheet: Vaccines and Immunization",
                "url": "https://www.who.int/news-room/fact-sheets/detail/vaccines-and-immunization",
                "snippet": "Immunization prevents 3.5-5 million deaths every year from diseases like diphtheria, tetanus, pertussis, influenza and measles."
            },
            "impfung": {
                "title": "WHO Fact Sheet: Impfungen und Immunisierung",
                "url": "https://www.who.int/news-room/fact-sheets/detail/vaccines-and-immunization",
                "snippet": "Impfungen verhindern jährlich 3,5-5 Millionen Todesfälle durch Krankheiten wie Diphtherie, Tetanus, Keuchhusten, Grippe und Masern."
            },
            "covid": {
                "title": "WHO: COVID-19 Dashboard & Information",
                "url": "https://covid19.who.int/",
                "snippet": "Official WHO COVID-19 data, statistics, and public health guidance."
            },
            "corona": {
                "title": "WHO: COVID-19 Dashboard & Information",
                "url": "https://covid19.who.int/",
                "snippet": "Offizielle WHO COVID-19 Daten, Statistiken und Gesundheitsrichtlinien."
            },
            "cancer": {
                "title": "WHO Fact Sheet: Cancer",
                "url": "https://www.who.int/news-room/fact-sheets/detail/cancer",
                "snippet": "Cancer is a leading cause of death worldwide, accounting for nearly 10 million deaths in 2020."
            },
            "diabetes": {
                "title": "WHO Fact Sheet: Diabetes",
                "url": "https://www.who.int/news-room/fact-sheets/detail/diabetes",
                "snippet": "The number of people with diabetes rose from 108 million in 1980 to 422 million in 2014."
            },
            "depression": {
                "title": "WHO Fact Sheet: Depression",
                "url": "https://www.who.int/news-room/fact-sheets/detail/depression",
                "snippet": "Depression is a common mental disorder affecting more than 264 million people worldwide."
            },
            "obesity": {
                "title": "WHO Fact Sheet: Obesity and Overweight",
                "url": "https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight",
                "snippet": "Worldwide obesity has nearly tripled since 1975."
            },
            "alcohol": {
                "title": "WHO Fact Sheet: Alcohol",
                "url": "https://www.who.int/news-room/fact-sheets/detail/alcohol",
                "snippet": "The harmful use of alcohol causes 3 million deaths each year globally."
            },
            "tobacco": {
                "title": "WHO Fact Sheet: Tobacco",
                "url": "https://www.who.int/news-room/fact-sheets/detail/tobacco",
                "snippet": "Tobacco kills more than 8 million people each year."
            },
            "climate": {
                "title": "WHO: Climate Change and Health",
                "url": "https://www.who.int/news-room/fact-sheets/detail/climate-change-and-health",
                "snippet": "Climate change is the single biggest health threat facing humanity."
            },
            "antimicrobial": {
                "title": "WHO Fact Sheet: Antimicrobial Resistance",
                "url": "https://www.who.int/news-room/fact-sheets/detail/antimicrobial-resistance",
                "snippet": "Antimicrobial resistance is one of the top 10 global public health threats."
            },
            "antibiotic": {
                "title": "WHO Fact Sheet: Antibiotic Resistance",
                "url": "https://www.who.int/news-room/fact-sheets/detail/antibiotic-resistance",
                "snippet": "Antibiotic resistance is rising to dangerously high levels in all parts of the world."
            }
        }

        query_lower = query.lower()

        for keyword, fact_sheet in fact_sheets.items():
            if keyword in query_lower:
                results.append({
                    "source": "WHO Fact Sheet",
                    "title": fact_sheet["title"],
                    "snippet": fact_sheet["snippet"],
                    "url": fact_sheet["url"],
                    "credibility_score": 0.98,  # WHO Fact Sheets = höchste Glaubwürdigkeit
                    "pub_date": "",
                    "type": "fact_sheet"
                })
                break  # Nur ein Fact Sheet pro Query

        return results

    async def get_health_statistics(self, indicator_code: str, country: str = "DEU") -> Optional[Dict]:
        """
        Hole spezifische Gesundheitsstatistiken für ein Land

        indicator_code: z.B. "WHOSIS_000001" (Life expectancy)
        country: ISO 3-letter code (DEU, USA, etc.)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=SSL_VERIFY) as client:
                response = await client.get(
                    f"{self.gho_base_url}/{indicator_code}",
                    params={
                        "$filter": f"SpatialDim eq '{country}'",
                        "$orderby": "TimeDim desc",
                        "$top": 1
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    values = data.get("value", [])
                    if values:
                        return {
                            "indicator": indicator_code,
                            "country": country,
                            "value": values[0].get("NumericValue"),
                            "year": values[0].get("TimeDim"),
                            "source": "WHO GHO"
                        }

        except Exception as e:
            logger.error(f"WHO statistics fetch failed: {e}")

        return None


# Convenience functions
async def search_who(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Convenience function für WHO Suche"""
    api = WHOAPI()
    return await api.search_health_topics(query, max_results)


async def get_who_stats(indicator: str, country: str = "DEU") -> Optional[Dict]:
    """Convenience function für WHO Statistiken"""
    api = WHOAPI()
    return await api.get_health_statistics(indicator, country)
