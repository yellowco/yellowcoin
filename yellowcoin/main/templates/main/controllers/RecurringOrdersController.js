function RecurringOrdersController($scope, $http) {
	$scope.recurringOrders = {{recurring_orders|safe}};
	$scope.deleteRecurringOrder = function(order) {
		$http.delete('/api/orders/recurring/' + order.id + '/').success(function() {
			var index = $scope.recurringOrders.indexOf(order);
			$scope.recurringOrders.splice(index, 1);
		}).error(function(data) {
			$scope.showError('delete a recurring order', data);
		});
	};
}
