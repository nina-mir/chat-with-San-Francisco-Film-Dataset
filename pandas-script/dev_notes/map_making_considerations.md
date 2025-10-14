Your plan is well-thought-out and makes a lot of sense! Here are my thoughts on your approach:

## What's Working Well in Your Plan

1. **Smart Detection Logic**: Using the preprocessing results to detect spatial queries is elegant. The presence of `"field": "geometry"` or `"type": "spatial"` in the filters array is a reliable indicator that visualization would be valuable.

2. **Logical Integration Point**: Adding map generation to the code generation step is the right place - you have all the context (preprocessing results, NLP plan, and the actual query results) needed to make informed decisions about visualization.

3. **Point-Based Simplicity**: Since you're only dealing with Point geometries, this keeps the visualization straightforward and focused - perfect for film location mapping.

## Suggestions and Considerations

### Detection Enhancement
Beyond just spatial filters, consider these additional triggers for map generation:
- Queries about "locations" or "places" (even without explicit spatial filtering)
- Distance-based queries (like your Union Square/Embarcadero examples)
- Queries that return multiple geographic points that would benefit from visual context

### Implementation Approach
I'd suggest creating the map generation as a **conditional step within your existing pipeline** rather than a separate stage:

```python
# In your code generation step
if self._should_generate_map(preprocessing_result, nlp_plan):
    # Generate both GeoPandas code AND Folium visualization code
    # Return both in your standardized result format
```

### Map Generation Triggers
Consider these scenarios where maps would add value:
- **Spatial filters**: Your current detection logic
- **Multiple locations returned**: Even non-spatial queries returning many locations
- **Distance queries**: Any query involving proximity or distance calculations
- **Location discovery**: Queries like "what was filmed at X location?"

### Practical Considerations

1. **Result Integration**: Your standardized result dictionary could include an optional `'map'` key alongside `'data'`, `'summary'`, and `'metadata'`.

2. **Performance**: Folium map generation is relatively fast, but consider whether to make it opt-in for very large result sets.

3. **Map Styling**: Since these are film locations, you could add nice touches like:
   - Different colors for different years/decades
   - Popup information showing film title, year, actors
   - Clustering for areas with many filming locations

4. **File Output**: Consider whether to save maps as HTML files alongside your existing logging.

## Questions to Consider

1. **User Control**: Do you want users to be able to explicitly request maps (e.g., "show me a map of...") even for non-spatial queries?

2. **Default Behavior**: For borderline cases, would you rather err on the side of creating too many maps or too few?

3. **Map Complexity**: Do you want simple point maps, or would you add features like:
   - Base map selection (street view, satellite, etc.)
   - Location clustering for dense areas
   - Custom markers based on film genres/years

Your approach is solid and well-integrated with your existing architecture. The key insight about using the preprocessing results as a trigger is particularly clever and should work reliably for your use cases.