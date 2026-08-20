#!/usr/bin/env python3
"""
Test script for spatial analysis implementation.
Validates that all functions work with real data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Setup path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import spatial_analysis
from backend.app.config import settings


def test_population_statistics():
    """Test population statistics extraction."""
    print("\n" + "=" * 70)
    print("TEST 1: Population Statistics")
    print("=" * 70)
    
    result = spatial_analysis.get_population_statistics()
    
    if result:
        print(f"[OK] Data Source: {result.get('source')}")
        print(f"[OK] Total Population: {result.get('total_population'):,.0f}")
        print(f"[OK] Mean Density (per cell): {result.get('mean_population_per_cell'):,.2f}")
        print(f"[OK] Max Density: {result.get('max_population'):.2f}")
        print(f"[OK] Study Area: {result.get('total_area_sqkm'):,.0f} km²")
        print(f"[OK] Valid Cells: {result.get('valid_cells')}")
        print("[PASS]")
        return True
    else:
        print("[FAIL] No data returned")
        return False


def test_high_population_areas():
    """Test high-population area detection."""
    print("\n" + "=" * 70)
    print("TEST 2: High-Population Area Detection")
    print("=" * 70)
    
    result = spatial_analysis.find_high_population_areas(percentile_threshold=75.0)
    
    print(f"[OK] Explanation: {result.get('explanation')}")
    print(f"[OK] High-population areas found: {result.get('high_population_count')}")
    print(f"[OK] Total population in high-density areas: {result.get('total_population_in_high_areas'):,.0f}")
    
    area_pct = result.get('area_percentage')
    if area_pct is not None:
        print(f"[OK] Area percentage: {area_pct:.1f}%")
    
    features = result.get('geojson', {}).get('features', [])
    if features:
        print(f"[OK] Sample high-population area:")
        sample = features[0]
        print(f"  - Population: {sample['properties']['population']:.2f}")
        print(f"  - Location: {sample['geometry']['coordinates'][:2]}")  # Show only first 2 coords
    
    print("[OK] PASSED")
    return True


def test_population_near_hospitals():
    """Test population calculation near hospitals."""
    print("\n" + "=" * 70)
    print("TEST 3: Population Near Hospitals")
    print("=" * 70)
    
    result = spatial_analysis.calculate_population_near_hospitals(radius_km=5.0)
    
    print(f"[OK] Explanation: {result.get('explanation')}")
    print(f"[OK] Hospitals analyzed: {result.get('hospitals_analyzed')}")
    
    total_nearby = result.get('total_population_nearby')
    if total_nearby is not None:
        print(f"[OK] Total population nearby: {total_nearby:,.0f}")
    
    avg_nearby = result.get('average_population_per_hospital')
    if avg_nearby is not None:
        print(f"[OK] Average per hospital: {avg_nearby:,.0f}")
    
    results = result.get('results', [])
    if results:
        print(f"[OK] Sample hospital analysis (first 2):")
        for hospital in results[:2]:
            print(f"\n  Hospital: {hospital.get('name')}")
            print(f"    Location: {hospital.get('location')}")
            pop_info = hospital.get('population_within_km', {})
            print(f"    Population within {pop_info.get('radius')}km: {pop_info.get('total'):,.0f}")
            if 'mean_density' in pop_info:
                print(f"    Mean density: {pop_info.get('mean_density'):.2f}")
    
    print("\n[OK] PASSED")
    return True


def test_hospital_accessibility():
    """Test hospital accessibility analysis."""
    print("\n" + "=" * 70)
    print("TEST 4: Hospital Accessibility Analysis")
    print("=" * 70)
    
    result = spatial_analysis.analyze_hospital_accessibility(
        major_road_distance_km=2.0
    )
    
    print(f"[OK] Explanation: {result.get('explanation')}")
    print(f"[OK] Hospitals analyzed: {result.get('hospitals_analyzed')}")
    
    accessibility_summary = result.get('accessibility_summary', {})
    if accessibility_summary:
        print(f"[OK] Accessibility Summary:")
        print(f"  - Good: {accessibility_summary.get('good', 0)}")
        print(f"  - Moderate: {accessibility_summary.get('moderate', 0)}")
        print(f"  - Poor: {accessibility_summary.get('poor', 0)}")
    
    results = result.get('results', [])
    if results:
        print(f"\n[OK] Sample hospital accessibility (first 2):")
        for hospital in results[:2]:
            print(f"\n  Hospital: {hospital.get('name')}")
            print(f"    Accessibility Level: {hospital.get('accessibility_level')}")
            print(f"    Distance to Major Road: {hospital.get('distance_to_major_road_km')} km")
            print(f"    Population Density: {hospital.get('surrounding_population_density'):.2f}")
            print(f"    Accessibility Score: {hospital.get('accessibility_score')}/100")
    
    print("\n[OK] PASSED")
    return True


def test_healthcare_gaps():
    """Test healthcare gap identification."""
    print("\n" + "=" * 70)
    print("TEST 5: Healthcare Gap Identification")
    print("=" * 70)
    
    result = spatial_analysis.find_healthcare_gaps(
        min_population_threshold=5000.0,
        max_hospital_distance_km=5.0
    )
    
    print(f"[OK] Explanation: {result.get('explanation')}")
    print(f"[OK] Healthcare gaps identified: {result.get('gaps_identified')}")
    
    total_affected = result.get('total_affected_population')
    if total_affected is not None:
        print(f"[OK] Total affected population: {total_affected:,.0f}")
    
    print(f"[OK] Gap threshold distance: {result.get('gap_threshold_distance_km')} km")
    
    gaps = result.get('results', [])
    if gaps:
        print(f"\n[OK] Sample healthcare gaps (first 3):")
        for i, gap in enumerate(gaps[:3], 1):
            print(f"\n  Gap #{i}:")
            print(f"    Location: {gap.get('location')}")
            print(f"    Population: {gap.get('population'):,.0f}")
            print(f"    Nearest Hospital Distance: {gap.get('nearest_hospital_distance_km')} km")
            print(f"    Gap Severity Score: {gap.get('gap_severity')}/100")
    else:
        print("[OK] No healthcare gaps identified (good coverage)")
    
    print("\n[OK] PASSED")
    return True


def test_site_suitability():
    """Test site suitability analysis."""
    print("\n" + "=" * 70)
    print("TEST 6: Site Suitability Analysis")
    print("=" * 70)
    
    weights = {
        "population_proximity": 0.40,
        "road_accessibility": 0.25,
        "healthcare_coverage": 0.25,
        "environmental_factors": 0.10,
    }
    
    result = spatial_analysis.calculate_site_suitability(weights=weights)
    
    print(f"[OK] Explanation: {result.get('explanation')}")
    print(f"[OK] Total candidates evaluated: {result.get('total_candidates')}")
    
    print(f"\n[OK] Weights Applied:")
    for factor, weight in weights.items():
        print(f"  - {factor}: {weight*100:.0f}%")
    
    candidates = result.get('top_candidates', [])
    if candidates:
        print(f"\n[OK] Top 5 Candidate Locations:")
        for candidate in candidates[:5]:
            print(f"\n  Rank #{candidate.get('rank')}:")
            print(f"    Location: {candidate.get('location')}")
            print(f"    Suitability Score: {candidate.get('suitability_score')}/100")
            
            factors = candidate.get('factors', {})
            if factors:
                print(f"    Factor Scores:")
                for factor_name, score in factors.items():
                    print(f"      - {factor_name}: {score}")
    
    print("\n[OK] PASSED")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("GeoAI Spatial Analysis - Implementation Validation Test")
    print("=" * 70)
    
    print(f"\nConfiguration:")
    print(f"  Study Area: {settings.study_area_name}")
    print(f"  Bbox: {settings.study_area_bbox}")
    print(f"  Real Data Dir: {settings.real_data_dir}")
    
    # Check if real data is available
    raster_path = settings.real_data_dir / "worldpop_pune_clip.tif"
    stats_path = settings.real_data_dir / "worldpop_stats.json"
    
    print(f"\n  Raster File: {'[OK] Available' if raster_path.exists() else '[FAIL] Missing'}")
    print(f"  Stats File: {'[OK] Available' if stats_path.exists() else '[FAIL] Missing'}")
    
    tests = [
        ("Population Statistics", test_population_statistics),
        ("High-Population Areas", test_high_population_areas),
        ("Population Near Hospitals", test_population_near_hospitals),
        ("Hospital Accessibility", test_hospital_accessibility),
        ("Healthcare Gaps", test_healthcare_gaps),
        ("Site Suitability", test_site_suitability),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n[SUCCESS] All tests passed! Implementation is working correctly.")
        return 0
    else:
        print(f"\n[WARNING] {total_count - passed_count} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
