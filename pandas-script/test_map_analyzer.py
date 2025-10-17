# test_map_analyzer.py
"""
Test script for MapDataAnalyzer with various data structures.
"""
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from src.map_analyzer import MapDataAnalyzer


def create_test_gdf():
    """Create a minimal test GeoDataFrame"""
    data = {
        'Title': ['The Matrix', 'The Matrix', 'Vertigo', 'Vertigo'],
        'Year': [1999, 1999, 1958, 1958],
        'Locations': [
            'Union Square',
            'Golden Gate Bridge',
            'Mission Dolores Park',
            'Potrero & San Bruno'
        ],
        'geometry': [
            Point(-122.4077, 37.7880),  # Union Square
            Point(-122.4783, 37.8199),  # Golden Gate Bridge
            Point(-122.4269, 37.7596),  # Mission Dolores Park
            Point(-122.4089, 37.7599)   # Potrero
        ]
    }
    return gpd.GeoDataFrame(data, crs='EPSG:4326')


def print_test_result(test_name, analysis):
    """Pretty print test results"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    print(f"Can Map: {analysis['can_map']}")
    print(f"Reason: {analysis['reason']}")
    print(f"Data Type: {analysis['data_type']}")
    print(f"Location Mentioned: {analysis['location_mentioned']}")
    if analysis['location_data']:
        print(f"Locations Found: {len(analysis['location_data'])}")
        for i, loc in enumerate(analysis['location_data'][:3], 1):  # Show first 3
            print(f"  {i}. {loc['location_name']}")
            if loc.get('metadata'):
                print(f"     Metadata: {loc['metadata']}")
    else:
        print("Locations Found: None")
    print()


def run_tests():
    """Run comprehensive tests"""
    # Setup
    gdf = create_test_gdf()
    analyzer = MapDataAnalyzer(gdf)
    
    # Test 1: List of location strings (Mrs. Doubtfire case)
    print("\n" + "🎬 STARTING TESTS " + "🎬" * 10)
    
    test_data_1 = {
        'data': ['Union Square', 'Golden Gate Bridge', 'Mission Dolores Park']
    }
    result_1 = analyzer.analyze(test_data_1, "find all the locations of the film Mrs. Doubtfire")
    print_test_result("List of Location Strings", result_1)
    
    # Test 2: Dict with mixed keys (your problematic case)
    test_data_2 = {
        'data': {
            'Number of unique actors': 14,
            'Least popular locations': ['Potrero & San Bruno', 'Mission Dolores Park', 'Union Square']
        }
    }
    result_2 = analyzer.analyze(test_data_2, "what are the least popular locations")
    print_test_result("Dict with Location List Value", result_2)
    
    # Test 3: Location frequency dict (keys are locations)
    test_data_3 = {
        'data': {
            'Union Square': 25,
            'Golden Gate Bridge': 18,
            'Mission Dolores Park': 12
        }
    }
    result_3 = analyzer.analyze(test_data_3, "what are the top locations by frequency")
    print_test_result("Location Frequency Dict", result_3)
    
    # Test 4: Year frequency dict (should NOT map)
    test_data_4 = {
        'data': {
            2020: 42,
            2021: 38,
            2022: 35
        }
    }
    result_4 = analyzer.analyze(test_data_4, "how many films per year")
    print_test_result("Year Frequency Dict (Non-mappable)", result_4)
    
    # Test 5: Scalar value (should NOT map)
    test_data_5 = {
        'data': 42
    }
    result_5 = analyzer.analyze(test_data_5, "how many unique films in 2020")
    print_test_result("Scalar Integer (Non-mappable)", result_5)
    
    # Test 6: Film->locations dict
    test_data_6 = {
        'data': {
            'The Matrix (1999)': ['Union Square', 'Golden Gate Bridge'],
            'Vertigo (1958)': ['Mission Dolores Park']
        }
    }
    result_6 = analyzer.analyze(test_data_6, "get films with their locations")
    print_test_result("Film->Locations Dict", result_6)
    
    # Test 7: List of dicts with Locations key
    test_data_7 = {
        'data': [
            {'Title': 'The Matrix', 'Locations': 'Union Square'},
            {'Title': 'Vertigo', 'Locations': 'Mission Dolores Park'}
        ]
    }
    result_7 = analyzer.analyze(test_data_7, "show me films and their locations")
    print_test_result("List of Dicts with Locations", result_7)
    
    # Test 8: GeoDataFrame
    test_data_8 = {
        'data': gdf
    }
    result_8 = analyzer.analyze(test_data_8, "get all film locations")
    print_test_result("GeoDataFrame", result_8)
    
    # Test 9: DataFrame with Locations column
    test_data_9 = {
        'data': pd.DataFrame({
            'Title': ['The Matrix', 'Vertigo'],
            'Locations': ['Union Square', 'Mission Dolores Park']
        })
    }
    result_9 = analyzer.analyze(test_data_9, "show films with locations")
    print_test_result("DataFrame with Locations", result_9)
    
    # Test 10: Dict with single location field
    test_data_10 = {
        'data': {
            'location': 'Union Square',
            'count': 25,
            'year': 1999
        }
    }
    result_10 = analyzer.analyze(test_data_10, "where was this filmed")
    print_test_result("Dict with Single Location Field", result_10)
    
    # Test 11: Empty data
    test_data_11 = {
        'data': None
    }
    result_11 = analyzer.analyze(test_data_11, "find locations")
    print_test_result("None/Empty Data", result_11)
    
    # Test 12: List with non-location strings (should NOT map)
    test_data_12 = {
        'data': ['Tom Hanks', 'Steven Spielberg', 'Morgan Freeman']
    }
    result_12 = analyzer.analyze(test_data_12, "list all actors")
    print_test_result("List of Non-Location Strings (Non-mappable)", result_12)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_results = [result_1, result_2, result_3, result_4, result_5, result_6,
                   result_7, result_8, result_9, result_10, result_11, result_12]
    
    mappable_count = sum(1 for r in all_results if r['can_map'])
    non_mappable_count = len(all_results) - mappable_count
    
    print(f"Total Tests: {len(all_results)}")
    print(f"✓ Mappable: {mappable_count}")
    print(f"✗ Non-mappable: {non_mappable_count}")
    
    print("\nExpected Mappable (9): Tests 1, 2, 3, 6, 7, 8, 9, 10")
    print("Expected Non-mappable (4): Tests 4, 5, 11, 12")
    
    # Check if results match expectations
    expected_mappable = [True, True, True, False, False, True, True, True, True, True, False, False]
    actual_mappable = [r['can_map'] for r in all_results]
    
    if expected_mappable == actual_mappable:
        print("\n🎉 ALL TESTS PASSED! 🎉")
    else:
        print("\n⚠️ SOME TESTS FAILED ⚠️")
        for i, (expected, actual) in enumerate(zip(expected_mappable, actual_mappable), 1):
            if expected != actual:
                print(f"  Test {i}: Expected {expected}, Got {actual}")


if __name__ == "__main__":
    run_tests()