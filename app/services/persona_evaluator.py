# services/persona_evaluator.py
"""
Persona evaluation service for measuring diversity and quality metrics.

Metric 3: Persona Diversity - Uses embedding cosine distance to measure semantic similarity
between personas. Higher diversity = lower similarity = better coverage of market segments.
"""
from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging
import json

logger = logging.getLogger(__name__)


class PersonaEvaluator:
    """
    Evaluates persona quality and diversity using multiple metrics.
    
    Key Metrics:
    1. Diversity (Semantic): Cosine distance between persona embeddings
    2. Industry Diversity: Unique industries count and distribution
    3. Geographic Diversity: Unique locations count
    4. Size Diversity: Coverage of company size ranges
    5. Tier Distribution: Balance across tier_1, tier_2, tier_3
    """
    
    def __init__(self, embedding_service=None):
        """
        Initialize evaluator with optional embedding service.
        
        Args:
            embedding_service: Service for generating embeddings (default: OpenAIEmbeddingService)
        """
        self.embedding_service = embedding_service or OpenAIEmbeddingService()
    
    def evaluate_personas(self, personas: List[Dict]) -> Dict:
        """
        Comprehensive evaluation of persona set.
        
        Args:
            personas: List of persona dictionaries
            
        Returns:
            Dictionary with evaluation metrics
        """
        if not personas or len(personas) < 2:
            return {
                "error": "Need at least 2 personas for evaluation",
                "persona_count": len(personas) if personas else 0
            }
        
        logger.info(f"Evaluating {len(personas)} personas")
        
        # Metric 1: Semantic Diversity (using embeddings)
        diversity_metrics = self._calculate_semantic_diversity(personas)
        
        # Metric 2: Industry Diversity
        industry_metrics = self._calculate_industry_diversity(personas)
        
        # Metric 3: Geographic Diversity
        geographic_metrics = self._calculate_geographic_diversity(personas)
        
        # Metric 4: Size Diversity
        size_metrics = self._calculate_size_diversity(personas)
        
        # Metric 5: Tier Distribution
        tier_metrics = self._calculate_tier_distribution(personas)
        
        # Metric 6: Field Completeness
        completeness_metrics = self._calculate_completeness(personas)
        
        # Overall score (weighted combination)
        overall_score = self._calculate_overall_score(
            diversity_metrics,
            industry_metrics,
            geographic_metrics,
            size_metrics,
            tier_metrics,
            completeness_metrics
        )
        
        return {
            "persona_count": len(personas),
            "overall_score": overall_score,
            "semantic_diversity": diversity_metrics,
            "industry_diversity": industry_metrics,
            "geographic_diversity": geographic_metrics,
            "size_diversity": size_metrics,
            "tier_distribution": tier_metrics,
            "completeness": completeness_metrics,
            "recommendations": self._generate_recommendations(
                diversity_metrics,
                industry_metrics,
                geographic_metrics,
                size_metrics,
                tier_metrics
            )
        }
    
    def _calculate_semantic_diversity(self, personas: List[Dict]) -> Dict:
        """
        Calculate semantic diversity using embedding cosine distance.
        
        This is the core Metric 3: Persona Diversity.
        
        Steps:
        1. Create text representation for each persona
        2. Generate embeddings
        3. Calculate pairwise cosine similarities
        4. Compute diversity metrics (average distance, min distance, etc.)
        
        Returns:
            Dictionary with diversity metrics
        """
        try:
            # Step 1: Create text representations
            persona_texts = [self._persona_to_text(p) for p in personas]
            
            # Step 2: Generate embeddings
            logger.info("Generating embeddings for personas...")
            embeddings = self.embedding_service.embed_batch(persona_texts)
            
            if embeddings is None or len(embeddings) != len(personas):
                logger.error("Failed to generate embeddings")
                return {
                    "error": "Failed to generate embeddings",
                    "average_cosine_similarity": None,
                    "average_cosine_distance": None,
                    "min_cosine_distance": None,
                    "max_cosine_similarity": None
                }
            
            # Step 3: Calculate pairwise cosine similarities
            similarity_matrix = cosine_similarity(embeddings)
            
            # Extract upper triangle (excluding diagonal)
            n = len(personas)
            similarities = []
            distances = []
            
            for i in range(n):
                for j in range(i + 1, n):
                    sim = similarity_matrix[i][j]
                    similarities.append(sim)
                    distances.append(1 - sim)  # Cosine distance = 1 - cosine similarity
            
            # Step 4: Compute metrics
            avg_similarity = np.mean(similarities)
            avg_distance = np.mean(distances)
            min_distance = np.min(distances)
            max_similarity = np.max(similarities)
            
            # Standard deviation (higher = more diverse)
            std_distance = np.std(distances)
            
            # Diversity score (0-1, higher = more diverse)
            # Normalize: distance ranges from 0-2, so divide by 2
            diversity_score = avg_distance / 2.0
            
            logger.info(
                f"Semantic diversity: avg_distance={avg_distance:.3f}, "
                f"min_distance={min_distance:.3f}, diversity_score={diversity_score:.3f}"
            )
            
            return {
                "average_cosine_similarity": float(avg_similarity),
                "average_cosine_distance": float(avg_distance),
                "min_cosine_distance": float(min_distance),
                "max_cosine_similarity": float(max_similarity),
                "std_cosine_distance": float(std_distance),
                "diversity_score": float(diversity_score),  # 0-1, higher = more diverse
                "pairwise_distances": [float(d) for d in distances],
                "interpretation": self._interpret_diversity_score(diversity_score, avg_distance)
            }
            
        except Exception as e:
            logger.error(f"Error calculating semantic diversity: {e}", exc_info=True)
            return {
                "error": str(e),
                "average_cosine_similarity": None,
                "average_cosine_distance": None
            }
    
    def _persona_to_text(self, persona: Dict) -> str:
        """
        Convert persona dictionary to text representation for embedding.
        
        Combines key fields that represent persona uniqueness:
        - persona_name
        - industry
        - location
        - company_size_range
        - company_type
        - description (full)
        - job_titles (first 5 for brevity)
        """
        parts = []
        
        # Core identity
        parts.append(f"Persona: {persona.get('persona_name', '')}")
        
        # Industry and location
        parts.append(f"Industry: {persona.get('industry', '')}")
        parts.append(f"Location: {persona.get('location', '')}")
        
        # Company characteristics
        parts.append(f"Company Size: {persona.get('company_size_range', '')}")
        parts.append(f"Company Type: {persona.get('company_type', '')}")
        
        # Decision makers (sample)
        job_titles = persona.get('job_titles', [])
        if job_titles:
            sample = job_titles[:5]  # First 5 for context
            parts.append(f"Target Roles: {', '.join(sample)}")
        
        # Full description (most important for semantic meaning)
        parts.append(f"Description: {persona.get('description', '')}")
        
        return "\n".join(parts)
    
    def _calculate_industry_diversity(self, personas: List[Dict]) -> Dict:
        """Calculate industry diversity metrics."""
        industries = [p.get('industry', 'Unknown') for p in personas]
        unique_industries = len(set(industries))
        total = len(personas)
        
        # Distribution
        industry_counts = {}
        for ind in industries:
            industry_counts[ind] = industry_counts.get(ind, 0) + 1
        
        # Diversity score: unique_industries / total (normalized)
        diversity_score = unique_industries / total if total > 0 else 0
        
        return {
            "unique_industries": unique_industries,
            "total_personas": total,
            "industry_diversity_score": diversity_score,
            "industry_distribution": industry_counts,
            "recommendation": "Aim for unique industries per persona" if unique_industries < total else "Good industry diversity"
        }
    
    def _calculate_geographic_diversity(self, personas: List[Dict]) -> Dict:
        """Calculate geographic diversity metrics."""
        locations = [p.get('location', 'Unknown') for p in personas]
        unique_locations = len(set(locations))
        total = len(personas)
        
        location_counts = {}
        for loc in locations:
            location_counts[loc] = location_counts.get(loc, 0) + 1
        
        diversity_score = unique_locations / total if total > 0 else 0
        
        return {
            "unique_locations": unique_locations,
            "total_personas": total,
            "geographic_diversity_score": diversity_score,
            "location_distribution": location_counts
        }
    
    def _calculate_size_diversity(self, personas: List[Dict]) -> Dict:
        """Calculate company size diversity metrics."""
        sizes = [p.get('company_size_range', 'Unknown') for p in personas]
        unique_sizes = len(set(sizes))
        total = len(personas)
        
        size_counts = {}
        for size in sizes:
            size_counts[size] = size_counts.get(size, 0) + 1
        
        diversity_score = unique_sizes / total if total > 0 else 0
        
        return {
            "unique_size_ranges": unique_sizes,
            "total_personas": total,
            "size_diversity_score": diversity_score,
            "size_distribution": size_counts
        }
    
    def _calculate_tier_distribution(self, personas: List[Dict]) -> Dict:
        """Calculate tier distribution metrics."""
        tiers = [p.get('tier', 'unknown') for p in personas]
        total = len(personas)
        
        tier_counts = {}
        for tier in tiers:
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        # Calculate percentages
        tier_percentages = {
            tier: (count / total * 100) if total > 0 else 0
            for tier, count in tier_counts.items()
        }
        
        # Check if distribution is balanced
        # Ideal: tier_1 (30-40%), tier_2 (40-50%), tier_3 (10-20%)
        tier_1_pct = tier_percentages.get('tier_1', 0)
        tier_2_pct = tier_percentages.get('tier_2', 0)
        tier_3_pct = tier_percentages.get('tier_3', 0)
        
        is_balanced = (
            30 <= tier_1_pct <= 40 and
            40 <= tier_2_pct <= 50 and
            10 <= tier_3_pct <= 20
        )
        
        return {
            "tier_distribution": tier_counts,
            "tier_percentages": tier_percentages,
            "is_balanced": is_balanced,
            "recommendation": "Distribution is balanced" if is_balanced else "Consider rebalancing tiers"
        }
    
    def _calculate_completeness(self, personas: List[Dict]) -> Dict:
        """Calculate field completeness metrics."""
        required_fields = [
            'persona_name', 'tier', 'job_titles', 'excluded_job_titles',
            'industry', 'company_size_range', 'company_type',
            'location', 'description'
        ]
        
        completeness_scores = []
        for persona in personas:
            present_fields = sum(1 for field in required_fields if persona.get(field))
            score = present_fields / len(required_fields)
            completeness_scores.append(score)
        
        avg_completeness = np.mean(completeness_scores) if completeness_scores else 0
        
        return {
            "average_completeness": float(avg_completeness),
            "completeness_scores": [float(s) for s in completeness_scores],
            "all_complete": all(s == 1.0 for s in completeness_scores)
        }
    
    def _calculate_overall_score(self, *metric_dicts) -> float:
        """
        Calculate weighted overall score.
        
        Weights:
        - Semantic diversity: 40% (most important)
        - Industry diversity: 20%
        - Geographic diversity: 15%
        - Size diversity: 10%
        - Tier distribution: 10%
        - Completeness: 5%
        """
        semantic = metric_dicts[0].get('diversity_score', 0)
        industry = metric_dicts[1].get('industry_diversity_score', 0)
        geographic = metric_dicts[2].get('geographic_diversity_score', 0)
        size = metric_dicts[3].get('size_diversity_score', 0)
        tier = 1.0 if metric_dicts[4].get('is_balanced', False) else 0.5
        completeness = metric_dicts[5].get('average_completeness', 0)
        
        overall = (
            semantic * 0.40 +
            industry * 0.20 +
            geographic * 0.15 +
            size * 0.10 +
            tier * 0.10 +
            completeness * 0.05
        )
        
        return float(overall)
    
    def _interpret_diversity_score(self, diversity_score: float, avg_distance: float) -> str:
        """Interpret diversity score for users."""
        if diversity_score >= 0.7:
            return "Excellent diversity - personas cover distinct market segments"
        elif diversity_score >= 0.5:
            return "Good diversity - personas have meaningful differences"
        elif diversity_score >= 0.3:
            return "Moderate diversity - some personas may be too similar"
        else:
            return "Low diversity - personas are too similar, consider generating more distinct segments"
    
    def _generate_recommendations(self, *metric_dicts) -> List[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []
        
        semantic = metric_dicts[0]
        industry = metric_dicts[1]
        geographic = metric_dicts[2]
        size = metric_dicts[3]
        tier = metric_dicts[4]
        
        # Semantic diversity
        if semantic.get('diversity_score', 0) < 0.5:
            recommendations.append(
                "Low semantic diversity: Generate personas with more distinct characteristics "
                "(different industries, geographies, or company sizes)"
            )
        
        # Industry diversity
        if industry.get('industry_diversity_score', 0) < 0.8:
            recommendations.append(
                f"Only {industry.get('unique_industries')} unique industries for "
                f"{industry.get('total_personas')} personas. Consider diversifying industries."
            )
        
        # Geographic diversity
        if geographic.get('geographic_diversity_score', 0) < 0.6:
            recommendations.append(
                f"Limited geographic diversity: {geographic.get('unique_locations')} unique locations. "
                "Consider adding personas from different regions."
            )
        
        # Tier distribution
        if not tier.get('is_balanced', False):
            recommendations.append(
                "Tier distribution is not balanced. Aim for: tier_1 (30-40%), "
                "tier_2 (40-50%), tier_3 (10-20%)"
            )
        
        if not recommendations:
            recommendations.append("All metrics look good! Personas are well-diversified.")
        
        return recommendations


class OpenAIEmbeddingService:
    """
    Service for generating embeddings using OpenAI API.
    """
    
    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize embedding service.
        
        Args:
            model: OpenAI embedding model name
                - text-embedding-3-small (cheaper, 1536 dims)
                - text-embedding-3-large (more accurate, 3072 dims)
                - text-embedding-ada-002 (legacy, 1536 dims)
        """
        self.model = model
        self.dimension = 1536 if "small" in model else (3072 if "large" in model else 1536)
    
    def embed_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            numpy array of shape (n_texts, embedding_dim) or None if error
        """
        try:
            from openai import OpenAI
            import os
            from dotenv import load_dotenv
            
            # Load .env file if exists
            load_dotenv()
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("OPENAI_API_KEY not found in environment")
                return None
            
            client = OpenAI(api_key=api_key)
            
            logger.info(f"Generating embeddings for {len(texts)} texts using {self.model}")
            
            # Call OpenAI API
            response = client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            # Extract embeddings
            embeddings = [item.embedding for item in response.data]
            
            # Convert to numpy array
            return np.array(embeddings)
            
        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            return None
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}", exc_info=True)
            return None


# Singleton instance
_persona_evaluator = None


def get_persona_evaluator() -> PersonaEvaluator:
    """Get or create PersonaEvaluator singleton."""
    global _persona_evaluator
    if _persona_evaluator is None:
        _persona_evaluator = PersonaEvaluator()
    return _persona_evaluator

