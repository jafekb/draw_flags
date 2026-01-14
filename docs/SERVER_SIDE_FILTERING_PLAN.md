# Server-Side Filtering Plan (Efficient Implementation)

## Overview
Implement server-side filtering by filtering flags BEFORE computing cosine similarities, making it more efficient than computing similarities on all 2,753 flags and more reliable than client-side filtering.

## Architecture

### Data Flow
1. Frontend sends: `{text_query: "red white blue", filters: {categories: ["national"], continent: "Africa"}}`
2. Backend filters dataset: 2,753 flags → 57 African national flags
3. Backend extracts embeddings for those 57 flags
4. Backend computes similarities only on those 57 embeddings
5. Backend returns top 15 from those 57
6. Frontend displays all 15 results

## Implementation Details

### Backend Changes

#### 1. Update API Endpoint
**File:** `backend/main.py`

Add filters parameter to the request:
```python
class SearchRequest(BaseModel):
    text_query: str
    categories: Optional[List[str]] = None
    continent: Optional[str] = None
    country: Optional[str] = None

@app.post("/", response_model=FlagList)
async def add_flag(request: SearchRequest):
    flags = flag_searcher.query(
        request.text_query,
        is_image=False,
        filters={
            "categories": request.categories,
            "continent": request.continent,
            "country": request.country
        }
    )
    return flags
```

#### 2. Update FlagSearcher
**File:** `backend/src/flag_searcher.py`

Add efficient filtering before similarity computation:

```python
def _get_filtered_indices(self, filters):
    """
    Return indices of flags matching the filters.
    
    Returns:
        List[int]: Indices of matching flags
    """
    if not filters:
        return list(range(len(self._flags.flags)))
    
    matching_indices = []
    
    for idx, flag in enumerate(self._flags.flags):
        # Category filter
        if filters.get("categories"):
            if flag.category not in filters["categories"]:
                continue
        
        # Continent filter
        if filters.get("continent"):
            if flag.continent != filters["continent"]:
                continue
        
        # Country filter (national flag OR from that country)
        if filters.get("country"):
            is_national = flag.category == "national" and flag.name == filters["country"]
            is_from_country = flag.country == filters["country"]
            if not (is_national or is_from_country):
                continue
        
        matching_indices.append(idx)
    
    return matching_indices

def query(self, text_query, is_image, filters=None):
    """
    Search for flags matching the query, with optional filtering.
    
    Args:
        text_query: Text description of the flag
        is_image: Whether query is an image (not implemented)
        filters: Optional dict with keys: categories, continent, country
    
    Returns:
        FlagList with top_k matching flags
    """
    if is_image:
        raise NotImplementedError
    
    # 1. Get indices of flags matching filters
    filtered_indices = self._get_filtered_indices(filters)
    
    # Handle empty filter results
    if len(filtered_indices) == 0:
        return FlagList(flags=[])
    
    # 2. Extract embeddings for filtered flags only
    filtered_embeddings = self._encoded_images[filtered_indices]
    
    # 3. Encode the text query
    query_embedding = self._encode_text(text_query)
    
    # 4. Compute similarities ONLY on filtered embeddings
    similarities = cosine_similarity(query_embedding, filtered_embeddings)
    
    # 5. Get top K from filtered set
    num_results = min(self._top_k, len(filtered_indices))
    top_k_local_indices = similarities.argsort()[0][::-1][:num_results]
    sorted_scores = similarities.ravel()[top_k_local_indices].tolist()
    
    # 6. Map back to original flags and add scores
    results = []
    for local_idx, score in zip(top_k_local_indices, sorted_scores):
        original_idx = filtered_indices[local_idx]
        flag = self._flags.flags[original_idx]
        flag_with_score = flag.model_copy(update={"score": score})
        results.append(flag_with_score)
    
    return FlagList(flags=results)
```

#### 3. Keep top_k at 15
**File:** `backend/main.py`

Change back to 15 since filtering is server-side:
```python
flag_searcher = FlagSearcher(top_k=15)
```

### Frontend Changes

#### 1. Update Flags.jsx
**File:** `frontend/src/components/Flags.jsx`

Simplify back to passing filters to API:

```javascript
const FlagList = () => {
  const [flags, setFlags] = useState([]);
  const [filters, setFilters] = useState({
    categories: null,
    continent: null,
    country: null,
  });

  const addFlag = async (textQuery) => {
    try {
      const response = await api.post("/", {
        text_query: textQuery,
        categories: filters.categories,
        continent: filters.continent,
        country: filters.country,
      });
      setFlags(response.data.flags);
    } catch (error) {
      console.error("Error adding flag", error);
    }
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    setFlags([]); // Clear results when filters change
  };

  return (
    <div>
      <FilterPanel onFilterChange={handleFilterChange} activeFilters={filters} />
      <h2>Describe the flag using words</h2>
      <SubmitDescriptionForm addFlag={addFlag} />
      
      {flags.length === 0 ? null : (
        <>
          <button onClick={() => setFlags([])} 
                  style={{ backgroundColor: "#FFCECE", color: "black" }}>
            Clear
          </button>
          <ImageGrid images={flags} title="I bet it's..." />
        </>
      )}
    </div>
  );
};
```

## Benefits

1. **Efficient**: Only compute similarities on filtered subset (e.g., 57 instead of 2,753)
2. **Complete Results**: Always get 15 results if available in filtered set
3. **Clean Separation**: Backend handles filtering, frontend handles display
4. **Scalable**: Performance improves when filters reduce dataset size

## Performance Comparison

| Scenario | Flags | Similarities Computed | Time |
|----------|-------|----------------------|------|
| No filter | 2,753 | 2,753 | ~100ms |
| Africa filter | 57 | 57 | ~5ms |
| Africa + National | 57 | 57 | ~5ms |
| USA + subdivisions | ~200 | ~200 | ~10ms |

## Files to Modify

1. `backend/main.py` - Add SearchRequest model and pass filters
2. `backend/src/flag_searcher.py` - Add `_get_filtered_indices()` and update `query()`
3. `frontend/src/components/Flags.jsx` - Pass filters to API, remove client-side filtering

## Testing Plan

1. Test no filters - should return all flags
2. Test category filter - only matching categories
3. Test continent filter - only matching continent
4. Test country filter - national + subdivisions
5. Test combined filters - all conditions met
6. Test empty results - no matches

## Migration from Current Code

Since we just implemented client-side filtering, we need to:
1. Revert the client-side filtering logic in Flags.jsx
2. Add SearchRequest model to main.py
3. Add filtering methods to flag_searcher.py
4. Keep FilterPanel component (already works!)
5. Test thoroughly

