-- =============================================================
-- Fix: kb_search_with_docs ranking issues
-- Problem: Health Happy brochure appears in unrelated queries
-- Root cause: bot_boost x1.5 + common Thai keywords match all bot_summaries
-- =============================================================

-- FIX 1: Replace function with improved version
-- Changes:
--   a) bot_boost default 1.5 → 1.0 (disable boost)
--   b) Add category_filter parameter
--   c) Add Thai stop words to exclude common insurance terms from ILIKE scoring
--   d) Require minimum 2 keyword matches for bot_summary to qualify

CREATE OR REPLACE FUNCTION public.kb_search_with_docs(
  query_text text,
  query_embedding vector DEFAULT NULL::vector,
  match_count integer DEFAULT 5,
  source_filter text DEFAULT NULL::text,
  vector_weight double precision DEFAULT 0.7,
  fts_weight double precision DEFAULT 0.3,
  bot_boost double precision DEFAULT 1.0,        -- Changed: 1.5 → 1.0
  category_filter text DEFAULT NULL::text         -- NEW: filter by category
)
RETURNS TABLE(
  id bigint, document_name text, source text, chunk_text text,
  chunk_index integer, chunk_tokens integer, storage_path text,
  pdf_public_url text, metadata jsonb, search_score double precision
)
LANGUAGE plpgsql
AS $function$
DECLARE
  keywords text[];
  or_query text;
  max_kw_len int;
  -- Thai stop words: too common in insurance docs, cause false matches
  thai_stop_words text[] := ARRAY[
    'ประกัน', 'คุ้มครอง', 'เบี้ย', 'แบบ', 'สัญญา',
    'บริษัท', 'กรมธรรม์', 'ผลประโยชน์', 'เงื่อนไข'
  ];
BEGIN
  -- Thai sliding window tokenization, capped at 20 longest keywords
  keywords := array(
    SELECT kw FROM (
      SELECT DISTINCT kw FROM (
        SELECT unnest AS kw
        FROM unnest(string_to_array(
          regexp_replace(query_text, '[^\u0E00-\u0E7Fa-zA-Z0-9\s]', ' ', 'g'),
          ' '
        ))
        WHERE length(unnest) >= 2
        UNION
        SELECT substring(word FROM i FOR len) AS kw
        FROM (
          SELECT unnest AS word
          FROM unnest(string_to_array(
            regexp_replace(query_text, '[^\u0E00-\u0E7Fa-zA-Z0-9\s]', ' ', 'g'),
            ' '
          ))
          WHERE length(unnest) >= 6
        ) words,
        generate_series(1, greatest(1, length(words.word) - 3)) i,
        generate_series(4, least(12, length(words.word))) len
        WHERE i + len - 1 <= length(words.word)
          AND len >= 4
      ) all_keywords
      WHERE length(kw) >= 3
        AND kw != ALL(thai_stop_words)  -- NEW: exclude stop words
    ) deduped
    ORDER BY length(kw) DESC
    LIMIT 20
  );

  IF array_length(keywords, 1) IS NOT NULL AND array_length(keywords, 1) > 0 THEN
    or_query := array_to_string(keywords, ' | ');
    max_kw_len := (SELECT MAX(length(k)) FROM unnest(keywords) k);
  ELSE
    or_query := query_text;
    max_kw_len := length(query_text);
  END IF;

  RETURN QUERY
  WITH vec AS (
    SELECT c.id AS cid, (1 - (c.embedding <=> query_embedding))::FLOAT AS score
    FROM kb_chunks c
    WHERE query_embedding IS NOT NULL AND c.embedding IS NOT NULL
      AND (source_filter IS NULL OR c.source = source_filter)
      AND (category_filter IS NULL OR c.category = category_filter)  -- NEW
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count * 4
  ),
  fts AS (
    SELECT c.id AS cid, ts_rank(to_tsvector('simple', c.chunk_text), to_tsquery('simple', or_query))::FLOAT AS score
    FROM kb_chunks c
    WHERE to_tsvector('simple', c.chunk_text) @@ to_tsquery('simple', or_query)
      AND (source_filter IS NULL OR c.source = source_filter)
      AND (category_filter IS NULL OR c.category = category_filter)  -- NEW
    LIMIT match_count * 4
  ),
  ilike_scored AS (
    SELECT c.id AS cid,
      LEAST(1.0, (
        SELECT SUM(length(k)::FLOAT / GREATEST(max_kw_len, 1))
        FROM unnest(keywords) k
        WHERE c.chunk_text ILIKE '%' || k || '%'
      ) / GREATEST(array_length(keywords, 1)::FLOAT * 0.3, 1))::FLOAT AS score
    FROM kb_chunks c
    WHERE array_length(keywords, 1) IS NOT NULL
      AND EXISTS (SELECT 1 FROM unnest(keywords) k WHERE c.chunk_text ILIKE '%' || k || '%')
      AND (source_filter IS NULL OR c.source = source_filter)
      AND (category_filter IS NULL OR c.category = category_filter)  -- NEW
    LIMIT match_count * 6
  ),
  all_ids AS (
    SELECT cid FROM vec
    UNION SELECT cid FROM fts
    UNION SELECT cid FROM ilike_scored
  ),
  merged AS (
    SELECT
      a.cid,
      COALESCE(v.score, 0)::FLOAT AS v_score,
      GREATEST(COALESCE(f.score, 0), COALESCE(il.score, 0))::FLOAT AS t_score
    FROM all_ids a
    LEFT JOIN vec v ON v.cid = a.cid
    LEFT JOIN fts f ON f.cid = a.cid
    LEFT JOIN ilike_scored il ON il.cid = a.cid
  ),
  final AS (
    SELECT
      m.cid,
      CASE
        WHEN c.document_name LIKE 'bot_%'
        THEN ((vector_weight * m.v_score) + (fts_weight * m.t_score)) * bot_boost
        ELSE (vector_weight * m.v_score) + (fts_weight * m.t_score)
      END AS final_score
    FROM merged m
    JOIN kb_chunks c ON c.id = m.cid
  )
  SELECT
    c.id, c.document_name, c.source, c.chunk_text, c.chunk_index, c.chunk_tokens,
    c.storage_path,
    CASE WHEN c.storage_path IS NOT NULL
      THEN 'https://heciyiepgxqtbphepalf.supabase.co/storage/v1/object/public/aia-knowledge-base/' || c.storage_path
      ELSE NULL
    END,
    c.metadata,
    f.final_score::FLOAT
  FROM final f
  JOIN kb_chunks c ON c.id = f.cid
  ORDER BY f.final_score DESC
  LIMIT match_count;
END;
$function$;

-- =============================================================
-- FIX 2: Populate category on product kb_chunks
-- Map bot_summary categories to product chunks by matching document names
-- =============================================================

-- PA products
UPDATE kb_chunks SET category = 'pa'
WHERE source = 'products' AND category IS NULL
AND (document_name ILIKE '%PA%' OR document_name ILIKE '%accident%');

-- Health products
UPDATE kb_chunks SET category = 'health'
WHERE source = 'products' AND category IS NULL
AND (document_name ILIKE '%health%' OR document_name ILIKE '%H&S%'
  OR document_name ILIKE '%HB%' OR document_name ILIKE '%HS%Junior%');

-- CI products
UPDATE kb_chunks SET category = 'ci'
WHERE source = 'products' AND category IS NULL
AND (document_name ILIKE '%CI%' OR document_name ILIKE '%cancer%'
  OR document_name ILIKE '%TPD%' OR document_name ILIKE '%MPCI%'
  OR document_name ILIKE '%WPCI%');

-- Investment / Unit Linked
UPDATE kb_chunks SET category = 'investment'
WHERE source = 'products' AND category IS NULL
AND (document_name ILIKE '%unit%link%' OR document_name ILIKE '%issara%'
  OR document_name ILIKE '%elite%' OR document_name ILIKE '%infinite%wealth%'
  OR document_name ILIKE '%infinite%gift%' OR document_name ILIKE '%20PayLink%');

-- Savings / Endowment
UPDATE kb_chunks SET category = 'savings'
WHERE source = 'products' AND category IS NULL
AND (document_name ILIKE '%saving%' OR document_name ILIKE '%endowment%'
  OR document_name ILIKE '%legacy%' OR document_name ILIKE '%protection65%'
  OR document_name ILIKE '%annuity%' OR document_name ILIKE '%pay%life%'
  OR document_name ILIKE '%excellent%' OR document_name ILIKE '%life%gift%'
  OR document_name ILIKE '%5pay%' OR document_name ILIKE '%7pay%'
  OR document_name ILIKE '%8pay%' OR document_name ILIKE '%10for80%'
  OR document_name ILIKE '%15pay%' OR document_name ILIKE '%flexi%');

-- Vitality
UPDATE kb_chunks SET category = 'vitality'
WHERE source = 'products' AND category IS NULL
AND document_name ILIKE '%vitality%';

-- =============================================================
-- FIX 3: Same category mapping for kb_files
-- =============================================================

UPDATE kb_files SET category = 'pa'
WHERE source = 'products' AND category IS NULL
AND (filename ILIKE '%PA%' AND filename NOT ILIKE '%PDPA%');

UPDATE kb_files SET category = 'health'
WHERE source = 'products' AND category IS NULL
AND (filename ILIKE '%health%' OR filename ILIKE '%H&S%' OR filename ILIKE '%HB%');

UPDATE kb_files SET category = 'ci'
WHERE source = 'products' AND category IS NULL
AND (filename ILIKE '%CI%' OR filename ILIKE '%cancer%'
  OR filename ILIKE '%TPD%' OR filename ILIKE '%MPCI%');

UPDATE kb_files SET category = 'investment'
WHERE source = 'products' AND category IS NULL
AND (filename ILIKE '%unit%link%' OR filename ILIKE '%issara%'
  OR filename ILIKE '%elite%' OR filename ILIKE '%infinite%wealth%'
  OR filename ILIKE '%infinite%gift%' OR filename ILIKE '%20PayLink%');

UPDATE kb_files SET category = 'savings'
WHERE source = 'products' AND category IS NULL
AND (filename ILIKE '%saving%' OR filename ILIKE '%endowment%'
  OR filename ILIKE '%legacy%' OR filename ILIKE '%protection65%'
  OR filename ILIKE '%annuity%' OR filename ILIKE '%pay%life%'
  OR filename ILIKE '%excellent%' OR filename ILIKE '%life%gift%');

UPDATE kb_files SET category = 'vitality'
WHERE source = 'products' AND category IS NULL
AND filename ILIKE '%vitality%';
