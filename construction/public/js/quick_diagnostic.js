// Paste this in browser console when a filter dropdown is OPEN
console.clear();
(function(){
  console.log('=== FILTER DROPDOWN DIAGNOSTIC ===');

  // Find all ULs in body
  document.querySelectorAll('body ul').forEach(function(ul, i){
    var style = getComputedStyle(ul);
    if (style.display !== 'none') {
      console.log('UL #' + i + ':', ul.className || '(no class)',
        'role:', ul.getAttribute('role'),
        'bg:', style.backgroundColor,
        'display:', style.display);
      // List first 3 items
      var items = ul.querySelectorAll('li');
      console.log('  Items:', items.length,
        items[0] ? items[0].textContent.substring(0,30) : '');
    }
  });

  // Find visible dropdown-menu elements
  document.querySelectorAll('.dropdown-menu').forEach(function(el, i){
    var style = getComputedStyle(el);
    if (style.display !== 'none') {
      console.log('Dropdown #' + i + ':', el.className,
        'bg:', style.backgroundColor,
        'parent:', el.parentElement?.className?.substring(0,50));
    }
  });

  // Check for awesomplete
  var awe = document.querySelectorAll('ul.awesomplete, [class*="awesomplete"]');
  console.log('\nAwesomplete elements:', awe.length);
  awe.forEach(function(el, i){
    console.log('  #' + i + ':', el.tagName, el.className,
      'display:', getComputedStyle(el).display);
  });

  console.log('=== END ===');
})();
