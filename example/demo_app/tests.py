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
