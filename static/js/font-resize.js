$(window).load(function() {
	var size = $(this).width() / 100;
	$("body").css("font-size", size + "px");
});

$(window).resize(function() {
	var size = $(this).width() / 100;
	$("body").css("font-size", size + "px");
});