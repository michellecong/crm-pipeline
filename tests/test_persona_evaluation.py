#!/usr/bin/env python3
"""
Test script for persona evaluation using embedding cosine distance.

This demonstrates Metric 3: Persona Diversity evaluation.
"""
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.persona_evaluator import get_persona_evaluator


def load_personas_from_file(filepath: str) -> list:
    """Load personas from generated JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get("result", {}).get("personas", [])


def print_evaluation_results(evaluation: dict):
    """Pretty print evaluation results."""
    print("\n" + "=" * 80)
    print("PERSONA EVALUATION RESULTS")
    print("=" * 80)
    
    print(f"\n📊 Overall Score: {evaluation['overall_score']:.3f} / 1.0")
    
    # Semantic Diversity (Metric 3)
    print("\n" + "-" * 80)
    print("🎯 METRIC 3: SEMANTIC DIVERSITY (Embedding Cosine Distance)")
    print("-" * 80)
    semantic = evaluation['semantic_diversity']
    if 'error' in semantic:
        print(f"❌ Error: {semantic['error']}")
    else:
        print(f"  Average Cosine Distance: {semantic.get('average_cosine_distance', 0):.3f}")
        print(f"  Min Cosine Distance:     {semantic.get('min_cosine_distance', 0):.3f}")
        print(f"  Diversity Score:        {semantic.get('diversity_score', 0):.3f} / 1.0")
        print(f"  Interpretation:         {semantic.get('interpretation', 'N/A')}")
    
    # Industry Diversity
    print("\n" + "-" * 80)
    print("🏭 INDUSTRY DIVERSITY")
    print("-" * 80)
    industry = evaluation['industry_diversity']
    print(f"  Unique Industries:        {industry['unique_industries']} / {industry['total_personas']}")
    print(f"  Diversity Score:          {industry['industry_diversity_score']:.3f} / 1.0")
    print(f"  Distribution:            {industry['industry_distribution']}")
    
    # Geographic Diversity
    print("\n" + "-" * 80)
    print("🌍 GEOGRAPHIC DIVERSITY")
    print("-" * 80)
    geo = evaluation['geographic_diversity']
    print(f"  Unique Locations:         {geo['unique_locations']} / {geo['total_personas']}")
    print(f"  Diversity Score:          {geo['geographic_diversity_score']:.3f} / 1.0")
    print(f"  Distribution:            {geo['location_distribution']}")
    
    # Size Diversity
    print("\n" + "-" * 80)
    print("📏 SIZE DIVERSITY")
    print("-" * 80)
    size = evaluation['size_diversity']
    print(f"  Unique Size Ranges:       {size['unique_size_ranges']} / {size['total_personas']}")
    print(f"  Diversity Score:          {size['size_diversity_score']:.3f} / 1.0")
    
    # Tier Distribution
    print("\n" + "-" * 80)
    print("🎚️  TIER DISTRIBUTION")
    print("-" * 80)
    tier = evaluation['tier_distribution']
    print(f"  Distribution:            {tier['tier_distribution']}")
    print(f"  Percentages:             {tier['tier_percentages']}")
    print(f"  Is Balanced:             {tier['is_balanced']}")
    
    # Recommendations
    print("\n" + "-" * 80)
    print("💡 RECOMMENDATIONS")
    print("-" * 80)
    for i, rec in enumerate(evaluation['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    print("\n" + "=" * 80 + "\n")


def main():
    """Main test function."""
    # Load personas from generated file
    persona_file = project_root / "data" / "generated" / "hubspot_personas_2025-11-02T20-36-02.json"
    
    if not persona_file.exists():
        print(f"❌ Persona file not found: {persona_file}")
        print("   Please generate personas first using the pipeline API.")
        return 1
    
    print(f"📂 Loading personas from: {persona_file.name}")
    personas = load_personas_from_file(str(persona_file))
    
    if not personas:
        print("❌ No personas found in file")
        return 1
    
    print(f"✅ Loaded {len(personas)} personas")
    
    # Initialize evaluator
    evaluator = get_persona_evaluator()
    
    # Evaluate personas
    print("\n🔍 Evaluating personas...")
    print("   This will generate embeddings and calculate cosine distances...")
    
    evaluation = evaluator.evaluate_personas(personas)
    
    # Print results
    print_evaluation_results(evaluation)
    
    # Save results
    output_file = project_root / "data" / "generated" / "hubspot_personas_evaluation.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Evaluation results saved to: {output_file.name}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

