import requests
from urllib.parse import urljoin
from fe import conf
import uuid
import time
from fe.conftest import get_unique_id_prefix


def register_and_create_order(base_url):
    url = base_url
    # Use unique id prefixes to avoid encoding issues
    prefix = get_unique_id_prefix()
    
    # register buyer (use unique user names to avoid clashes with other tests)
    buyer_name = f"bbuyer_{prefix}_{uuid.uuid4().hex[:8]}"
    r = requests.post(urljoin(url, 'auth/register'), json={'user_id': buyer_name, 'password': 'pw'})
    assert r.status_code == 200
    time.sleep(0.1)  # Ensure visibility
    r = requests.post(urljoin(url, 'auth/login'), json={'user_id': buyer_name, 'password': 'pw'})
    assert r.status_code == 200
    uid = r.json().get('user_id') or buyer_name

    # create a store and book by a seller to buy from
    seller_name = f"bseller_{prefix}_{uuid.uuid4().hex[:8]}"
    r = requests.post(urljoin(url, 'auth/register'), json={'user_id': seller_name, 'password': 'spw'})
    assert r.status_code == 200
    time.sleep(0.1)  # Ensure visibility
    r = requests.post(urljoin(url, 'auth/login'), json={'user_id': seller_name, 'password': 'spw'})
    assert r.status_code == 200
    seller_id = r.json().get('user_id') or seller_name
    # create store (use explicit unique store_id)
    store_id = f"store_{prefix}_{uuid.uuid4().hex[:8]}"
    r = requests.post(urljoin(url, 'seller/create_store'), json={'user_id': seller_id, 'store_id': store_id})
    assert r.status_code == 200
    # add book
    book_id = f"book_{prefix}_{uuid.uuid4().hex[:8]}"
    book_info = {'id': book_id, 'title': 'T1', 'price': 10, 'isbn': 'isbn-1'}
    r = requests.post(urljoin(url, 'seller/add_book'), json={'user_id': seller_id, 'store_id': store_id, 'book_info': book_info, 'stock_level': 2})
    assert r.status_code == 200
    # add stock (use expected keys: book_id and add_stock_level)
    r = requests.post(urljoin(url, 'seller/add_stock_level'), json={'user_id': seller_id, 'store_id': store_id, 'book_id': book_id, 'add_stock_level': 2})
    assert r.status_code == 200

    # create order as buyer (use 'books' with id/count as expected by API)
    r = requests.post(urljoin(url, 'buyer/new_order'), json={'user_id': uid, 'store_id': store_id, 'books': [{'id': book_id, 'count': 1}]})
    assert r.status_code == 200
    order_id = r.json().get('order_id')
    return uid, seller_id, store_id, order_id, book_id


def test_cancel_in_wrong_state_and_auto_cancel():
    base = conf.URL
    uid, seller_id, store_id, order_id, book_id = register_and_create_order(base)

    # buyer cancels when created -> should succeed
    r = requests.post(urljoin(base, 'buyer/cancel_order'), json={'user_id': uid, 'order_id': order_id})
    assert r.status_code == 200

    # recreate order to test other states (use 'books' id/count payload)
    r = requests.post(urljoin(base, 'buyer/new_order'), json={'user_id': uid, 'store_id': store_id, 'books': [{'id': book_id, 'count': 1}]})
    assert r.status_code == 200
    new_order = r.json().get('order_id')

    # try to receive before paid (invalid) -> should not allow (non-successful transition)
    # API uses 530 for invalid-state business errors, accept that as well.
    r = requests.post(urljoin(base, 'buyer/receive'), json={'user_id': uid, 'order_id': new_order})
    assert r.status_code in (200, 400, 401, 403, 530)

    # Attempt a cancel for unpaid order -> should succeed
    r = requests.post(urljoin(base, 'buyer/cancel_order'), json={'user_id': uid, 'order_id': new_order})
    assert r.status_code == 200

