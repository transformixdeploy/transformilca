from flask import Flask, request, jsonify
from typing import Any, Dict
import asyncio

# Reuse existing project services
from seo_analyzer import SEOAnalyzer
from gpt_insights_service import GPTInsightsService
from helpers import is_valid_url, validate_url
from sentiment_analyzer import SentimentAnalyzer


app = Flask(__name__)


def map_seo_to_response(seo_result: Dict[str, Any], gpt_insights: Dict[str, Any]) -> Dict[str, Any]:
    """Map internal SEO analysis result to the required API response schema."""

    # Basic numbers
    page_speed_score = seo_result.get("page_speed_score") or seo_result.get("page_speed_scores", {}).get("overall", 0) or 0
    internal_links = seo_result.get("internal_links", 0) or 0
    external_links = seo_result.get("external_links", 0) or 0

    # Content info
    images_count = seo_result.get("images_count", 0) or 0
    images_missing_alt = seo_result.get("alt_tags_missing", 0) or 0

    # Page info
    title = seo_result.get("title") or ""
    title_length = seo_result.get("title_length", len(title) if title else 0) or 0
    meta_description = seo_result.get("meta_description") or ""
    meta_description_length = seo_result.get("meta_description_length", len(meta_description) if meta_description else 0) or 0
    https_enabled = bool(seo_result.get("https", False))
    canonical_url = seo_result.get("canonical_url") or ""

    # Headings mapping
    headings = seo_result.get("headings", {}) or {}
    def get_heading_list(tag: str):
        values = headings.get(tag, []) or []
        # Ensure list of strings
        return [str(v) for v in values]

    # Schema & social
    schema_markup = seo_result.get("schema_markup", []) or []
    social_links = seo_result.get("social_links", []) or []

    # Open Graph tags mapping
    og_tags = seo_result.get("og_tags", {}) or {}
    open_graph_tags = {
        "title": og_tags.get("og:title") or "",
        "description": og_tags.get("og:description") or "",
        "url": og_tags.get("og:url") or "",
        "type": og_tags.get("og:type") or "",
        "siteName": og_tags.get("og:site_name") or "",
    }

    # AI insights
    insights = (gpt_insights or {}).get("insights", {})
    summary = insights.get("summary", "")
    full_social_analysis = insights.get("full_analysis", "")

    return {
        "pageSpeedScore": page_speed_score,
        "internalLinks": internal_links,
        "externalLinks": external_links,
        "contentInfo": {
            "imagesCount": images_count,
            "imagesMissingAltTage": images_missing_alt,
        },
        "pageInfo": {
            "title": title,
            "titleLength": title_length,
            "metaDescription": meta_description,
            "metaDescriptionLength": meta_description_length,
            "https": https_enabled,
            "canonicalUrl": canonical_url,
        },
        "headingStructure": {
            "h1Tages": get_heading_list("h1"),
            "h2Tages": get_heading_list("h2"),
            "h3Tages": get_heading_list("h3"),
            "h4Tages": get_heading_list("h4"),
            "h5Tages": get_heading_list("h5"),
            "h6Tages": get_heading_list("h6"),
        },
        "schemaMarkup": schema_markup,
        "socialLinks": social_links,
        "openGraphTags": open_graph_tags,
        "summary": summary,
        "fullSocialAnalysis": full_social_analysis,
    }


@app.post("/ai/website-swot-analysis")
def website_swot_analysis():
    try:
        body = request.get_json(force=True, silent=True) or {}

        website_url = (body.get("website_url") or "").strip()
        if not website_url:
            return jsonify({"error": "website_url is required"}), 400

        # Normalize and validate URL
        website_url = validate_url(website_url)
        if not is_valid_url(website_url):
            return jsonify({"error": "Invalid website_url. Must include http(s) scheme and domain."}), 400

        # Run existing async analysis services
        analyzer = SEOAnalyzer()
        gpt_service = GPTInsightsService()

        async def run_analysis(url: str) -> Dict[str, Any]:
            seo_result = await analyzer.analyze_website(url)
            gpt_result = await gpt_service.generate_seo_insights(seo_result)
            return map_seo_to_response(seo_result, gpt_result)

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            response_payload = loop.run_until_complete(run_analysis(website_url))
        finally:
            loop.close()
        return jsonify(response_payload), 200
    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500
@app.post("/ai/customer-sentiment-analysis")
def customer_sentiment_analysis():
    try:
        body = request.get_json(force=True, silent=True) or {}

        industry = (body.get("industry_field") or "").strip()
        country = (body.get("country") or "").strip()

        if not industry or not country:
            return jsonify({"error": "industry_field and country are required"}), 400

        # Fixed parameters per requirement
        MAX_COMPETITORS = 5
        REVIEWS_PER_COMPETITOR = 100

        analyzer = SentimentAnalyzer()

        # Run full competitor sentiment analysis
        async def run_competitor_analysis() -> Dict[str, Any]:
            return await analyzer.analyze_competitors_sentiment(
                industry=industry,
                region=country,
                max_competitors=MAX_COMPETITORS,
                reviews_per_competitor=REVIEWS_PER_COMPETITOR,
            )

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            analysis_results = loop.run_until_complete(run_competitor_analysis())
        finally:
            loop.close()

        # Map to required response schema
        competitor_results = analysis_results.get("competitor_results", [])
        combined = analysis_results.get("combined_analysis", {})
        combined_summary = combined.get("combined_summary", {})

        # competitorsAnalyized list
        competitors_analyzed_list = []
        for result in competitor_results:
            comp = result.get("competitor_info", {})
            summary = result.get("sentiment_summary", {})
            pct = summary.get("sentiment_percentages", {})
            competitors_analyzed_list.append({
                "name": comp.get("name", ""),
                "googleRating": comp.get("rating", 0) or 0,
                "reviewsAnalyzed": result.get("total_reviews_analyzed", 0) or 0,
                "positivePercentage": pct.get("Positive", 0) or 0,
                "negativePercentage": pct.get("Negative", 0) or 0,
                "avgSentiment": summary.get("average_polarity", 0) or 0,
            })

        # competitorsDetails
        competitors_details = []
        for result in competitor_results:
            comp = result.get("competitor_info", {})
            ai_insights = result.get("ai_insights", {})
            ai_summary = (ai_insights.get("insights", {}) or {}).get("summary") or ai_insights.get("summary", "") or ""
            competitors_details.append({
                "address": comp.get("address", "") or "",
                "googleMaps": comp.get("google_maps_url", "") or "",
                "aiInsights": ai_summary,
            })

        # competitorSentimentComparisonChart
        sentiment_chart = []
        for result in competitor_results:
            comp = result.get("competitor_info", {})
            summary = result.get("sentiment_summary", {})
            pct = summary.get("sentiment_percentages", {})
            sentiment_chart.append({
                "name": comp.get("name", ""),
                "negative": pct.get("Negative", 0) or 0,
                "positive": pct.get("Positive", 0) or 0,
                "neutral": pct.get("Neutral", 0) or 0,
            })

        # competitorRating_averageSentiment_chart
        rating_vs_sentiment = []
        for result in competitor_results:
            comp = result.get("competitor_info", {})
            summary = result.get("sentiment_summary", {})
            rating_vs_sentiment.append({
                "googleRating": comp.get("rating", 0) or 0,
                "averageSentiment": summary.get("average_polarity", 0) or 0,
                "competitorName": comp.get("name", ""),
            })

        # Pie chart for combined summary
        pie = {
            "title": f"{industry.title()} sentiment distribution in {country}",
            "positive": combined_summary.get("sentiment_percentages", {}).get("Positive", 0) or 0,
            "negative": combined_summary.get("sentiment_percentages", {}).get("Negative", 0) or 0,
            "neutral": combined_summary.get("sentiment_percentages", {}).get("Neutral", 0) or 0,
        }

        # Reviews analyzed per competitor
        reviews_per_comp_list = []
        for result in competitor_results:
            comp = result.get("competitor_info", {})
            reviews_per_comp_list.append({
                "name": comp.get("name", ""),
                "reviews": result.get("total_reviews_analyzed", 0) or 0,
            })

        payload = {
            "analysisTitle": f"{industry.title()} Industry Analysis - {country}",
            "competitorsAnalyzedNumber": combined.get("total_competitors_analyzed", len(competitor_results)) or 0,
            "totalReview": combined.get("total_reviews_analyzed", 0) or 0,
            "avgGoogleRating": round(sum([(r.get("competitor_info", {}).get("rating", 0) or 0) for r in competitor_results]) / max(len(competitor_results), 1), 2) if competitor_results else 0,
            "competitorsAnalyized": competitors_analyzed_list,
            "competitorsDetails": competitors_details,
            "competitorSentimentComparisonChart": sentiment_chart,
            "competitorRating_averageSentiment_chart": rating_vs_sentiment,
            "pieChart": pie,
            "reviewsAnalyzedPerCompetitor": reviews_per_comp_list,
        }

        return jsonify(payload), 200

    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500


if __name__ == "__main__":
    # Simple dev server run: python flask_api.py
    app.run(host="0.0.0.0", port=8000, debug=True)


