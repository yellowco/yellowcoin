$(document).ready(function() {
	var $password = $("#register-password");
	var $confirm = $("#register-password-confirm");
	var $email = $("#register-email");
	var $tos = $("input[name='tos']");
	var $parent = $password.parent();
	$password.keypress(function() {
		setStrength(scorePassword($password.val()));
	});
	$confirm.keypress(function() {
		$confirm.tooltip('destroy');
	});
	$email.keypress(function() {
		$email.tooltip('destroy');
	});
	$tos.change(function() {
		$tos.tooltip('destroy');
	});
	var triggered = false;
	$parent.parents("form").submit(doValidation).find('[type="submit"]').hover(doValidation, function() {
		$password.tooltip('destroy');
	});
	function doValidation(event) {
		var isHover = (event.type != "submit");
		var valid = true;
		$password.trigger('keypress');
		if(!$parent.hasClass('has-success') && isHover) {
			if($password.val().length < 6) {
				$password.tooltip({trigger:'manual', title:'Your password needs to be at least six characters long.'});
				$password.tooltip('show');
			} else {
				$password.tooltip({trigger:'manual', title:'We won\'t stop you, but you should use a stronger password.'});
				$password.tooltip('show');
			}
			triggered = true;
		} else if(triggered) {
			$password.tooltip({trigger:'manual', html:true, placement:'right', title:'<i class="fa fa-thumbs-o-up fa-2x"></i>'});
			$password.tooltip('show');
		}
		if($password.val().length < 6 && !isHover) {
			$password.tooltip({trigger:'manual', title:'Your password needs to be at least six characters long.'});
			$password.tooltip('show');
			valid = false;
		}
		if(!validEmail($email.val())) {
			$email.tooltip({trigger:'manual', title:'Your email is not valid.'});
			$email.tooltip('show');
			valid = false;
		}
		if($tos.length > 0 && !$tos.is(":checked")) {
			$tos.tooltip({trigger:'manual', title:'You must accept the terms of service.'});
			$tos.tooltip('show');
			valid = false;
		}
		if($confirm.val() != $password.val()) {
			$confirm.tooltip({trigger:'manual', title:'This doesn\'t match your password.'});
			$confirm.tooltip('show');
			valid = false;
		}
		if(!valid) {
			event.preventDefault();
		}
	}
function validEmail(email) {
	return /^([a-zA-Z0-9_.+-])+\@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$/.test(email);
}
function setStrength(str) {
	$parent.removeClass('has-success has-warning has-error');
	if(str > 80) {
		$parent.addClass('has-success');
	} else if(str > 60) {
		$parent.addClass('has-warning');
	} else {
		$parent.addClass('has-error');
	}
}
function scorePassword(pass) {
    var score = 0;
    if (!pass)
        return score;

    var letters = new Object();
    for (var i=0; i<pass.length; i++) {
        letters[pass[i]] = (letters[pass[i]] || 0) + 1;
        score += 5.0 / letters[pass[i]];
    }

    var variations = {
        digits: /\d/.test(pass),
        lower: /[a-z]/.test(pass),
        upper: /[A-Z]/.test(pass),
        nonWords: /\W/.test(pass),
    }

    variationCount = 0;
    for (var check in variations) {
        variationCount += (variations[check] == true) ? 1 : 0;
    }
    score += (variationCount - 1) * 10;

    return parseInt(score);
}
});
