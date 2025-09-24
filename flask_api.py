from flask import Flask, request, jsonify
from typing import Any, Dict

# Reuse existing project services
from seo_analyzer import SEOAnalyzer
from gpt_insights_service import GPTInsightsService
from helpers import is_valid_url, validate_url


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
async def website_swot_analysis():
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

        response_payload = await run_analysis(website_url)
        return jsonify(response_payload), 200

    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500


if __name__ == "__main__":
    # Simple dev server run: python flask_api.py
    app.run(host="0.0.0.0", port=8000, debug=True)


