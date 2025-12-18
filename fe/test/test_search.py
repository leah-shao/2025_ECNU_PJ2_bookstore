
import pytest
import requests
import uuid
from urllib.parse import urljoin
from fe import conf
from fe.access import auth, seller, book


class TestSearchModel:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.auth = auth.Auth(conf.URL)
        self.seller_id = f"seller_search_{uuid.uuid4()}"
        self.seller_password = f"pwd_{uuid.uuid4().hex}"
        
        # Register seller
        code = self.auth.register(self.seller_id, self.seller_password)
        assert code == 200
        
        # Create store
        seller_obj = seller.Seller(conf.URL, self.seller_id, self.seller_password)
        self.store_id = f"store_{uuid.uuid4()}"
        code = seller_obj.create_store(self.store_id)
        assert code == 200
        
        # Create books using Book class
        self.books = []
        book_configs = [
            {"id": f"book_python_{uuid.uuid4()}", "title": "Python Programming", "author": "John Doe", "price": 2999, "isbn": "978-0-12-345678-0"},
            {"id": f"book_java_{uuid.uuid4()}", "title": "Java Advanced", "author": "Jane Smith", "price": 3999, "isbn": "978-0-98-765432-1"},
            {"id": f"book_csharp_{uuid.uuid4()}", "title": "C# for Beginners", "author": "Bob Johnson", "price": 2499, "isbn": "978-1-11-111111-1"}
        ]
        
        for config in book_configs:
            b = book.Book()
            b.id = config["id"]
            b.title = config["title"]
            b.author = config["author"]
            b.price = config["price"]
            b.isbn = config["isbn"]
            
            code = seller_obj.add_book(self.store_id, 10, b)
            assert code == 200
            self.books.append(config)
        
        yield
    
    def test_search_by_title(self):
        """Test searching for books by title"""
        url = urljoin(conf.URL, "search/")
        
        # Search for "Python"
        r = requests.get(urljoin(url, ""), params={"q": "Python"})
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "ok"
        # Should find the Python book
        assert len([b for b in data["results"] if "Python" in b.get("title", "")]) > 0
    
    def test_search_by_author(self):
        url = urljoin(conf.URL, "search/")
        
        # Search for "John"
        r = requests.get(urljoin(url, ""), params={"q": "John"})
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "ok"
        # Should find books by John
        assert len(data["results"]) > 0
    
    def test_search_pagination(self):
        url = urljoin(conf.URL, "search/")
        
        # Search with page and page_size
        r = requests.get(urljoin(url, ""), params={"q": "", "page": 1, "page_size": 1})
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "ok"
        assert data["page"] == 1
        assert data["page_size"] == 1
        # Should return at most 1 result
        assert len(data["results"]) <= 1
    
    def test_search_by_store_id(self):
        url = urljoin(conf.URL, "search/")
        
        # Search in specific store
        r = requests.get(urljoin(url, ""), params={"store_id": self.store_id, "q": ""})
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "ok"
        # Should find books in this store
        assert len(data["results"]) > 0
    
    def test_search_empty_query(self):
        url = urljoin(conf.URL, "search/")
        
        # Search with empty query
        r = requests.get(urljoin(url, ""), params={"q": ""})
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "ok"
        assert data["total"] >= len(self.books)
    
    def test_search_no_results(self):
        url = urljoin(conf.URL, "search/")
        
        # Search for something that doesn't exist
        r = requests.get(urljoin(url, ""), params={"q": "NONEXISTENT_BOOK_XYZ_123"})
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "ok"
        assert len(data["results"]) == 0
    
    def test_search_case_insensitive(self):
        url = urljoin(conf.URL, "search/")
        
        # Search for "python" (lowercase)
        r1 = requests.get(urljoin(url, ""), params={"q": "python"})
        assert r1.status_code == 200
        
        # Search for "PYTHON" (uppercase)
        r2 = requests.get(urljoin(url, ""), params={"q": "PYTHON"})
        assert r2.status_code == 200
        
        # Both should return results
        data1 = r1.json()
        data2 = r2.json()
        assert len(data1["results"]) > 0
        assert len(data2["results"]) > 0
        assert len(data1["results"]) == len(data2["results"])
    
    def test_search_invalid_page(self):
        url = urljoin(conf.URL, "search/")
        
        # Search with invalid page (should default to 1)
        r = requests.get(urljoin(url, ""), params={"q": "", "page": "invalid"})
        assert r.status_code == 200
        data = r.json()
        # Should return default page
        assert data["page"] == 1
    
    def test_search_invalid_page_size(self):
        url = urljoin(conf.URL, "search/")
        
        # Search with invalid page_size (should default to 10)
        r = requests.get(urljoin(url, ""), params={"q": "", "page_size": "invalid"})
        assert r.status_code == 200
        data = r.json()
        # Should return default page_size
        assert data["page_size"] == 10
    
    def test_search_total_count_matches_results(self):
        url = urljoin(conf.URL, "search/")
        
        # Search all books
        r = requests.get(urljoin(url, ""), params={"q": ""})
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "ok"
        # Total should be greater than or equal to returned results
        assert data["total"] >= len(data["results"])
