#!/usr/bin/env python3
"""
Simple script to test the Django example API endpoints.
Run this after starting the example with: docker-compose up -d
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_api():
    print("Testing Django Example API...")
    print("=" * 50)
    
    # Test categories endpoint
    print("\n1. Testing Categories API:")
    response = requests.get(f"{BASE_URL}/categories/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Create a category
    print("\n2. Creating a category:")
    category_data = {
        "name": "Electronics",
        "description": "Electronic devices and gadgets"
    }
    response = requests.post(f"{BASE_URL}/categories/", json=category_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        category = response.json()
        print(f"Created category: {category['name']} (ID: {category['id']})")
        
        # Test products endpoint
        print("\n3. Testing Products API:")
        response = requests.get(f"{BASE_URL}/products/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        # Create a product
        print("\n4. Creating a product:")
        product_data = {
            "name": "Laptop",
            "description": "High-performance laptop",
            "price": "999.99",
            "category": category['id'],
            "stock_quantity": 10
        }
        response = requests.post(f"{BASE_URL}/products/", json=product_data)
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            product = response.json()
            print(f"Created product: {product['name']} (ID: {product['id']})")
            
            # Test in-stock products
            print("\n5. Testing in-stock products:")
            response = requests.get(f"{BASE_URL}/products/in_stock/")
            print(f"Status: {response.status_code}")
            print(f"In-stock products: {len(response.json())}")
            
            # Test products by category
            print("\n6. Testing products by category:")
            response = requests.get(f"{BASE_URL}/products/by_category/?category_id={category['id']}")
            print(f"Status: {response.status_code}")
            print(f"Products in category: {len(response.json())}")
    
    # Test orders endpoint
    print("\n7. Testing Orders API:")
    response = requests.get(f"{BASE_URL}/orders/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    print("\n" + "=" * 50)
    print("API test completed!")

if __name__ == "__main__":
    test_api()
