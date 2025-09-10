from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import Category, Product, Order, OrderItem


class CategoryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics",
            description="Electronic devices and gadgets"
        )

    def test_category_creation(self):
        """Test that a category can be created successfully"""
        self.assertEqual(self.category.name, "Electronics")
        self.assertEqual(self.category.description, "Electronic devices and gadgets")
        self.assertTrue(self.category.created_at)
        self.assertTrue(self.category.updated_at)

    def test_category_str_representation(self):
        """Test the string representation of a category"""
        self.assertEqual(str(self.category), "Electronics")

    def test_category_verbose_name_plural(self):
        """Test the verbose name plural setting"""
        self.assertEqual(Category._meta.verbose_name_plural, "Categories")


class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics",
            description="Electronic devices"
        )
        self.product = Product.objects.create(
            name="Laptop",
            description="High-performance laptop",
            price=Decimal('999.99'),
            category=self.category,
            stock_quantity=10
        )

    def test_product_creation(self):
        """Test that a product can be created successfully"""
        self.assertEqual(self.product.name, "Laptop")
        self.assertEqual(self.product.price, Decimal('999.99'))
        self.assertEqual(self.product.category, self.category)
        self.assertTrue(self.product.in_stock)
        self.assertEqual(self.product.stock_quantity, 10)

    def test_product_str_representation(self):
        """Test the string representation of a product"""
        self.assertEqual(str(self.product), "Laptop")

    def test_product_is_available_property(self):
        """Test the is_available property"""
        self.assertTrue(self.product.is_available)
        
        # Test when out of stock
        self.product.in_stock = False
        self.assertFalse(self.product.is_available)
        
        # Test when stock quantity is 0
        self.product.in_stock = True
        self.product.stock_quantity = 0
        self.assertFalse(self.product.is_available)


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('199.98')
        )

    def test_order_creation(self):
        """Test that an order can be created successfully"""
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.status, 'pending')
        self.assertEqual(self.order.total_amount, Decimal('199.98'))
        self.assertTrue(self.order.created_at)
        self.assertTrue(self.order.updated_at)

    def test_order_str_representation(self):
        """Test the string representation of an order"""
        expected = f"Order {self.order.id} - testuser"
        self.assertEqual(str(self.order), expected)

    def test_order_is_pending_property(self):
        """Test the is_pending property"""
        self.assertTrue(self.order.is_pending)
        
        self.order.status = 'processing'
        self.assertFalse(self.order.is_pending)


class OrderItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            name="Laptop",
            description="High-performance laptop",
            price=Decimal('999.99'),
            category=self.category
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('1999.98')
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal('999.99')
        )

    def test_order_item_creation(self):
        """Test that an order item can be created successfully"""
        self.assertEqual(self.order_item.order, self.order)
        self.assertEqual(self.order_item.product, self.product)
        self.assertEqual(self.order_item.quantity, 2)
        self.assertEqual(self.order_item.price, Decimal('999.99'))

    def test_order_item_str_representation(self):
        """Test the string representation of an order item"""
        expected = "Laptop x 2"
        self.assertEqual(str(self.order_item), expected)

    def test_order_item_total_price_property(self):
        """Test the total_price property"""
        expected_total = 2 * Decimal('999.99')
        self.assertEqual(self.order_item.total_price, expected_total)


class CategoryAPITest(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics",
            description="Electronic devices"
        )

    def test_list_categories(self):
        """Test listing all categories"""
        url = reverse('category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check paginated response structure
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], "Electronics")

    def test_create_category(self):
        """Test creating a new category"""
        url = reverse('category-list')
        data = {
            'name': 'Books',
            'description': 'Books and literature'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 2)

    def test_retrieve_category(self):
        """Test retrieving a specific category"""
        url = reverse('category-detail', kwargs={'pk': self.category.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Electronics")

    def test_update_category(self):
        """Test updating a category"""
        url = reverse('category-detail', kwargs={'pk': self.category.pk})
        data = {'name': 'Updated Electronics', 'description': 'Updated description'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Updated Electronics')

    def test_delete_category(self):
        """Test deleting a category"""
        url = reverse('category-detail', kwargs={'pk': self.category.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Category.objects.count(), 0)

    def test_category_products_endpoint(self):
        """Test the custom products endpoint for a category"""
        # Create a product for this category
        Product.objects.create(
            name="Laptop",
            description="High-performance laptop",
            price=Decimal('999.99'),
            category=self.category
        )
        
        url = reverse('category-products', kwargs={'pk': self.category.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Laptop")


class ProductAPITest(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics",
            description="Electronic devices"
        )
        self.product = Product.objects.create(
            name="Laptop",
            description="High-performance laptop",
            price=Decimal('999.99'),
            category=self.category,
            stock_quantity=5
        )

    def test_list_products(self):
        """Test listing all products"""
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check paginated response structure
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_product(self):
        """Test creating a new product"""
        url = reverse('product-list')
        data = {
            'name': 'Smartphone',
            'description': 'Latest smartphone',
            'price': '699.99',
            'category': self.category.id,
            'stock_quantity': 10
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)

    def test_products_in_stock_endpoint(self):
        """Test the in_stock products endpoint"""
        # Create an out-of-stock product
        Product.objects.create(
            name="Out of Stock Item",
            description="This item is out of stock",
            price=Decimal('99.99'),
            category=self.category,
            in_stock=False
        )
        
        url = reverse('product-in-stock')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only the in-stock product
        self.assertEqual(response.data[0]['name'], "Laptop")

    def test_products_by_category_endpoint(self):
        """Test the by_category products endpoint"""
        # Create another category and product
        other_category = Category.objects.create(name="Books")
        Product.objects.create(
            name="Programming Book",
            description="Learn Python",
            price=Decimal('49.99'),
            category=other_category
        )
        
        url = reverse('product-by-category')
        response = self.client.get(url, {'category_id': self.category.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Laptop")


class OrderAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('199.98')
        )

    def test_list_orders(self):
        """Test listing all orders"""
        url = reverse('order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check paginated response structure
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)

    def test_cancel_order_endpoint(self):
        """Test the cancel order endpoint"""
        url = reverse('order-cancel', kwargs={'pk': self.order.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')

    def test_ship_order_endpoint(self):
        """Test the ship order endpoint"""
        # First set order to processing status
        self.order.status = 'processing'
        self.order.save()
        
        url = reverse('order-ship', kwargs={'pk': self.order.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'shipped')

    def test_ship_pending_order_fails(self):
        """Test that shipping a pending order fails"""
        url = reverse('order-ship', kwargs={'pk': self.order.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class TelemetryDemoTests(TestCase):
    """Tests designed to generate interesting telemetry data"""
    
    def setUp(self):
        # Create test data
        self.categories = []
        for i in range(5):
            category = Category.objects.create(
                name=f"Category {i}",
                description=f"Description for category {i}"
            )
            self.categories.append(category)
        
        self.products = []
        for i, category in enumerate(self.categories):
            for j in range(3):  # 3 products per category
                product = Product.objects.create(
                    name=f"Product {i}-{j}",
                    description=f"Description for product {i}-{j}",
                    price=Decimal(f'{10 + i * 10 + j}.99'),
                    category=category,
                    stock_quantity=5 + j
                )
                self.products.append(product)

    def test_duplicate_queries(self):
        """Test that generates many duplicate queries for telemetry analysis"""
        # This will generate many SELECT queries for the same products
        for _ in range(10):  # Run the same query 10 times
            products = list(Product.objects.filter(category=self.categories[0]))
            self.assertEqual(len(products), 3)
        
        # Generate duplicate queries with different parameters
        for category in self.categories:
            for _ in range(3):  # 3 times per category
                products = list(Product.objects.filter(category=category))
                self.assertTrue(len(products) > 0)

    def test_long_running_test(self):
        """Test that takes longer to execute for duration analysis"""
        import time
        
        # Simulate some processing time
        time.sleep(0.1)  # 100ms delay
        
        # Perform multiple database operations
        for i in range(20):
            # Create and delete products to generate queries
            product = Product.objects.create(
                name=f"Temp Product {i}",
                description="Temporary product for testing",
                price=Decimal('1.00'),
                category=self.categories[0],
                stock_quantity=1
            )
            product.delete()
        
        # Verify we still have our original products
        self.assertEqual(Product.objects.count(), len(self.products))

    def test_complex_database_operations(self):
        """Test with various database operations (SELECT, INSERT, UPDATE, DELETE)"""
        # SELECT operations
        _ = list(Category.objects.all())
        _ = list(Product.objects.all())
        
        # INSERT operations
        new_category = Category.objects.create(
            name="New Category",
            description="A newly created category"
        )
        new_product = Product.objects.create(
            name="New Product",
            description="A newly created product",
            price=Decimal('50.00'),
            category=new_category,
            stock_quantity=10
        )
        
        # UPDATE operations
        new_product.price = Decimal('75.00')
        new_product.save()
        new_category.name = "Updated Category"
        new_category.save()
        
        # More SELECT operations after updates
        updated_product = Product.objects.get(pk=new_product.pk)
        self.assertEqual(updated_product.price, Decimal('75.00'))
        
        # DELETE operations
        new_product.delete()
        new_category.delete()
        
        # Final verification
        self.assertEqual(Category.objects.count(), len(self.categories))
        self.assertEqual(Product.objects.count(), len(self.products))


class NetworkCallTests(APITestCase):
    """Tests that make network calls for telemetry monitoring"""
    
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            description="For network testing"
        )
        self.product = Product.objects.create(
            name="Test Product",
            description="For network testing",
            price=Decimal('100.00'),
            category=self.category,
            stock_quantity=5
        )

    def test_external_api_call(self):
        """Test that makes an external API call"""
        import urllib.request
        import json
        
        # Make a call to a public API (httpbin.org for testing)
        try:
            with urllib.request.urlopen('https://httpbin.org/json') as response:
                data = json.loads(response.read().decode())
                self.assertIn('slideshow', data)
        except Exception:
            # If network is not available, just pass the test
            # This ensures the test doesn't fail in environments without internet
            pass

    def test_multiple_network_calls(self):
        """Test that makes multiple network calls"""
        import urllib.request
        import json
        
        urls = [
            'https://httpbin.org/json',
            'https://httpbin.org/uuid',
            'https://httpbin.org/user-agent'
        ]
        
        for url in urls:
            try:
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())
                    self.assertIsInstance(data, dict)
            except Exception:
                # If network is not available, just pass the test
                pass

    def test_database_with_network_calls(self):
        """Test that combines database operations with network calls"""
        import urllib.request
        import json
        
        # Database operations
        products = list(Product.objects.filter(category=self.category))
        self.assertEqual(len(products), 1)
        
        # Network call
        try:
            with urllib.request.urlopen('https://httpbin.org/json') as response:
                data = json.loads(response.read().decode())
                self.assertIn('slideshow', data)
        except Exception:
            pass
        
        # More database operations
        self.product.price = Decimal('150.00')
        self.product.save()
        
        # Another network call
        try:
            with urllib.request.urlopen('https://httpbin.org/uuid') as response:
                data = json.loads(response.read().decode())
                self.assertIn('uuid', data)
        except Exception:
            pass


class PerformanceStressTests(TestCase):
    """Tests designed to stress test performance and generate interesting metrics"""
    
    def setUp(self):
        # Create a large dataset
        self.categories = []
        for i in range(10):
            category = Category.objects.create(
                name=f"Stress Category {i}",
                description=f"Category for stress testing {i}"
            )
            self.categories.append(category)
            
            # Create products for each category
            for j in range(5):
                Product.objects.create(
                    name=f"Stress Product {i}-{j}",
                    description=f"Product for stress testing {i}-{j}",
                    price=Decimal(f'{10 + i * 5 + j}.99'),
                    category=category,
                    stock_quantity=10 + j
                )

    def test_large_dataset_queries(self):
        """Test with large dataset to generate many queries"""
        # Complex queries that will generate multiple database hits
        categories_with_products = Category.objects.filter(
            product__isnull=False
        ).distinct()
        
        for category in categories_with_products:
            # Multiple queries per category
            products = list(Product.objects.filter(category=category))
            expensive_products = list(Product.objects.filter(
                category=category, 
                price__gt=Decimal('50.00')
            ))
            low_stock_products = list(Product.objects.filter(
                category=category,
                stock_quantity__lt=15
            ))
            
            # Verify results
            self.assertTrue(len(products) > 0)
            self.assertTrue(len(expensive_products) >= 0)
            self.assertTrue(len(low_stock_products) >= 0)

    def test_nested_queries(self):
        """Test with nested queries that generate complex query patterns"""
        # This will generate many related queries
        for category in self.categories:
            products = list(Product.objects.filter(category=category))
            for product in products:
                # Nested query for each product
                related_products = list(Product.objects.filter(
                    category=product.category,
                    price__range=(product.price - Decimal('10.00'), product.price + Decimal('10.00'))
                ))
                self.assertTrue(len(related_products) > 0)

    def test_bulk_operations(self):
        """Test with bulk operations to generate interesting query patterns"""
        # Bulk create
        new_products = []
        for i in range(20):
            new_products.append(Product(
                name=f"Bulk Product {i}",
                description=f"Bulk created product {i}",
                price=Decimal(f'{5 + i}.99'),
                category=self.categories[0],
                stock_quantity=1
            ))
        
        Product.objects.bulk_create(new_products)
        
        # Bulk update
        Product.objects.filter(name__startswith='Bulk Product').update(
            price=Decimal('99.99')
        )
        
        # Bulk delete
        Product.objects.filter(name__startswith='Bulk Product').delete()
        
        # Verify cleanup
        self.assertEqual(Product.objects.filter(name__startswith='Bulk Product').count(), 0)
