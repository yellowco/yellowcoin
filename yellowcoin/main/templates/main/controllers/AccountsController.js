function AccountsController($scope, $http, $timeout) {
	$scope.data = {BTC:{}, bank:{}}
	$scope.pending = {};
	$scope.errors = {};
	$scope.validationId = 0;
	$scope.setValidate = function(context, value) {
		$scope.validationId = value;
		$scope.microdeposit1 = "";
		$scope.microdeposit2 = "";
	};
	$scope.microdeposit1 = "";
	$scope.microdeposit2 = "";
	$scope.microdepositErrors = null;
	$scope.validate = function(context, id) {
		$scope.microdepositErrors = null;
		var mp1 = parseFloat($scope.microdeposit1), mp2 = parseFloat($scope.microdeposit2);
		if(mp1 && mp2) {
			$http.put('/api/accounts/bank/' + id + '/verify/', {
				micropayment_1:mp1,
				micropayment_2:mp2
			}).success(function(data) {
			  	$("#bank-validate-modal").modal('hide');
				$scope.accounts[context][id].is_confirmed = true;
				$scope.microdeposit1 = "";
				$scope.microdeposit2 = "";
			}).error(function(data) {
				$scope.microdepositErrors = data.detail;
			});
		} else {
			$scope.microdepositErrors = "The values you entered are not valid.";
		}
	};
	$scope.readable = {
		'bank':{icon:'money', text:'Bank Accounts'},
		'BTC':{icon:'btc',text:'Bitcoin Addresses'}
	};
	$scope.$watch('data.bank.routing_number', function(value) {
		if(value && value.length == 9) {
			$http.get('/internal/bank/lookup/' + value + '/').success(function(data) {
				$scope.data.bank.bank_name = data.name;
			}).error(function(data) {
				$scope.data.bank.bank_name = "Unknown";
			});
		} else {
			$scope.data.bank.bank_name = "";
		}
	});
	$scope.submit = function(context) {
		$scope.errors[context] = null;
		$http.post('/api/accounts/' + context + '/', $scope.data[context]).success(function(data) {
		   	$scope.accounts[context][data.id] = data;
			$scope.data[context] = {};
			if(context == 'bank') {
				$scope.data[context].type = 'C'; // edge case
			}
			$("#" + context + "-modal").modal('hide');
	   	}).error(function(data) {
		   	$scope.errors[context] = data.detail;
		});
	};
	var timerHandles = {};
	var delta = 250;
	$scope.delete = function(context, id) {
		$scope.accounts[context][id].deleteTimeout = 5000;
		function deleteTick() {
			$scope.accounts[context][id].deleteTimeout -= delta;
			if($scope.accounts[context][id].deleteTimeout <= 0) {
				$scope.accounts[context][id].deleted = true;
				$http.delete('/api/accounts/' + context + '/' + id + '/')
					.success(function(data) {
						$scope.accounts[context][id].deleteTimeout = false;
						delete $scope.accounts[context][id];
			   		}).error(function(data) {
						$scope.accounts[context][id].deleted = false;
						$scope.showError('delete an account', data.detail);
					});
			} else {
				timerHandles[id] = $timeout(deleteTick, delta, true);
			}
		}
		timerHandles[id] = $timeout(deleteTick, delta, true);
	};
	$scope.undelete = function(context, id) {
		$scope.accounts[context][id].deleteTimeout = false;
		$timeout.cancel(timerHandles[id]);
	};
	$scope.setDefault = function(context, id) {
		var previousDefault;
		for(var i in $scope.accounts[context]) {
			if($scope.accounts[context][i].is_default) {
				previousDefault = i;
				$scope.accounts[context][i].is_default = false;
			}
		}
		$scope.accounts[context][id].is_default = true;
   		$http.put('/api/accounts/' + context + '/' + id + '/', {is_default:true})
			.error(function(data) {
				$scope.accounts[context][id].is_default = false;
				$scope.accounts[context][previousDefault].is_default = true;
				$scope.showError('set the default account', data.detail);
			});
	};
}

