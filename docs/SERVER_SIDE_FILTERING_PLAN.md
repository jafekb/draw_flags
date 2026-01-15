# Server-Side Filtering Plan (Efficient Implementation)

## Overview
Implement server-side filtering by retrieving ANN candidates from the vector index and filtering by metadata, so the vector store remains the only supported search path.

## Architecture

### Data Flow
1. Frontend sends: `{text_query: "red white blue", filters: {categories: ["national"], continent: "Africa"}}`
2. Backend encodes text and queries HNSW for `candidate_k` neighbors
3. Backend filters candidates by metadata
4. Backend returns top 15 matching candidates
5. Frontend displays all 15 results

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

Use ANN candidates and filter by metadata:

```python
def search_by_vector(self, vector, top_k, filters=None) -> FlagList:
    if filters:
        candidate_k = min(self._filtered_candidate_k, total_flags)
        ids, scores = self._vector_index.search(vector, candidate_k)
        flags = self._metadata_store.get_many(ids)

        filtered_flags = []
        for flag, score in zip(flags, scores):
            if not self._matches_filters(flag, filters):
                continue
            filtered_flags.append(flag.model_copy(update={"score": score}))
            if len(filtered_flags) >= top_k:
                break
        return FlagList(flags=filtered_flags)
    ...
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

1. **Vector store only**: Single search path for all queries
2. **Efficient**: ANN candidate search keeps latency low
3. **Clean separation**: Backend handles filtering, frontend handles display
4. **Configurable**: Tune `candidate_k` without changing the API

## Performance Notes

- Filtered queries are approximate: results depend on `candidate_k`.
- Larger `candidate_k` improves recall but costs more time.

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

## Migration Notes

- Filtering is now performed on ANN candidates instead of full-vector scans.
- The vector index is the only supported query path.

