from ....models import ResearchNode, TrendingCache
from ....serializer import CapabilitySerializer, ResearchNodeCardSerializer


def get_trending_data():
    trending_combinations = {}
    trending_categories = {}

    # 1. Fetch all nodes with a trend score > 0 in a single query
    trending_nodes = list(
        ResearchNode.with_trend_score()
        .with_aggregates()
        .filter(trend_score__gt=0, status__in=["open", "in_progress", "in_review", "awaiting_coordinator"])
        .prefetch_related("required_capabilities", "keywords", "type")
    )

    cap_scores = {}
    combo_scores = {}

    # 2. Aggregate scores in memory (Extremely fast)
    for node in trending_nodes:
        # Aggregate Capability Scores
        for cap in node.required_capabilities.all():
            cap_scores[cap] = cap_scores.get(cap, 0) + node.trend_score

        # Aggregate Keyword + Type Combinations
        for kw in node.keywords.all():
            if node.type:
                combo_key = (kw, node.type)
                combo_scores[combo_key] = combo_scores.get(combo_key, 0) + node.trend_score

    # 3. Sort and slice the top 3 of each
    top_caps = sorted(cap_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    top_combos = sorted(combo_scores.items(), key=lambda x: x[1], reverse=True)[:3]

    # 4. Map the data to the format expected by the React frontend
    for cap, score in top_caps:
        # Find the top 10 nodes belonging to this capability
        cap_nodes = sorted(
            [n for n in trending_nodes if cap in n.required_capabilities.all()],
            key=lambda x: x.trend_score,
            reverse=True,
        )[:10]

        trending_categories[cap.slug] = {
            "category": CapabilitySerializer(cap).data,
            "nodes": ResearchNodeCardSerializer(cap_nodes, many=True).data,
        }

    for (kw, node_type), score in top_combos:
        # Find the top 10 nodes belonging to this keyword + type combination
        combo_nodes = sorted(
            [n for n in trending_nodes if kw in n.keywords.all() and n.type == node_type],
            key=lambda x: x.trend_score,
            reverse=True,
        )[:10]

        combo_slug = f"{kw.slug}_{node_type.name}"
        trending_combinations[combo_slug] = {
            "tag": kw.name,
            "type": node_type.name,
            "nodes": ResearchNodeCardSerializer(combo_nodes, many=True).data,
        }

    return {"trendingCombinations": trending_combinations, "trendingCategories": trending_categories}


def update_trending_cache():
    trending_data = get_trending_data()
    cache, created = TrendingCache.objects.get_or_create(pk=1)
    cache.trending_data = trending_data
    cache.save()
