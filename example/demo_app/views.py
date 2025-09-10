from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Category, Product, Order 
from .serializers import CategorySerializer, ProductSerializer, OrderSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        category = self.get_object()
        products = category.products.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @action(detail=False, methods=['get'])
    def in_stock(self, request):
        products = self.queryset.filter(in_stock=True)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category_id = request.query_params.get('category_id')
        if category_id:
            products = self.queryset.filter(category_id=category_id)
        else:
            products = self.queryset.all()
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status == 'pending':
            order.status = 'cancelled'
            order.save()
            return Response({'status': 'Order cancelled'})
        return Response({'error': 'Order cannot be cancelled'}, 
                       status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def ship(self, request, pk=None):
        order = self.get_object()
        if order.status == 'processing':
            order.status = 'shipped'
            order.save()
            return Response({'status': 'Order shipped'})
        return Response({'error': 'Order cannot be shipped'}, 
                       status=status.HTTP_400_BAD_REQUEST)
