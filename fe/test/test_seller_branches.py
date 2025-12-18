import requests
from urllib.parse import urljoin
from fe import conf
import uuid
import time


def test_ship_by_other_seller_fails():
    base = conf.URL
    # use timestamp to ensure unique IDs
    ts = str(int(time.time() * 1000000))
    
    # register seller A and create store/book
    sellerA_name = f"sA_{ts[:10]}"
    r = requests.post(urljoin(base, 'auth/register'), json={'user_id': sellerA_name, 'password': 'a'})
    assert r.status_code == 200
    r = requests.post(urljoin(base, 'auth/login'), json={'user_id': sellerA_name, 'password': 'a'})
    assert r.status_code == 200
    sellerA = r.json().get('user_id') or sellerA_name
    store_id = f"sA_{ts}"
    r = requests.post(urljoin(base, 'seller/create_store'), json={'user_id': sellerA, 'store_id': store_id})
    assert r.status_code == 200
    book_id = f"bk_{ts}"
    book_info = {'id': book_id, 'title': 'Sbook', 'price': 5, 'isbn': f's-isbn-{ts}'}
    r = requests.post(urljoin(base, 'seller/add_book'), json={'user_id': sellerA, 'store_id': store_id, 'book_info': book_info, 'stock_level': 1})
    r = requests.post(urljoin(base, 'seller/add_stock_level'), json={'user_id': sellerA, 'store_id': store_id, 'book_id': book_id, 'add_stock_level': 1})

    # register buyer and create order
    buyer_name = f"buy_{ts[:10]}"
    r = requests.post(urljoin(base, 'auth/register'), json={'user_id': buyer_name, 'password': 'b'})
    assert r.status_code == 200
    r = requests.post(urljoin(base, 'auth/login'), json={'user_id': buyer_name, 'password': 'b'})
    buyer = r.json().get('user_id') or buyer_name
    r = requests.post(urljoin(base, 'buyer/new_order'), json={'user_id': buyer, 'store_id': store_id, 'books': [{'id': book_id, 'count': 1}]})
    assert r.status_code == 200
    order_id = r.json().get('order_id')

    # register another seller B and try to ship A's order -> should fail
    sellerB_name = f"sB_{ts[:10]}"
    r = requests.post(urljoin(base, 'auth/register'), json={'user_id': sellerB_name, 'password': 'bb'})
    assert r.status_code == 200
    r = requests.post(urljoin(base, 'auth/login'), json={'user_id': sellerB_name, 'password': 'bb'})
    assert r.status_code == 200
    sellerB = r.json().get('user_id') or sellerB_name
    r = requests.post(urljoin(base, 'seller/ship'), json={'user_id': sellerB, 'order_id': order_id})
    # seller B should NOT be able to ship seller A's order
    # accept non-200 success codes (error statuses like 403, 401, 400)
    assert r.status_code != 200
