$(document).ready(function() {
	var $password = $("#register-password");
	var $parent = $password.parent();
	$password.keypress(function() {
		setStrength(scorePassword($password.val()));
	});
	var triggered = false;
	$parent.parent().find('[type="submit"]').hover(function() {
		if(!$parent.hasClass('has-success')) {
			$password.tooltip({trigger:'manual', title:'We won\'t stop you, but you might want to use a stronger password.'});
			$password.tooltip('show');
			triggered = true;
		} else if(triggered) {
			$password.tooltip({trigger:'manual', html:true, placement:'right', title:'<i class="fa fa-thumbs-o-up fa-2x"></i>'});
			$password.tooltip('show');
		}
	}, function() {
		$password.tooltip('destroy');
	});
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
