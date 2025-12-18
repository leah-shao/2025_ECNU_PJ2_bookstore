"""Search helper using PostgreSQL text search.

Functions:
 - search_books(q, fields=None, store_id=None, page=1, page_size=10)

Uses PostgreSQL LIKE search against the store table with book_info JSON field.
"""
from be.model import store as store_mod
from be.model import db_conn
import json
import math


def search_books(q: str, fields=None, store_id: str = None, page: int = 1, page_size: int = 10):
    """Search books in PostgreSQL.
    Parameters:
    - q: keyword string
    - fields: list of fields to search
    - store_id: if provided, restrict to books available in that store
    - page/page_size: pagination
    """
    try:
        conn = store_mod.get_db_conn()
        
        # Build WHERE clauses
        where_clauses = []
        params = []
        
        if store_id:
            where_clauses.append('store_id = %s')
            params.append(store_id)
        
        if q:
            # Search in book_info JSON and other fields
            like_q = f'%{q}%'
            where_clauses.append('(book_info::text ILIKE %s OR book_info::text ILIKE %s OR book_info::text ILIKE %s)')
            params.extend([like_q, like_q, like_q])
        
        where_clause = ' AND '.join(f'({w})' for w in where_clauses) if where_clauses else '1=1'
        
        # Get total count
        count_sql = f'SELECT COUNT(*) FROM store WHERE {where_clause}'
        cursor = conn.execute(count_sql, params)
        total = cursor.fetchone()[0]
        
        # Get paginated results
        offset = (page - 1) * page_size
        sql = f'SELECT book_info FROM store WHERE {where_clause} LIMIT %s OFFSET %s'
        cursor = conn.execute(sql, params + [page_size, offset])
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            try:
                book_info = row[0]
                # Handle both string and dict returns from PostgreSQL JSONB
                if isinstance(book_info, str):
                    book_info = json.loads(book_info)
                results.append(book_info)
            except Exception:
                results.append({})
        
        return 200, 'ok', results, total
    
    except Exception as e:
        return 528, f'Search failed: {str(e)}', [], 0

