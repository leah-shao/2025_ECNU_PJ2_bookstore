import requests
from urllib.parse import urljoin
from fe import conf
import uuid
import time


class TestSellerEdgeCases:
    def test_seller_add_multiple_books(self):
        base = conf.URL
        ts = str(int(time.time() * 1000000))
        seller_id = f"sel_{ts}"
        store_id = f"store_{ts}"
        
        # Register seller
        r = requests.post(urljoin(base, 'auth/register'), json={'user_id': seller_id, 'password': 'p'})
        assert r.status_code == 200
        
        # Login
        r = requests.post(urljoin(base, 'auth/login'), json={'user_id': seller_id, 'password': 'p'})
        assert r.status_code == 200
        seller_name = r.json().get('user_id') or seller_id
        
        # Create store
        r = requests.post(urljoin(base, 'seller/create_store'), json={'user_id': seller_name, 'store_id': store_id})
        assert r.status_code == 200
        
        # Add 5 books
        for i in range(5):
            book_info = {
                'id': f'book_{i}_{ts}',
                'title': f'Book {i}',
                'price': 10 + i,
                'isbn': f'isbn-{i}-{ts}'
            }
            r = requests.post(urljoin(base, 'seller/add_book'), json={
                'user_id': seller_name,
                'store_id': store_id,
                'book_info': book_info,
                'stock_level': 100 + i
            })
            assert r.status_code == 200
    
    def test_seller_non_existent_store(self):
        base = conf.URL
        ts = str(int(time.time() * 1000000))
        seller_id = f"sel2_{ts}"
        
        # Register seller
        r = requests.post(urljoin(base, 'auth/register'), json={'user_id': seller_id, 'password': 'p'})
        assert r.status_code == 200
        
        # Login
        r = requests.post(urljoin(base, 'auth/login'), json={'user_id': seller_id, 'password': 'p'})
        assert r.status_code == 200
        seller_name = r.json().get('user_id') or seller_id
        
        # Try to add book to non-existent store
        book_info = {'id': f'book_{ts}', 'title': 'Book', 'price': 10, 'isbn': f'isbn-{ts}'}
        r = requests.post(urljoin(base, 'seller/add_book'), json={
            'user_id': seller_name,
            'store_id': 'nonexistent_store',
            'book_info': book_info,
            'stock_level': 100
        })
        # Should return error (not 200)
        assert r.status_code != 200


class TestUserBalanceOperations:
    
    def test_user_add_large_funds(self):
        base = conf.URL
        ts = str(int(time.time() * 1000000))
        user_id = f"user_fund_{ts}"
        
        # Register
        r = requests.post(urljoin(base, 'auth/register'), json={'user_id': user_id, 'password': 'p'})
        assert r.status_code == 200
        
        # Add large amount
        r = requests.post(urljoin(base, 'buyer/add_funds'), json={
            'user_id': user_id,
            'password': 'p',
            'add_value': 1000000
        })
        assert r.status_code == 200
    
    def test_user_multiple_add_funds(self):
        base = conf.URL
        ts = str(int(time.time() * 1000000))
        user_id = f"user_multi_{ts}"
        
        # Register
        r = requests.post(urljoin(base, 'auth/register'), json={'user_id': user_id, 'password': 'p'})
        assert r.status_code == 200
        
        # Add funds 3 times
        for amount in [100, 200, 300]:
            r = requests.post(urljoin(base, 'buyer/add_funds'), json={
                'user_id': user_id,
                'password': 'p',
                'add_value': amount
            })
            assert r.status_code == 200
